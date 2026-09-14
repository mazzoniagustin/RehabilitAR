# RehabilitAR

Sistema de gestión para un centro de rehabilitación: clases (individuales y fijas), reservas, lista de espera, asistencia por QR, usuarios y roles, aptos físicos, pagos/mensualidades (Mercado Pago), notificaciones automáticas y un panel de auditoría con estadísticas.


## Equipo

- Agustín Mazzoni
- Luciano Galluzzi
- Nicolás Libré
- Santino Saborido

## Stack

**Backend**
- Python + [FastAPI](https://fastapi.tiangolo.com/) (con tareas en background vía `asyncio` para recordatorios y cancelaciones automáticas)
- [Supabase](https://supabase.com/) (PostgreSQL + Auth + Storage)
- Autenticación por JWT (validado contra Supabase, decodificado con `python-jose`)
- **Mercado Pago**: pagos de mensualidad/deudas, llamados directo a su API REST con `requests` (sin el SDK oficial)
- `reportlab` para generación de comprobantes en PDF
- Envío de mails por SMTP (Gmail) para notificaciones y recordatorios

**Frontend**
- HTML / CSS / JavaScript vanilla
- [Chart.js](https://www.chartjs.org/) y [SheetJS/xlsx](https://sheetjs.com/) en el panel de auditoría, para gráficos y exportar reportes a Excel
- Consumo de la API vía `fetch`

## Estructura del proyecto

```
RehabilitAR/
├── backend/
│   ├── main.py                    # App FastAPI, CORS, routers, jobs automáticos en background
│   ├── database.py                 # Clientes de Supabase (anon + admin/service-role)
│   ├── routes/
│   │   ├── auth.py                 #   /auth          — login, registro, recuperar/resetear contraseña
│   │   ├── user.py                 #   /users         — perfil propio, edición, búsqueda pública
│   │   ├── staff.py                #   /staff         — panel administrativo (aptos, bloqueos, altas)
│   │   ├── classes.py              #   /classes       — alta/gestión de clases, disponibilidad
│   │   ├── reservations.py         #   /reservations  — reservar, lista de espera, mis reservas
│   │   ├── cancellations.py        #   /cancellations — cancelar clase/reserva/suscripción
│   │   ├── payments.py             #   /payments      — mensualidad, deudas, reservas pagas
│   │   ├── mp_webhook.py           #   /mp            — webhook de Mercado Pago
│   │   ├── attendance.py           #   /attendance    — asistencia (manual y por QR)
│   │   ├── notifications.py        #   /notifications — campanita de notificaciones + disparo manual de recordatorios
│   │   └── audit.py                #   /audit         — estadísticas globales y por usuario
│   ├── services/                   # Lógica de negocio (uno o más por dominio de routes/)
│   │   ├── automatic_notifications_service.py  # recordatorios/avisos que disparan los jobs de main.py
│   │   ├── subscriptions_service.py
│   │   ├── audit_service.py
│   │   ├── attendance_service.py
│   │   ├── reservations/           #   individual, fija (regular), lista de espera, "mis reservas"
│   │   └── cancellations/          #   clases, reservas, suscripción
│   ├── schemes/                    # Modelos Pydantic de entrada (request bodies)
│   └── utils/                      # Permisos/roles, validaciones, notificaciones por mail, contraseñas
│
├── frontend/
│   ├── login.html / reset-password.html
│   ├── dashboard.html              # Panel principal (staff + clientes), carga audit.js + dashboard.js
│   ├── attendance.html / attendance.js  # Página de registro de asistencia por QR
│   ├── audit.js                    # Panel de auditoría/estadísticas (Chart.js + export a Excel)
│   ├── auth.js
│   ├── dashboard.js                
│   └── styles.css
│
└── supabase/migrations/            # Migraciones SQL versionadas (ej. tabla de log de notificaciones)
```

## Roles de usuario

| Rol | Tipo | Descripción |
|---|---|---|
| `ADMINISTRATIVO` | Empleado | Gestiona clases, usuarios, aptos físicos, bloqueos, auditoría |
| `RECEPCIONISTA` | Empleado | Requiere especialidad |
| `PROFESOR` | Empleado | Requiere especialidad; dicta clases, solicita asignación, marca asistencia |
| `ABONADO` | Cliente | Con mensualidad activa — puede reservar clases |
| `NO_ABONADO` | Cliente | Sin mensualidad activa |

Los permisos por endpoint se validan con `utils/permissions.py` (`check_permission([...roles])`), que decodifica el JWT de Supabase.

## Instalación

### Requisitos previos
- Python 3.10+
- Una instancia de [Supabase](https://supabase.com/) (URL + `anon key` + `service_role key`) con las tablas del proyecto y las migraciones de `supabase/migrations/` aplicadas
- Credenciales de Mercado Pago (modo test para desarrollo)
- Una cuenta de Gmail con contraseña de aplicación, para el envío de mails/recordatorios

### 1. Clonar y crear entorno virtual

```bash
git clone https://github.com/mazzoniagustin/RehabilitAR.git
cd RehabilitAR
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```bash
# Supabase
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-anon-key
SUPABASE_JWT_SECRET=tu-jwt-secret-de-supabase
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key   

# Mercado Pago
MERCADO_PAGO_ACCESS_TOKEN_TEST=tu-access-token-de-test
MP_EXTERNAL_POS_ID=id-de-tu-punto-de-venta  

# Mail (recordatorios y notificaciones por SMTP de Gmail)
acc_password=tu-contraseña-de-aplicación-de-gmail

# URL pública del frontend (usada, por ejemplo, para armar links en los mails)
FRONTEND_PUBLIC_URL=http://localhost:8000/frontend


```

### 4. Correr el backend

```bash
cd backend
uvicorn main:app --reload
```

## Endpoints principales

| Router | Prefijo | Qué maneja |
|---|---|---|
| `auth` | `/auth` | Registro, login, logout, recuperar/resetear contraseña |
| `user` | `/users` | Perfil propio, edición, cambio de contraseña, subir apto, búsqueda pública |
| `staff` | `/staff` | Alta de empleados, aprobar/rechazar aptos, bloquear/desbloquear usuarios |
| `classes` | `/classes` | Alta de clases individuales/fijas, disponibilidad, salas, profesores, solicitudes |
| `reservations` | `/reservations` | Reservar (individual/fija), lista de espera, mis reservas |
| `cancellations` | `/cancellations` | Cancelar clase, reserva o suscripción |
| `payments` | `/payments` | Pagar mensualidad, deudas, reservas; estado de pagos; cobro en efectivo |
| `mp_webhook` | `/mp` | Webhook de notificaciones de Mercado Pago |
| `attendance` | `/attendance` | Marcar asistencia (manual o vía QR por clase) |
| `notifications` | `/notifications` | Campanita de notificaciones y disparo manual de recordatorios |
| `audit` | `/audit` | Estadísticas globales y por usuario para el panel de auditoría |