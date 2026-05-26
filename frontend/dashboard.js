console.log("dashboard cargó");
// CONFIG
const API          = 'http://localhost:8000';

// HELPERS
const getToken  = () => localStorage.getItem('token');
const clearAuth = () => { localStorage.removeItem('token'); localStorage.removeItem('currentUser'); };
const authH     = () => ({ 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` });
const setUser   = u  => localStorage.setItem('currentUser', JSON.stringify(u));
const getUser   = () => JSON.parse(localStorage.getItem('currentUser') || 'null');

const EMPLOYEE_ROLES = ['ADMINISTRATIVO', 'RECEPCIONISTA', 'PROFESOR'];

function showAlert(id, msg, type = 'error') {
  const el = document.getElementById(id);
  if (!el) return;
  const text = typeof msg === 'string' ? msg : JSON.stringify(msg);
  el.textContent = text;
  el.className = `alert ${type} show`;
  setTimeout(() => { if (el) el.classList.remove('show'); }, 5000);
}

function handleUnauthorized() {
  clearAuth();
  window.location.href = 'login.html';
}

function badge(val, map) {
  const cls = (val || '').toLowerCase().replace(/[^a-z0-9]/g, '_');
  return `<span class="badge ${cls}">${map[val] || val || '—'}</span>`;
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('es-AR', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' });
}

const ROL_LABELS = {
  NO_ABONADO:'No abonado', ABONADO:'Abonado',
  ADMINISTRATIVO:'Administrativo', PROFESOR:'Profesor', RECEPCIONISTA:'Recepcionista'
};
const STATUS_LABELS = { ACTIVA:'Activa', SUSPENDIDA:'Suspendido' };
const CERT_LABELS   = { APROBADO:'APROBADO', RECHAZADO:'RECHAZADO', PENDIENTE:'PENDIENTE'};


// SIDEBAR — diferenciado por rol

const ICONS = {
  grid:     '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
  user:     '<circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>',
  users:    '<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
  gift:     '<path d="M20 12V22H4V12"/><path d="M22 7H2v5h20V7z"/><path d="M12 22V7"/>',
  lock:     '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>',
  file:     '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/>',
  bell:   '<path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/>',
  users2: '<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/>',
};

const NAV_CONFIG = {
  NO_ABONADO: [
    { label:'Inicio',          panel:'Inicio',    icon:'grid' },
    { label:'Encontrar',    panel:'Usuarios',        icon:'users' },
    { label:'Mi perfil',       panel:'Perfil',    icon:'user' },
    { label:'Clases',          panel:'Clases',    icon:'calendar' },
    { label:'Mis reservas',    panel:'Reservas',  icon:'gift' },
    { label: 'Solicitar reactivación', panel:'Reactivacion', icon:'bell' },
    { label:'Seguridad',       panel:'Seguridad', icon:'lock' },
  ],
  ABONADO: [
    { label:'Inicio',          panel:'Inicio',    icon:'grid' },
    { label:'Mi perfil',       panel:'Perfil',    icon:'user' },
    { label:'Encontrar',    panel:'Usuarios',        icon:'users' },
    { label:'Clases',          panel:'Clases',    icon:'calendar' },
    { label:'Mis reservas',    panel:'Reservas',  icon:'gift' },
    { label: 'Solicitar reactivación', panel:'Reactivacion', icon:'bell' },
    { label:'Seguridad',       panel:'Seguridad', icon:'lock' },
  ],
  ADMINISTRATIVO: [
    { label:'Inicio',             panel:'Inicio',        icon:'grid' },
    { label:'Mi perfil',          panel:'Perfil',        icon:'user' },
    { label:'Usuarios',           panel:'Usuarios',      icon:'users',   section:'Administración' },
    { label:'Clases',             panel:'Clases',        icon:'calendar' },
    { label:'Aptos físicos',      panel:'Certificados',  icon:'file' },
    { label:'Solicitudes',        panel:'Solicitudes',   icon:'bell' },
    { label:'Seguridad',          panel:'Seguridad',     icon:'lock' },
  ],
  RECEPCIONISTA: [
    { label:'Inicio',             panel:'Inicio',        icon:'grid' },
    { label:'Mi perfil',          panel:'Perfil',        icon:'user' },
    { label:'Encontrar',    panel:'Usuarios',        icon:'users',   section:'Centro' },
    //{ label:'Usuarios',           panel:'Usuarios',      icon:'users2' },
    //{ label:'Aptos físicos',      panel:'Certificados',  icon:'file' },
    { label: 'Solicitar reactivación', panel:'Reactivacion', icon:'bell' },
    { label:'Seguridad',          panel:'Seguridad',     icon:'lock' },
  ],
  PROFESOR: [
    { label:'Inicio',             panel:'Inicio',        icon:'grid' },
    { label:'Mi perfil',          panel:'Perfil',        icon:'user' },
    { label:'Encontrar',    panel:'Usuarios',        icon:'users' },
    { label:'Mis clases',         panel:'Clases',        icon:'calendar', section:'Clases' },
    { label: 'Solicitar reactivación', panel:'Reactivacion', icon:'bell' },
    { label:'Seguridad',          panel:'Seguridad',     icon:'lock' },
  ],
};

function buildSidebar(rol) {
  const items = NAV_CONFIG[rol] || NAV_CONFIG['NO_ABONADO'];
  const nav   = document.getElementById('sidebarNav');
  nav.innerHTML = '';
  let lastSection = null;

  items.forEach((item, i) => {
    if (item.section && item.section !== lastSection) {
      lastSection = item.section;
      const sec = document.createElement('div');
      sec.className = 'nav-section';
      sec.textContent = item.section;
      nav.appendChild(sec);
    }
    const btn = document.createElement('button');
    btn.className = 'nav-item' + (i === 0 ? ' active' : '');
    btn.innerHTML = `<svg viewBox="0 0 24 24">${ICONS[item.icon] || ''}</svg>${item.label}`;
    btn.onclick = () => {
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('panel' + item.panel).classList.add('active');
      onPanelShow(item.panel);
    };
    nav.appendChild(btn);
  });
}

function onPanelShow(panel) {
  if (panel === 'Clases')       loadClases();
  if (panel === 'Reservas')     loadReservas();
  if (panel === 'Usuarios')     initUserPanel();
  if (panel === 'Certificados') loadCertificados();
  if (panel === 'Solicitudes')  loadSolicitudes();
  if (panel === 'Reactivacion') loadReactivacionPanel();
  if (panel === 'Buscar')       initUserPanel();
}
// CARGA DEL DASHBOARD
const STAT_MAPS = {
  NO_ABONADO:    [{ label:'Reservas totales', key:'total_reservations' }, { label:'Ausencias', key:'total_absences' }, { label:'Cancelaciones', key:'total_cancellations' }],
  ABONADO:       [{ label:'Reservas totales', key:'total_reservations' }, { label:'Ausencias', key:'total_absences' }, { label:'Cancelaciones', key:'total_cancellations' }, { label:'Créditos disponibles', key:'credits' }],
  ADMINISTRATIVO:[{ label:'Usuarios gestionados', key:'_na' }],
  RECEPCIONISTA: [{ label:'Usuarios registrados', key:'_na' }],
  PROFESOR:      [{ label:'Clases dictadas', key:'_na' }],
};

async function loadDashboard() {
  if (!getToken()) { window.location.href = 'login.html'; return; }

  const res = await fetch(`${API}/users/me`, { headers: authH() });
  if (res.status === 401) { handleLogout(); return; }
  const u = await res.json();
  setUser(u);

  const initials = ((u.name || '?')[0] + (u.surname || '?')[0]).toUpperCase();
  document.getElementById('avatarInitials').textContent = initials;
  document.getElementById('sidebarName').textContent    = `${u.name} ${u.surname}`;
  document.getElementById('sidebarEmail').textContent   = u.email || '';
  document.getElementById('sidebarRole').textContent    = u.rol || '';
  document.getElementById('welcomeMsg').textContent     = `Hola, ${u.name} 👋`;

  // Stats
  const stats = STAT_MAPS[u.rol] || STAT_MAPS['NO_ABONADO'];
  document.getElementById('statsGrid').innerHTML = stats.map(s => `
    <div class="stat-card">
      <div class="stat-icon"><svg viewBox="0 0 24 24" fill="none" stroke="var(--teal)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/></svg></div>
      <div class="stat-body"><strong>${u[s.key] ?? '—'}</strong><span>${s.label}</span></div>
    </div>`).join('');

  // Alertas según estado
  if (u.account_status === 'SUSPENDIDA') showAlert('dashAlert', 'Tu cuenta está suspendida. Comunicate con el centro.', 'error');

  // Perfil — vista
  document.getElementById('pfName').textContent    = u.name    || '—';
  document.getElementById('pfSurname').textContent = u.surname || '—';
  document.getElementById('pfEmail').textContent   = u.email   || '—';
  document.getElementById('pfDni').textContent     = u.dni     || '—';
  document.getElementById('pfPhone').textContent   = u.phone   || '—';
  document.getElementById('pfGender').textContent  = u.gender  || '—';
  document.getElementById('pfAge').textContent     = u.age     || '—';
  document.getElementById('pfAddress').textContent = u.address || '—';
  document.getElementById('pfRol').innerHTML    = badge(u.rol,            ROL_LABELS);
  document.getElementById('pfStatus').innerHTML = badge(u.account_status, STATUS_LABELS);

  const isEmployee = EMPLOYEE_ROLES.includes(u.rol);

  // Solo empleados: mostrar especialidad
  if (isEmployee) {
    document.getElementById('pfSpecialtyRow').style.display = 'flex';
    document.getElementById('pfSpecialty').textContent = u.specialty || '—';
  }

  // Solo clientes: mostrar apto físico y sección de subida
  if (!isEmployee) {
    document.getElementById('pfCertRow').style.display = 'flex';
    document.getElementById('pfCert').innerHTML = badge(u.physical_certificate, CERT_LABELS);

    // Mostrar sección de subida solo si no está aprobado
    if (u.physical_certificate !== 'APROBADO') {
      document.getElementById('certSection').style.display = 'block';

      if (u.physical_certificate === 'RECHAZADO') showAlert('dashAlert', 'Tu apto físico fue rechazado. Subí uno nuevo desde "Mi perfil".', 'warn');
      if (!u.physical_certificate || u.physical_certificate === 'PENDIENTE') showAlert('dashAlert', 'Todavía no subiste tu apto físico. Hacelo desde "Mi perfil".', 'warn');
    }
  }

  // Solo abonados: créditos y vencimiento
  if (u.rol === 'ABONADO') {
    document.getElementById('pfCreditsRow').style.display = 'flex';
    const available = u.available_credits ?? 0;
    document.getElementById('pfExpiryRow').style.display  = 'flex';
    document.getElementById('pfCredits').textContent      = available;
    document.getElementById('creditsFill').style.width    = `${((available) / 3) * 100}%`;
    document.getElementById('pfExpiry').textContent       = u.subscription_expiry
      ? new Date(u.subscription_expiry).toLocaleDateString('es-AR') : '—';
  }

  // Admin/recep: mostrar botón de registrar usuario y opciones de empleado
  if (u.rol === 'ADMINISTRATIVO') {
    document.getElementById('btnRegistrarUsuario').style.display = 'inline-flex';
    document.getElementById('optEmpleado').style.display = '';   // habilitar opción empleado
  }
  if (u.rol === 'RECEPCIONISTA') {
    document.getElementById('btnRegistrarUsuario').style.display = 'inline-flex';
    // Recepcionista solo puede registrar clientes, no empleados
  }

  if (u.account_status === 'SUSPENDIDA') {
    const config = NAV_CONFIG[u.rol] || NAV_CONFIG['NO_ABONADO'];

  if (!config.find(i => i.panel === 'Reactivacion')) {
    config.push({ label:'Solicitar reactivación', panel:'Reactivacion', icon:'bell' });
  }
}

  buildSidebar(u.rol);
}


function toggleEdit() {
  const view = document.getElementById('profileViewMode');
  const edit = document.getElementById('profileEditMode');
  const u = getUser();
  if (edit.style.display === 'none' || !edit.style.display) {
    document.getElementById('editName').value    = u?.name    || '';
    document.getElementById('editSurname').value = u?.surname || '';
    document.getElementById('editPhone').value   = u?.phone   || '';
    document.getElementById('editAddress').value = u?.address || '';
    document.getElementById('editGender').value  = u?.gender  || '';
    document.getElementById('editAge').value     = u?.age     || '';
    view.style.display = 'none';
    edit.style.display = 'block';
  } else {
    edit.style.display = 'none';
    view.style.display = 'block';
  }
}

async function saveProfile() {
  const name    = document.getElementById('editName').value.trim();
  const surname = document.getElementById('editSurname').value.trim();
  if (!name || !surname) return showAlert('perfilAlert', 'Nombre y apellido son obligatorios.');

  const ageVal = document.getElementById('editAge').value;
  const body = {
    name, surname,
    phone:   document.getElementById('editPhone').value.trim()   || null,
    address: document.getElementById('editAddress').value.trim() || null,
    gender:  document.getElementById('editGender').value         || null,
    age:     ageVal === '' ? null : Number(ageVal),
  };

  try {
    const res  = await fetch(`${API}/users/me`, { method:'PUT', headers:authH(), body:JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) return showAlert('perfilAlert', typeof data.detail === 'string' ? data.detail : 'Error al guardar.');

    showAlert('perfilAlert', 'Perfil actualizado correctamente.', 'success');

    // Actualizar vista sin recargar
    document.getElementById('pfName').textContent    = name;
    document.getElementById('pfSurname').textContent = surname;
    document.getElementById('pfPhone').textContent   = body.phone   || '—';
    document.getElementById('pfAddress').textContent = body.address || '—';
    document.getElementById('pfGender').textContent  = body.gender  || '—';
    document.getElementById('pfAge').textContent     = body.age     ?? '—';

    const u = getUser();
    if (u) { Object.assign(u, body); setUser(u); }
    toggleEdit();
  } catch { showAlert('perfilAlert', 'No se pudo conectar.'); }
}

let dashCertFile = null;

function handleDashCertSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  if (!['application/pdf','image/jpeg','image/png','image/webp'].includes(file.type))
    return showAlert('certAlert', 'Solo PDF, JPG, PNG o WEBP.');
  if (file.size > 5 * 1024 * 1024)
    return showAlert('certAlert', 'El archivo no puede superar 5MB.');
  dashCertFile = file;
  document.getElementById('dashCertName').textContent = '📎 ' + file.name;
  document.getElementById('dashCertName').style.display = 'block';
  document.getElementById('uploadCertBtn').disabled = false;
}

async function submitCertificate() {

  const allowedTypes = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'application/pdf'
  ];

  if (!allowedTypes.includes(dashCertFile.type)) {
    showAlert('certAlert', 'Formato inválido.');
    return;
  }

  if (!dashCertFile) return;
  
  const btn = document.getElementById('uploadCertBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Subiendo...';
  
  try {
    const token = getToken();

    const formData = new FormData();
    formData.append('file', dashCertFile); 

    const res = await fetch(`${API}/users/upload-certificate`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${token}` 
      },  
      body: formData
    });
    
    const data = await res.json();
    if (!res.ok) {
      return showAlert('certAlert', typeof data.detail === 'string' ? data.detail : 'Error.');
    }

    showAlert('certAlert', 'Apto físico enviado. Quedará pendiente de verificación.', 'success');
    dashCertFile = null;
    document.getElementById('dashCertName').style.display = 'none';
    document.getElementById('dashCertInput').value = '';
    
  } catch (e) {
    showAlert('certAlert', 'Error al subir el archivo: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Enviar apto físico';
  }
}


let adminClassRooms = [];
let adminClassProfessors = [];
let adminClassFormProfessors = [];
let professorClassRequests = [];
let classAvailabilityListenersReady = false;

function apiErrorMessage(data, fallback = 'Error.') {
  if (typeof data?.detail === 'string') return data.detail;
  if (Array.isArray(data?.detail)) return data.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(' ');
  return fallback;
}

function combineDateAndTime(date, time) {
  return date && time ? new Date(`${date}T${time}`).toISOString() : null;
}

function professorName(professorId) {
  const professor = adminClassProfessors.find(p => p.id === professorId);
  return professor ? `${professor.name} ${professor.surname}` : '';
}

async function loadAdminClassData() {
  const professorsRes = await fetch(`${API}/classes/professors`, { headers: authH() });
  const professors = await professorsRes.json();

  if (!professorsRes.ok) throw new Error(apiErrorMessage(professors, 'No se pudieron cargar los profesores.'));

  adminClassProfessors = professors || [];
  bindClassAvailabilityInputs();
  await refreshClassAvailabilityOptions();
}

function bindClassAvailabilityInputs() {
  if (classAvailabilityListenersReady) return;

  ['classDate', 'classStartTime', 'classEndTime'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', refreshClassAvailabilityOptions);
  });

  classAvailabilityListenersReady = true;
}

function getClassFormTimeRange() {
  const classDate = document.getElementById('classDate').value;
  const startTime = document.getElementById('classStartTime').value;
  const endTime = document.getElementById('classEndTime').value;

  if (!classDate || !startTime || !endTime) return null;

  return {
    start_time: combineDateAndTime(classDate, startTime),
    end_time: combineDateAndTime(classDate, endTime)
  };
}

async function refreshClassAvailabilityOptions() {
  const roomSelect = document.getElementById('classRoom');
  const professorSelect = document.getElementById('classProfessor');
  const detailsFields = document.getElementById('classDetailsFields');
  const createButton = document.getElementById('createClassBtn');
  const range = getClassFormTimeRange();

  if (!range) {
    adminClassRooms = [];
    adminClassFormProfessors = [];
    if (roomSelect) roomSelect.innerHTML = '';
    if (professorSelect) professorSelect.innerHTML = '';
    if (detailsFields) detailsFields.style.display = 'none';
    if (createButton) createButton.disabled = true;
    return;
  }

  try {
    const params = new URLSearchParams(range);
    const [roomsRes, professorsRes] = await Promise.all([
      fetch(`${API}/classes/rooms?${params.toString()}`, { headers: authH() }),
      fetch(`${API}/classes/professors?${params.toString()}`, { headers: authH() })
    ]);

    const rooms = await roomsRes.json();
    const professors = await professorsRes.json();

    if (!roomsRes.ok) throw new Error(apiErrorMessage(rooms, 'No se pudieron cargar las salas disponibles.'));
    if (!professorsRes.ok) throw new Error(apiErrorMessage(professors, 'No se pudieron cargar los profesores disponibles.'));

    adminClassRooms = rooms || [];
    adminClassFormProfessors = professors || [];
    if (detailsFields) detailsFields.style.display = 'block';
    if (createButton) createButton.disabled = adminClassRooms.length === 0;

    roomSelect.innerHTML = adminClassRooms.length
      ? adminClassRooms.map(room => `
        <option value="${room.id}">${room.name} - cupo ${room.capacity}</option>
      `).join('')
      : '<option value="">No hay salas disponibles</option>';

    professorSelect.innerHTML = '<option value="">Sin profesor inicial</option>' + adminClassFormProfessors.map(professor => `
      <option value="${professor.id}">${professor.name} ${professor.surname}${professor.specialty ? ` - ${professor.specialty}` : ''}</option>
    `).join('');
  } catch (e) {
    adminClassRooms = [];
    adminClassFormProfessors = [];
    if (detailsFields) detailsFields.style.display = 'block';
    if (createButton) createButton.disabled = true;
    roomSelect.innerHTML = '<option value="">No se pudieron cargar salas</option>';
    professorSelect.innerHTML = '<option value="">No se pudieron cargar profesores</option>';
    showAlert('clasesAlert', e.message || 'No se pudo cargar disponibilidad.');
  }
}

async function fetchAvailableProfessorsForClasses(classes) {
  const entries = await Promise.all(classes.map(async c => {
    const res = await fetch(`${API}/classes/${c.id}/available-professors`, { headers: authH() });
    const data = await res.json();
    if (!res.ok) return [c.id, []];
    return [c.id, data || []];
  }));

  return Object.fromEntries(entries);
}

async function loadAdminClasses() {
  const container = document.getElementById('clasesTableContainer');
  container.innerHTML = '<div class="empty-state"><p>Cargando...</p></div>';

  try {
    const res = await fetch(`${API}/classes/`, { headers: authH() });
    const data = await res.json();

    if (!res.ok) {
      container.innerHTML = `<div class="empty-state"><p>${apiErrorMessage(data, 'Error al cargar las clases.')}</p></div>`;
      return;
    }

    if (!data.length) {
      container.innerHTML = '<div class="empty-state"><p>No hay clases programadas.</p></div>';
      return;
    }

    const availableProfessorsByClass = await fetchAvailableProfessorsForClasses(data);

    container.innerHTML = `
      <table class="data-table">
        <thead><tr><th>Actividad</th><th>Tipo</th><th>Sala</th><th>Inicio</th><th>Cupo</th><th>Profesor</th><th>Asignar</th><th>Acciones</th></tr></thead>
        <tbody>${data.map(c => {
          const assignedName = c.professor_name || professorName(c.professor_id);
          const availableProfessors = availableProfessorsByClass[c.id] || [];
          const hasAvailableProfessors = availableProfessors.length > 0;
          return `
          <tr>
            <td><strong>${(c.activity_type || '').replace(/_/g, ' ')}</strong></td>
            <td>${c.type || '-'}</td>
            <td>${c.rooms?.name || '-'}</td>
            <td>${formatDate(c.start_time)}</td>
            <td>${c.current_capacity}/${c.max_capacity}</td>
            <td>${assignedName || '<span style="color:var(--muted)">Sin asignar</span>'}</td>
            <td>
              <div style="display:flex;gap:6px;align-items:center;min-width:260px">
                <select id="assignProfessor_${c.id}" style="min-width:170px">
                  <option value="">${hasAvailableProfessors ? 'Seleccionar' : 'Sin disponibles'}</option>
                  ${availableProfessors.map(p => `<option value="${p.id}" ${p.id === c.professor_id ? 'selected' : ''}>${p.name} ${p.surname}</option>`).join('')}
                </select>
                <button class="action-btn" ${hasAvailableProfessors ? '' : 'disabled'} onclick="assignProfessorToClass('${c.id}')">Asignar</button>
              </div>
            </td>
            <td>
              <div style="display:flex;gap:6px;flex-wrap:wrap">
                <button class="action-btn" onclick="openStudentsModal('${c.id}', '${(c.activity_type || '').replace(/_/g, ' ')} ${formatDate(c.start_time)}')">Inscriptos</button>
                <button class="action-btn" onclick="openCapacityModal('${c.id}', ${c.current_capacity}, ${c.max_capacity})">Cupo</button>
                <button class="action-btn danger" onclick="cancelClass('${c.id}')">Cancelar</button>
              </div>
            </td>
          </tr>`;
        }).join('')}
        </tbody>
      </table>`;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p>${e.message || 'No se pudo cargar.'}</p></div>`;
  }
}

async function loadProfessorRequests() {
  const container = document.getElementById('professorRequestsContainer');
  container.innerHTML = '<div class="empty-state"><p>Cargando...</p></div>';

  try {
    const res = await fetch(`${API}/classes/requests/pending`, { headers: authH() });
    const data = await res.json();

    if (!res.ok) {
      container.innerHTML = `<div class="empty-state"><p>${apiErrorMessage(data, 'Error al cargar solicitudes.')}</p></div>`;
      return;
    }

    if (!data.length) {
      container.innerHTML = '<div class="empty-state"><p>No hay solicitudes pendientes.</p></div>';
      return;
    }

    container.innerHTML = `
      <table class="data-table">
        <thead><tr><th>Profesor</th><th>Clase</th><th>Sala</th><th>Horario</th><th>Acciones</th></tr></thead>
        <tbody>${data.map(req => {
          const clase = req.classes || {};
          const professor = req.users || {};
          return `
            <tr>
              <td><strong>${professor.name || ''} ${professor.surname || ''}</strong><span style="display:block;font-size:.78rem;color:var(--muted)">${professor.specialty || ''}</span></td>
              <td>${(clase.activity_type || '').replace(/_/g, ' ')} / ${clase.type || '-'}</td>
              <td>${clase.rooms?.name || '-'}</td>
              <td>${formatDate(clase.start_time)}</td>
              <td style="display:flex;gap:6px;flex-wrap:wrap">
                <button class="action-btn success" onclick="evaluateProfessorRequest('${req.class_id}', '${req.id}', 'ACEPTADA')">Aceptar</button>
                <button class="action-btn danger" onclick="rejectProfessorRequest('${req.class_id}', '${req.id}')">Rechazar</button>
              </td>
            </tr>`;
        }).join('')}
        </tbody>
      </table>`;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p>${e.message || 'No se pudo conectar.'}</p></div>`;
  }
}

async function loadMyProfessorRequests() {
  try {
    const res = await fetch(`${API}/classes/requests/me`, { headers: authH() });
    const data = await res.json();

    if (!res.ok) {
      professorClassRequests = [];
      showAlert('clasesAlert', apiErrorMessage(data, 'Error al cargar tus solicitudes.'));
      return;
    }

    professorClassRequests = data || [];
  } catch {
    professorClassRequests = [];
    showAlert('clasesAlert', 'No se pudieron cargar tus solicitudes.');
  }
}

function professorRequestForClass(classId) {
  return professorClassRequests.find(req => req.class_id === classId);
}

async function loadClases() {
  const u = getUser();
  const isAdmin = u?.rol === 'ADMINISTRATIVO';
  const isProfessor = u?.rol === 'PROFESOR';
  const adminForm = document.getElementById('adminClassForm');
  const requestsSection = document.getElementById('adminProfessorRequests');
  const title = document.getElementById('clasesTitle');
  const subtitle = document.getElementById('clasesSubtitle');
  const listTitle = document.getElementById('clasesListTitle');
  const container = document.getElementById('clasesTableContainer');

  if (isAdmin) {
    title.textContent = 'Gestion de clases';
    subtitle.textContent = 'Crea clases y asigna profesores';
    listTitle.innerHTML = '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg> Clases programadas';
    adminForm.style.display = 'block';
    requestsSection.style.display = 'block';
    container.innerHTML = '<div class="empty-state"><p>Cargando...</p></div>';

    loadProfessorRequests();

    try {
      await loadAdminClassData();
      await loadAdminClasses();
    } catch (e) {
      container.innerHTML = `<div class="empty-state"><p>${e.message || 'No se pudo cargar.'}</p></div>`;
    }
    return;
  }

  requestsSection.style.display = 'none';
  title.textContent = 'Clases disponibles';
  subtitle.textContent = isProfessor ? 'Solicita asignacion a clases programadas' : 'Explora y reserva clases';
  listTitle.innerHTML = '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg> Proximas clases';
  adminForm.style.display = 'none';
  container.innerHTML = '<div class="empty-state"><p>Cargando...</p></div>';

  try {
    if (isProfessor) await loadMyProfessorRequests();

    const res  = await fetch(isProfessor ? `${API}/classes/available-for-professor` : `${API}/classes/available`, { headers: authH() });
    if (!res.ok) { container.innerHTML = '<div class="empty-state"><p>Error al cargar las clases.</p></div>'; return; }
    const data = await res.json();
    if (!data.length) { container.innerHTML = '<div class="empty-state"><p>No hay clases disponibles.</p></div>'; return; }
    container.innerHTML = `
      <table class="data-table">
        <thead><tr><th>Actividad</th><th>Tipo</th><th>Inicio</th><th>Cupo</th><th>Profesor</th><th></th></tr></thead>
        <tbody>${data.map(c => {
          const request = isProfessor ? professorRequestForClass(c.id) : null;
          const hasProfessor = !!c.professor_id;
          const buttonLabel = request
            ? (request.status === 'PENDIENTE' ? 'Solicitada' : request.status === 'ACEPTADA' ? 'Aceptada' : 'Rechazada')
            : hasProfessor ? 'Asignada' : 'Solicitar';
          const buttonDisabled = isProfessor && (!!request || hasProfessor);
          const isMyClass = isProfessor && request?.status === 'ACEPTADA';
          return `
          <tr>
            <td><strong>${(c.activity_type || '').replace(/_/g, ' ')}</strong></td>
            <td>${c.type || '—'}</td>
            <td>${formatDate(c.start_time)}</td>
            <td>${c.current_capacity}/${c.max_capacity}</td>
            <td>${c.professor_name || '<span style="color:var(--muted)">Sin asignar</span>'}</td>
            <td style="display:flex;gap:6px">
              <button class="action-btn" ${buttonDisabled ? 'disabled' : ''} onclick="${isProfessor ? `requestProfessorClass('${c.id}')` : `reserveClass('${c.id}')`}">${isProfessor ? buttonLabel : 'Reservar'}</button>
              ${isMyClass ? `<button class="action-btn" onclick="openStudentsModal('${c.id}', '${(c.activity_type || '').replace(/_/g, ' ')}')">Inscriptos</button>` : ''}
            </td>
          </tr>`;
        }).join('')}
        </tbody>
      </table>`;
  } catch { container.innerHTML = '<div class="empty-state"><p>No se pudo cargar.</p></div>'; }
}

async function requestProfessorClass(classId) {
  try {
    const res = await fetch(`${API}/classes/${classId}/request`, {
      method: 'POST',
      headers: authH()
    });
    const data = await res.json();
    if (!res.ok) return showAlert('clasesAlert', apiErrorMessage(data, 'Error al enviar la solicitud.'));
    showAlert('clasesAlert', data.message || 'Solicitud enviada correctamente.', 'success');
    await loadClases();
  } catch {
    showAlert('clasesAlert', 'No se pudo conectar.');
  }
}

async function evaluateProfessorRequest(classId, requestId, status, reason = null) {
  try {
    const res = await fetch(`${API}/classes/${classId}/request/${requestId}`, {
      method: 'PATCH',
      headers: authH(),
      body: JSON.stringify({ status, reason })
    });
    const data = await res.json();
    if (!res.ok) {
      const targetAlert = status === 'RECHAZADA' ? 'rejectProfessorRequestAlert' : 'clasesAlert';
      showAlert(targetAlert, apiErrorMessage(data, 'Error al evaluar la solicitud.'));
      return false;
    }
    showAlert('clasesAlert', data.message || 'Solicitud evaluada correctamente.', 'success');
    await loadAdminClasses();
    await loadProfessorRequests();
    return true;
  } catch {
    const targetAlert = status === 'RECHAZADA' ? 'rejectProfessorRequestAlert' : 'clasesAlert';
    showAlert(targetAlert, 'No se pudo conectar.');
    return false;
  }
}

let rejectProfessorClassId = null;
let rejectProfessorRequestId = null;

function rejectProfessorRequest(classId, requestId) {
  rejectProfessorClassId = classId;
  rejectProfessorRequestId = requestId;
  document.getElementById('rejectProfessorRequestReason').value = '';
  document.getElementById('rejectProfessorRequestAlert').className = 'alert';
  document.getElementById('rejectProfessorRequestModal').classList.add('open');
}

function closeRejectProfessorRequestModal() {
  document.getElementById('rejectProfessorRequestModal').classList.remove('open');
  rejectProfessorClassId = null;
  rejectProfessorRequestId = null;
}

async function confirmRejectProfessorRequest() {
  const reason = document.getElementById('rejectProfessorRequestReason').value.trim();
  if (!reason || !reason.trim()) {
    showAlert('rejectProfessorRequestAlert', 'El rechazo debe incluir un motivo obligatorio.');
    return;
  }

  const ok = await evaluateProfessorRequest(
    rejectProfessorClassId,
    rejectProfessorRequestId,
    'RECHAZADA',
    reason
  );
  if (ok) closeRejectProfessorRequestModal();
}

async function createClassFromAdmin() {
  const room_id = document.getElementById('classRoom').value;
  const type = document.getElementById('classType').value;
  const activity_type = document.getElementById('classActivity').value;
  const max_capacity = Number(document.getElementById('classCapacity').value);
  const class_date = document.getElementById('classDate').value;
  const start_time = document.getElementById('classStartTime').value;
  const end_time = document.getElementById('classEndTime').value;
  const professor_id = document.getElementById('classProfessor').value || null;

  if (!room_id || !type || !activity_type || !max_capacity || !class_date || !start_time || !end_time) {
    return showAlert('clasesAlert', 'Completa todos los campos obligatorios.');
  }

  const apiStartTime = combineDateAndTime(class_date, start_time);
  const apiEndTime = combineDateAndTime(class_date, end_time);
  const selectedDate = new Date(`${class_date}T00:00`);
  const startMinutes = Number(start_time.slice(0, 2)) * 60 + Number(start_time.slice(3, 5));
  const endMinutes = Number(end_time.slice(0, 2)) * 60 + Number(end_time.slice(3, 5));

  if (selectedDate.getDay() === 0 || selectedDate.getDay() === 6) {
    return showAlert('clasesAlert', 'Las clases solo pueden programarse de lunes a viernes.');
  }

  if (startMinutes < 8 * 60 || endMinutes > 20 * 60) {
    return showAlert('clasesAlert', 'Las clases deben estar dentro del horario del centro: 08:00 a 20:00.');
  }

  if (new Date(apiEndTime) <= new Date(apiStartTime)) {
    return showAlert('clasesAlert', 'La hora de fin debe ser mayor a la hora de inicio.');
  }

  const btn = document.getElementById('createClassBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Creando...';

  try {
    const res = await fetch(`${API}/classes/`, {
      method: 'POST',
      headers: authH(),
      body: JSON.stringify({
        room_id,
        type,
        activity_type,
        is_scheduled: false,
        max_capacity,
        start_time: apiStartTime,
        end_time: apiEndTime,
        professor_id
      })
    });

    const data = await res.json();
    if (!res.ok) return showAlert('clasesAlert', apiErrorMessage(data, 'Error al crear la clase.'));

    showAlert('clasesAlert', data.message || 'La clase se creo exitosamente.', 'success');
    document.getElementById('classCapacity').value = '';
    document.getElementById('classDate').value = '';
    document.getElementById('classStartTime').value = '';
    document.getElementById('classEndTime').value = '';
    document.getElementById('classProfessor').value = '';
    await refreshClassAvailabilityOptions();
    await loadAdminClasses();
  } catch {
    showAlert('clasesAlert', 'No se pudo conectar.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Crear clase';
  }
}

async function cancelClass(classId) {
  if (!confirm('¿Cancelar esta clase? Esta acción no se puede deshacer.')) return;
  try {
    const res = await fetch(`${API}/classes/${classId}/cancel`, { method: 'PATCH', headers: authH() });
    const data = await res.json();
    if (res.status === 401) return handleUnauthorized();
    if (!res.ok) return showAlert('clasesAlert', apiErrorMessage(data, 'Error al cancelar la clase.'));
    showAlert('clasesAlert', data.message || 'Clase cancelada exitosamente.', 'success');
    await loadAdminClasses();
  } catch { showAlert('clasesAlert', 'No se pudo conectar.'); }
}

let capacityTargetId = null;

function openCapacityModal(classId, currentCapacity, maxCapacity) {
  capacityTargetId = classId;
  document.getElementById('currentCapacityText').textContent = `${currentCapacity} inscriptos / ${maxCapacity} cupo`;
  document.getElementById('newCapacityInput').value = maxCapacity;
  document.getElementById('capacityAlert').className = 'alert';
  document.getElementById('capacityModal').classList.add('open');
}

function closeCapacityModal() {
  document.getElementById('capacityModal').classList.remove('open');
  capacityTargetId = null;
}

async function confirmUpdateCapacity() {
  const newCapacity = Number(document.getElementById('newCapacityInput').value);
  if (!newCapacity || newCapacity < 1) return showAlert('capacityAlert', 'Ingresá un cupo válido mayor a 0.');
  try {
    const res = await fetch(`${API}/classes/${capacityTargetId}/capacity`, {
      method: 'PATCH',
      headers: authH(),
      body: JSON.stringify({ new_capacity: newCapacity })
    });
    const data = await res.json();
    if (!res.ok) return showAlert('capacityAlert', apiErrorMessage(data, 'Error al modificar el cupo.'));
    showAlert('clasesAlert', data.message || 'Cupo actualizado.', 'success');
    closeCapacityModal();
    await loadAdminClasses();
  } catch { showAlert('capacityAlert', 'No se pudo conectar.'); }
}

async function openStudentsModal(classId, className) {
  document.getElementById('studentsModalTitle').textContent = `Inscriptos — ${className}`;
  document.getElementById('studentsContainer').innerHTML = '<div class="empty-state"><p>Cargando...</p></div>';
  document.getElementById('studentsModal').classList.add('open');
  try {
    const res = await fetch(`${API}/classes/${classId}/students`, { headers: authH() });
    const data = await res.json();
    if (!res.ok) {
      document.getElementById('studentsContainer').innerHTML = `<div class="empty-state"><p>${apiErrorMessage(data, 'Error al cargar.')}</p></div>`;
      return;
    }
    if (!data.length) {
      document.getElementById('studentsContainer').innerHTML = '<div class="empty-state"><p>No hay inscriptos en esta clase.</p></div>';
      return;
    }
    document.getElementById('studentsContainer').innerHTML = `
      <table class="data-table">
        <thead><tr><th>Nombre</th><th>Email</th><th>Teléfono</th></tr></thead>
        <tbody>${data.map(s => {
          const u = s.users || s;
          return `<tr>
            <td><strong>${u.name || ''} ${u.surname || ''}</strong></td>
            <td style="font-size:.82rem">${u.email || '—'}</td>
            <td style="font-size:.82rem">${u.phone || '—'}</td>
          </tr>`;
        }).join('')}
        </tbody>
      </table>`;
  } catch {
    document.getElementById('studentsContainer').innerHTML = '<div class="empty-state"><p>No se pudo conectar.</p></div>';
  }
}

function closeStudentsModal() {
  document.getElementById('studentsModal').classList.remove('open');
}

async function assignProfessorToClass(classId) {
  const professor_id = document.getElementById(`assignProfessor_${classId}`).value;
  if (!professor_id) return showAlert('clasesAlert', 'Selecciona un profesor.');

  try {
    const res = await fetch(`${API}/classes/${classId}/assign-professor`, {
      method: 'PATCH',
      headers: authH(),
      body: JSON.stringify({ professor_id })
    });

    const data = await res.json();
    if (!res.ok) return showAlert('clasesAlert', apiErrorMessage(data, 'Error al asignar profesor.'));

    showAlert('clasesAlert', data.message || 'Se asigno el profesor correctamente.', 'success');
    await loadAdminClasses();
  } catch {
    showAlert('clasesAlert', 'No se pudo conectar.');
  }
}

async function reserveClass(classId) {
  try {
    const res  = await fetch(`${API}/reservations`, { method:'POST', headers:authH(), body:JSON.stringify({ class_id: classId }) });
    const data = await res.json();
    if (!res.ok) return showAlert('clasesAlert', typeof data.detail === 'string' ? data.detail : 'Error al reservar.');
    showAlert('clasesAlert', '¡Reserva realizada!', 'success');
    loadClases();
  } catch { showAlert('clasesAlert', 'No se pudo conectar.'); }
}

async function loadReservas() {
  const container = document.getElementById('reservasContainer');
  container.innerHTML = '<div class="empty-state"><p>Cargando...</p></div>';
  try {
    const res  = await fetch(`${API}/reservations/me`, { headers: authH() });
    if (!res.ok) { container.innerHTML = '<div class="empty-state"><p>Error al cargar.</p></div>'; return; }
    const data = await res.json();
    if (!data.length) { container.innerHTML = '<div class="empty-state"><p>No tenés reservas activas.</p></div>'; return; }
    container.innerHTML = `
      <table class="data-table">
        <thead><tr><th>Actividad</th><th>Inicio</th><th>Estado</th><th>Pago</th><th></th></tr></thead>
        <tbody>${data.map(r => `
          <tr>
            <td>${(r.activity_type || '').replace('_', ' ') || '—'}</td>
            <td>${formatDate(r.start_time)}</td>
            <td>${badge(r.status, { CONFIRMADA:'Confirmada', CANCELADA:'Cancelada', AUSENTE:'Ausente' })}</td>
            <td>${badge(r.payment_status, { PENDIENTE:'Pendiente', SENADO_50:'50% señado', PAGADO:'Pagado', DEVUELTO:'Devuelto', CREDITO_APLICADO:'Crédito' })}</td>
            <td>${r.status === 'CONFIRMADA' ? `<button class="action-btn danger" onclick="cancelReserva('${r.id}')">Cancelar</button>` : ''}</td>
          </tr>`).join('')}
        </tbody>
      </table>`;
  } catch { container.innerHTML = '<div class="empty-state"><p>No se pudo cargar.</p></div>'; }
}

async function cancelReserva(id) {
  if (!confirm('¿Confirmás la cancelación? Se aplicarán las políticas del centro.')) return;
  try {
    const res  = await fetch(`${API}/reservations/${id}/cancel`, { method:'POST', headers:authH() });
    const data = await res.json();
    if (!res.ok) return showAlert('clasesAlert', typeof data.detail === 'string' ? data.detail : 'Error.');
    showAlert('clasesAlert', 'Reserva cancelada.', 'success');
    loadReservas();
  } catch { showAlert('clasesAlert', 'No se pudo conectar.'); }
}


let searchTimeout = null;
let blockTargetId = null;

let pubSearchTimeout = null;

// Muestra los filtros correctos según el rol al abrir el panel
function initUserPanel() {
  const u = getUser();
  if (!u) return;

  if (u.rol === 'ADMINISTRATIVO') {
    document.getElementById('adminFilters').style.display  = 'block';
    document.getElementById('publicFilters').style.display = 'none';
    loadUsers();   // carga todos por defecto
  } else {
    document.getElementById('adminFilters').style.display  = 'none';
    document.getElementById('publicFilters').style.display = 'block';
    // No precarga — espera que el usuario escriba o filtre
    document.getElementById('usersTableContainer').innerHTML = `
      <div class="empty-state">
        <svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
        <p>Buscá por nombre o filtrá por rol para encontrar usuarios.</p>
      </div>`;
    document.getElementById('userCount').textContent = '';
  }
}

// ── Admin: carga con filtros ──────────────────────────────────
async function loadUsers(name = '', role = '', status = '') {
  const container = document.getElementById('usersTableContainer');
  container.innerHTML = '<div class="empty-state"><p>Cargando...</p></div>';

  try {
    const params = new URLSearchParams();
    if (name)   params.append('name',   name);
    if (role)   params.append('role',    role);
    if (status) params.append('status', status);

    const url = `${API}/staff/users${params.toString() ? '?' + params.toString() : ''}`;
    const res  = await fetch(url, { headers: authH() });
    const data = await res.json();

    if (!res.ok) { container.innerHTML = `<div class="empty-state"><p>${data.detail || 'Error.'}</p></div>`; return; }

    renderUsersTable(data, true);
  } catch {
    container.innerHTML = '<div class="empty-state"><p>No se pudo conectar.</p></div>';
  }
}

function applyAdminFilters() {
  const name   = document.getElementById('searchName').value.trim();
  const role   = document.getElementById('filterRole').value;
  const status = document.getElementById('filterStatus').value;
  loadUsers(name, role, status);
}

// Al limpiar como admin → muestra todos de nuevo
function clearAdminFilters() {
  document.getElementById('searchName').value   = '';
  document.getElementById('filterRole').value   = '';
  document.getElementById('filterStatus').value = '';
  loadUsers();  // sin filtros = todos los usuarios
}

function onSearchInput() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => applyAdminFilters(), 400);
}

// ── Público (recep/prof/cliente): carga con filtros ───────────
async function loadPublicUsers(name = '', role = '') {
  const container = document.getElementById('usersTableContainer');
  const countEl   = document.getElementById('userCount');

  if (!name && !role) {
    container.innerHTML = '<div class="empty-state"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg><p>Escribí un nombre o seleccioná un rol para buscar.</p></div>';
    countEl.textContent = '';
    return;
  }

  container.innerHTML = '<div class="empty-state"><p>Buscando...</p></div>';

  try {
    const params = new URLSearchParams();
    if (name) params.append('name', name);
    if (role) params.append('role', role);

    const res  = await fetch(`${API}/users/public-search?${params.toString()}`, { headers: authH() });
    const data = await res.json();

    if (!res.ok) { container.innerHTML = `<div class="empty-state"><p>${data.detail || 'Error.'}</p></div>`; return; }

    const currentUser = getUser();
    const filtered = data.filter(u => u.id !== currentUser?.id);

    countEl.textContent = `${filtered.length} resultado${filtered.length !== 1 ? 's' : ''}`;

    if (!filtered.length) {
      container.innerHTML = '<div class="empty-state"><p>No se encontraron usuarios.</p></div>';
      return;
    }

    container.innerHTML = `
      <table class="data-table">
        <thead><tr><th>Nombre</th><th>Rol</th><th></th></tr></thead>
        <tbody>${filtered.map(u => `
          <tr>
            <td><strong style="color:var(--teal-dim)">${u.name} ${u.surname}</strong></td>
            <td>${badge(u.rol, ROL_LABELS)}</td>
            <td><button class="action-btn" onclick="openUserProfile('${u.id}')">Ver perfil</button></td>
          </tr>`).join('')}
        </tbody>
      </table>`;
  } catch {
    container.innerHTML = '<div class="empty-state"><p>No se pudo conectar.</p></div>';
  }
}

function applyPublicFilters() {
  const name = document.getElementById('publicSearchName').value.trim();
  const role = document.getElementById('publicFilterRole').value;
  loadPublicUsers(name, role);
}

// HU-36/37: limpiar filtros vista pública → limpia la tabla
function clearPublicFilters() {
  document.getElementById('publicSearchName').value  = '';
  document.getElementById('publicFilterRole').value  = '';
  document.getElementById('userCount').textContent   = '';
  document.getElementById('usersTableContainer').innerHTML = `
    <div class="empty-state">
      <svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
      <p>Buscá por nombre o filtrá por rol para encontrar usuarios.</p>
    </div>`;
}

function onPublicSearchInput() {
  clearTimeout(pubSearchTimeout);
  pubSearchTimeout = setTimeout(() => applyPublicFilters(), 400);
}

// ── Render tabla (compartido) ─────────────────────────────────
function renderUsersTable(data, isAdmin) {
  const currentUser = getUser();
  const container = document.getElementById('usersTableContainer');
  data = data.filter(u => u.id !== currentUser.id);
  document.getElementById('userCount').textContent =
    `${data.length} resultado${data.length !== 1 ? 's' : ''}`;

  if (!data.length) {
    container.innerHTML = `
      <div class="empty-state">
        <svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
        <p>No se encontraron usuarios.</p>
      </div>`;
    return;
  }

  container.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>Nombre</th>
        ${isAdmin ? '<th>Email</th><th>DNI</th>' : ''}
        <th>Rol</th>
        ${isAdmin ? '<th>Estado</th>' : ''}
        <th></th>
      </tr></thead>
      <tbody>${data.map(u => `
        <tr>
          <td><strong style="color:var(--teal-dim)">${u.name} ${u.surname}</strong></td>
          ${isAdmin ? `<td style="font-size:.82rem">${u.email || '—'}</td><td>${u.dni || '—'}</td>` : ''}
          <td>${badge(u.rol, ROL_LABELS)}</td>
          ${isAdmin ? `<td>${badge(u.account_status, STATUS_LABELS)}</td>` : ''}
          <td style="display:flex;gap:6px">
            <button class="action-btn" onclick="openUserProfile('${u.id}')">Ver perfil</button>
            ${isAdmin
              ? (u.account_status === 'ACTIVA'
                  ? `<button class="action-btn danger" onclick="openBlockModal('${u.id}','${u.name} ${u.surname}')">Suspender</button>`
                  : `<button class="action-btn success" onclick="unblockUser('${u.id}')">Reactivar</button>`)
              : ''}
          </td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

// ── Ver perfil completo ───────────────────────────────────────
async function openUserProfile(userId) {
  document.getElementById('userProfileModal').classList.add('open');
  document.getElementById('modalUserName').textContent = 'Cargando...';
  document.getElementById('modalUserBody').innerHTML   = '';
  document.getElementById('modalActions').innerHTML    = '';

  const currentUser = getUser();
  const isAdmin = currentUser?.rol === 'ADMINISTRATIVO';

  const url = isAdmin ? `${API}/users/${userId}` : `${API}/users/public/${userId}`;

  try {
    const res = await fetch(url, { headers: authH() });
    const u   = await res.json();
    if (!res.ok) { document.getElementById('modalUserName').textContent = 'Error'; return; }

    document.getElementById('modalUserName').textContent = `${u.name} ${u.surname}`;

    let fields = [];

    if (isAdmin) {
      const isEmp = EMPLOYEE_ROLES.includes(u.rol);
      fields = [
        ['Email',        u.email        || '—'],
        ['DNI',          u.dni          || '—'],
        ['Teléfono',     u.phone        || '—'],
        ['Rol',          badge(u.rol, ROL_LABELS)],
        ['Estado',       badge(u.account_status, STATUS_LABELS)],
        ['Género',       u.gender       || '—'],
        ['Edad',         u.age ? `${u.age} años` : '—'],
        ['Dirección',    u.address      || '—'],
        ...(!isEmp ? [['Apto físico', badge(u.physical_certificate, CERT_LABELS)]] : []),
        ...(u.specialty ? [['Especialidad', u.specialty]] : []),
        ...(u.rol === 'ABONADO' ? [['Créditos', `${u.credits ?? 0}/3`]] : []),
      ];

      const actions = document.getElementById('modalActions');
      if (u.account_status === 'ACTIVA') {
        actions.innerHTML = `<button class="btn btn-sm btn-danger" onclick="closeUserModal();openBlockModal('${u.id}','${u.name} ${u.surname}')">Reactivar cuenta</button>`;
      } else {
        actions.innerHTML = `<button class="btn btn-sm" onclick="unblockFromModal('${u.id}')">Reactivar cuenta</button>`;
      }

    } else {
      fields = [
        ['Nombre',  `${u.name} ${u.surname}`],
        ['Rol',     badge(u.rol, ROL_LABELS)],
        ['Edad',    u.age ? `${u.age} años` : '—'],
        ['Género', u.gender || '—'],
        ...(u.rol === 'ABONADO' ? [['Tipo', badge('ABONADO', ROL_LABELS)]] : []),
      ];
    }

    document.getElementById('modalUserBody').innerHTML = fields.map(([label, value]) =>
      `<div class="profile-field"><span class="profile-field-label">${label}</span><span class="profile-field-value">${value}</span></div>`
    ).join('');

  } catch { document.getElementById('modalUserName').textContent = 'Error al cargar.'; }
}

function closeUserModal() { document.getElementById('userProfileModal').classList.remove('open'); }

async function unblockUser(userId) {
  if (!confirm('¿Reactivar esta cuenta?')) return;
  try {
    const res  = await fetch(`${API}/staff/unblock_user/${user_id}`, { method:'POST', headers:authH() });
    const data = await res.json();
    if (!res.ok) return showAlert('usuariosAlert', typeof data.detail === 'string' ? data.detail : 'Error.');
    showAlert('usuariosAlert', 'Cuenta reactivada.', 'success');
    filterByRole();
  } catch { showAlert('usuariosAlert', 'No se pudo conectar.'); }
}

async function unblockFromModal(userId) {
  closeUserModal();
  await unblockUser(userId);
}
function openBlockModal(userId, userName) {
  blockTargetId = userId;
  document.getElementById('blockModalTitle').textContent = `Suspender a ${userName}`;
  document.getElementById('blockReason').value = '';
  document.getElementById('blockModal').classList.add('open');
}
function closeBlockModal() { document.getElementById('blockModal').classList.remove('open'); blockTargetId = null; }

async function confirmBlock() {
  const reason = document.getElementById('blockReason').value.trim();
  if (!reason) return showAlert('usuariosAlert', 'El motivo es obligatorio.');
  try {
    const res  = await fetch(`${API}/staff/block_user/${blockTargetId}`, { method:'POST', headers:authH(), body:JSON.stringify({ reason }) });
    const data = await res.json();
    if (!res.ok) return showAlert('usuariosAlert', typeof data.detail === 'string' ? data.detail : 'Error.');
    closeBlockModal();
    showAlert('usuariosAlert', 'Usuario suspendido.', 'success');
    filterByRole();
  } catch { showAlert('usuariosAlert', 'No se pudo conectar.'); }
}


let rejectTargetId = null;

async function loadCertificados() {
  const container = document.getElementById('pendingCertsContainer');
  container.innerHTML = '<div class="empty-state"><p>Cargando...</p></div>';
  try {
    const res  = await fetch(`${API}/staff/pending-certificates`, { headers: authH() });
    if (!res.ok) { container.innerHTML = '<div class="empty-state"><p>Error al cargar.</p></div>'; return; }
    const data = await res.json();
    if (!data.length) { container.innerHTML = '<div class="empty-state"><svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><p>No hay aptos físicos pendientes</p></div>'; return; }
    container.innerHTML = `
      <table class="data-table">
        <thead><tr><th>Cliente</th><th>DNI</th><th>Archivo</th><th>Acciones</th></tr></thead>
        <tbody>${data.map(u => `
          <tr>
            <td><strong>${u.name} ${u.surname}</strong><span style="display:block;font-size:.78rem;color:var(--muted)">${u.email}</span></td>
            <td>${u.dni}</td>
            <td>${u.physical_certificate_url ? `<a href="${u.physical_certificate_url}" target="_blank" style="color:var(--teal);font-size:.85rem">Ver archivo ↗</a>` : '—'}</td>
            <td style="display:flex;gap:6px">
              <button class="action-btn success" onclick="approveCert('${u.id}')">Aprobar</button>
              <button class="action-btn danger"  onclick="openRejectModal('${u.id}')">Rechazar</button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>`;
  } catch { container.innerHTML = '<div class="empty-state"><p>No se pudo cargar.</p></div>'; }
}

async function viewCert(userId) {
  try {
    const res = await fetch(
      `${API}/staff/certificates/${userId}/view`,
      { headers: authH() }
    );

    if (!res.ok) {
      showAlert('usuariosAlert', 'No se pudo cargar el archivo.');
      return;
    }

    const data = await res.json();
    window.open(data.url, '_blank');

  } catch {
    showAlert('usuariosAlert', 'Error al abrir el archivo.');
  }
}

async function approveCert(userId) {
  try {
    const res = await fetch(`${API}/staff/approve_certificate`, { 
      method: 'POST', 
      headers: {
        ...authH(), 
        'Content-Type': 'application/json' 
      }, 
      body: JSON.stringify({ id: userId }) 
    });
    const data = await res.json();
    if (!res.ok) return showAlert('usuariosAlert', typeof data.detail === 'string' ? data.detail : 'Error.');
    showAlert('usuariosAlert', 'Apto físico aprobado.', 'success');
    loadCertificados();
  } catch { showAlert('usuariosAlert', 'No se pudo conectar.'); }
}

function openRejectModal(userId) { rejectTargetId = userId; document.getElementById('rejectReason').value = ''; document.getElementById('rejectModal').classList.add('open'); }
function closeRejectModal() { document.getElementById('rejectModal').classList.remove('open'); rejectTargetId = null; }

async function confirmReject() {
  const reason = document.getElementById('rejectReason').value.trim();
  if (!reason) return alert('El motivo es obligatorio.');
  try {
    const res = await fetch(`${API}/staff/reject_certificate`, { 
      method: 'POST', 
      headers: {
        ...authH(),
        'Content-Type': 'application/json' 
      }, 
      body: JSON.stringify({ id: rejectTargetId, reason }) 
    });
    if (!res.ok) return alert(typeof data.detail === 'string' ? data.detail : 'Error.');
    closeRejectModal();
    loadCertificados();
  } catch { alert('No se pudo conectar.'); }
}


async function loadSolicitudes() {
  const container = document.getElementById('solicitudesContainer');
  container.innerHTML = '<div class="empty-state"><p>Cargando...</p></div>';
  try {
    const res  = await fetch(`${API}/staff/pending_unblocks`, { headers: authH() });
    const data = await res.json();
    if (!res.ok) { container.innerHTML = `<div class="empty-state"><p>${data.detail || 'Error.'}</p></div>`; return; }
    if (!data.length) {
      container.innerHTML = '<div class="empty-state"><svg viewBox="0 0 24 24"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg><p>No hay solicitudes pendientes</p></div>';
      return;
    }
    container.innerHTML = `
      <table class="data-table">
        <thead><tr><th>Usuario</th><th>Motivo del reclamo</th><th>Fecha</th><th>Acciones</th></tr></thead>
        <tbody>${data.map(s => {
          // 💡 Limpiamos el texto acá en el Front para quitarle el prefijo feo
          const cleanReason = s.reason ? s.reason.replace('SOLICITUD DE DESBLOQUEO: ', '') : '—';

          return `
          <tr>
            <td>
              <strong style="color:var(--teal-dim)">${s.name} ${s.surname}</strong>
              <span style="display:block;font-size:.78rem;color:var(--muted)">${s.email || ''}</span>
            </td>
            <td style="font-size:.85rem">${cleanReason}</td>
            <td style="font-size:.82rem;color:var(--muted)">${s.created_at ? new Date(s.created_at).toLocaleDateString('es-AR') : '—'}</td>
            <td style="display:flex;gap:6px">
              <button class="action-btn success" onclick="approveUnlock('${s.user_id}','${s.user_id}')">Aprobar</button>
              <button class="action-btn danger"  onclick="openRejectUnlockModal('${s.user_id}','${s.user_id}')">Rechazar</button>
            </td>
          </tr>`;
        }).join('')}
        </tbody>
      </table>`;
  } catch { container.innerHTML = '<div class="empty-state"><p>No se pudo conectar.</p></div>'; }
}

async function loadReactivacionPanel() {
  const u = getUser();
  const statusEl = document.getElementById('reactivacionStatus');
  const formEl   = document.getElementById('reactivacionForm');

  statusEl.innerHTML = `
    <div class="field-row">
      <span class="field-label">Estado actual</span>
      <span class="field-value">${badge(u.account_status, STATUS_LABELS)}</span>
    </div>`;

  if (u.account_status !== 'SUSPENDIDA') {
    formEl.innerHTML = '<p style="color:var(--muted);font-size:.88rem">Tu cuenta está activa. No necesitás enviar una solicitud.</p>';
    return;async function loadSolicitudes() {
  const container = document.getElementById('solicitudesContainer');
  container.innerHTML = '<div class="empty-state"><p>Cargando...</p></div>';
  try {
    const res  = await fetch(`${API}/staff/pending_unblocks`, { headers: authH() });
    const data = await res.json();
    if (!res.ok) { container.innerHTML = `<div class="empty-state"><p>${data.detail || 'Error.'}</p></div>`; return; }
    if (!data.length) {
      container.innerHTML = '<div class="empty-state"><svg viewBox="0 0 24 24"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg><p>No hay solicitudes pendientes</p></div>';
      return;
    }
    container.innerHTML = `
      <table class="data-table">
        <thead><tr><th>Usuario</th><th>Motivo del reclamo</th><th>Fecha</th><th>Acciones</th></tr></thead>
        <tbody>${data.map(s => {
          // 💡 Limpiamos el texto acá en el Front para quitarle el prefijo feo
          const cleanReason = s.reason ? s.reason.replace('SOLICITUD DE DESBLOQUEO: ', '') : '—';

          return `
          <tr>
            <td>
              <strong style="color:var(--teal-dim)">${s.name} ${s.surname}</strong>
              <span style="display:block;font-size:.78rem;color:var(--muted)">${s.email || ''}</span>
            </td>
            <td style="font-size:.85rem">${cleanReason}</td>
            <td style="font-size:.82rem;color:var(--muted)">${s.created_at ? new Date(s.created_at).toLocaleDateString('es-AR') : '—'}</td>
            <td style="display:flex;gap:6px">
              <button class="action-btn success" onclick="approveUnlock('${s.user_id}','${s.user_id}')">Aprobar</button>
              <button class="action-btn danger"  onclick="openRejectUnlockModal('${s.user_id}','${s.user_id}')">Rechazar</button>
            </td>
          </tr>`;
        }).join('')}
        </tbody>
      </table>`;
  } catch { container.innerHTML = '<div class="empty-state"><p>No se pudo conectar.</p></div>'; }
}
  }

}

async function submitUnblockRequest() {
  const reason = document.getElementById('unblockReason').value.trim();
  if (!reason) return showAlert('reactivacionAlert', 'Ingresá el motivo del reclamo.');

  try {
    const res = await fetch(`${API}/users/request-unblock`, {
      method: 'POST',
      headers: {
        ...authH(),
        'Content-Type': 'application/json' 
      },
      body: JSON.stringify({ reason })
    });
    const data = await res.json();
    if (!res.ok) return showAlert('reactivacionAlert', typeof data.detail === 'string' ? data.detail : 'Error.');

    showAlert('reactivacionAlert', 'Solicitud enviada. El equipo del centro la revisará pronto.', 'success');
    document.getElementById('unblockReason').value = '';
    document.getElementById('reactivacionForm').innerHTML =
      '<p style="color:var(--muted);font-size:.88rem">Solicitud enviada correctamente. Aguardá la respuesta del equipo.</p>';
  } catch {
    showAlert('reactivacionAlert', 'No se pudo conectar.');
  }
}

async function approveUnlock(userId) {
  try {
    const res  = await fetch(`${API}/staff/approve_unblock_request/${userId}`, { method:'POST', headers:authH() });
    const data = await res.json();
    if (!res.ok) return showAlert('solicitudesAlert', typeof data.detail === 'string' ? data.detail : 'Error.');
    showAlert('solicitudesAlert', 'Cuenta reactivada.', 'success');
    loadSolicitudes();
  } catch { showAlert('solicitudesAlert', 'No se pudo conectar.'); }
}


let rejectUnlockTargetId = null;
function openRejectUnlockModal(userId) {
  rejectUnlockTargetId = userId;
  document.getElementById('rejectUnlockReason').value = '';
  document.getElementById('rejectUnlockModal').classList.add('open');
}

function closeRejectUnlockModal() {
  document.getElementById('rejectUnlockModal').classList.remove('open');
  rejectUnlockTargetId = null;
}

async function confirmRejectUnlock() {
  const reason = document.getElementById('rejectUnlockReason').value.trim();
  if (!reason) return alert('El motivo es obligatorio.');
  try {
    const res  = await fetch(`${API}/staff/reject_unblock_request/${rejectUnlockTargetId}`, { method:'POST', headers:authH(), body:JSON.stringify({ reason }) });
    const data = await res.json();
    if (!res.ok) return alert(typeof data.detail === 'string' ? data.detail : 'Error.');
    closeRejectUnlockModal();
    loadSolicitudes();
  } catch { alert('No se pudo conectar.'); }
}

function clearValue(id) {
  const el = document.getElementById(id);
  if (el) el.value = '';
}

function openRegisterModal() {
  document.getElementById('registerType').value = 'cliente';
  document.getElementById('employeeFields').style.display = 'none';

  const today = new Date().toISOString().split('T')[0];
  document.getElementById('rBirthdate').max = today;

  clearValue('rName');
  clearValue('rSurname');
  clearValue('rEmail');
  clearValue('rDni');
  clearValue('rBirthdate');
  clearValue('rSpecialty');

  document.getElementById('registerUserAlert').className = 'alert';
  document.getElementById('registerUserModal').classList.add('open');
}

function closeRegisterModal() { document.getElementById('registerUserModal').classList.remove('open'); }

function setDisplay(id, value) {
  const el = document.getElementById(id);
  if (el) el.style.display = value;
}

function onRegisterTypeChange() {
  const type = document.getElementById('registerType').value;

  setDisplay('employeeFields', type === 'empleado' ? 'block' : 'none');
  setDisplay('rPhoneGroup',    type === 'cliente'  ? 'block' : 'none');

  if (type === 'empleado') onRolChange();
}

function onRolChange() {
  const rol = document.getElementById('rRol')?.value;
  if (!rol) return;

  setDisplay('specialtyGroup', rol === 'ADMINISTRATIVO' ? 'none' : 'block');

}
async function submitRegisterUser() {
  const type = document.getElementById('registerType').value;
  const name    = document.getElementById('rName').value.trim();
  const surname = document.getElementById('rSurname').value.trim();
  const email   = document.getElementById('rEmail').value.trim();
  const birthdate = document.getElementById('rBirthdate').value;

  if (!birthdate)
    return showAlert(
      'registerUserAlert',
      'La fecha de nacimiento es obligatoria.'
    );

  const dni     = document.getElementById('rDni').value.trim();

  if (!name || !surname || !email || !dni)
    return showAlert('registerUserAlert', 'Completá todos los campos obligatorios.');

  let url  = '';
  let body = {};

  if (type === 'cliente') {
    url  = `${API}/staff/register`;
    body = {
      name,
      surname,
      email,
      dni,
      birth_date: birthdate
  };
  } else {
    const rol       = document.getElementById('rRol').value;
    const specialty = document.getElementById('rSpecialty').value.trim();
    if (rol !== 'ADMINISTRATIVO' && !specialty)
      return showAlert('registerUserAlert', 'La especialidad es obligatoria para este rol.');
      url  = `${API}/staff/register_employee`;
      body = {
          name,
          surname,
          email,
          dni,
          rol,
          specialty: specialty || null,
          birth_date: birthdate
    };
}
  

  const btn = document.getElementById('registerUserBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Registrando...';

  try {
    const res  = await fetch(url, { method:'POST', headers:authH(), body:JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) return showAlert('registerUserAlert', typeof data.detail === 'string' ? data.detail : 'Error al registrar.');
    showAlert('registerUserAlert', 'Usuario registrado exitosamente. Se enviará la contraseña por mail.', 'success');
    setTimeout(() => closeRegisterModal(), 2500);
    filterByRole();
  } catch { showAlert('registerUserAlert', 'No se pudo conectar.'); }
  finally { btn.disabled = false; btn.textContent = 'Registrar'; }
}

// SEGURIDAD

async function handleChangePassword() {
  const np = document.getElementById('newPw').value;
  const cp = document.getElementById('confirmPw').value;
  if (!np || !cp)      return showAlert('pwAlert', 'Completá ambos campos.');
  if (np.length < 6)   return showAlert('pwAlert', 'Mínimo 6 caracteres.');
  if (np !== cp)       return showAlert('pwAlert', 'Las contraseñas no coinciden.');
  try {
    const res  = await fetch(`${API}/users/me/change-password`, { method:'POST', headers:authH(), body:JSON.stringify({ new_password:np, confirm_new_password:cp }) });
    const data = await res.json();
    if (!res.ok) return showAlert('pwAlert', typeof data.detail === 'string' ? data.detail : 'Error.');
    showAlert('pwAlert', 'Contraseña actualizada correctamente.', 'success');
    document.getElementById('newPw').value = '';
    document.getElementById('confirmPw').value = '';
  } catch { showAlert('pwAlert', 'No se pudo conectar.'); }
}


// LOGOUT

async function handleLogout() {
  try { await fetch(`${API}/auth/logout`, { method:'POST', headers:authH() }); } catch {}
  clearAuth();
  window.location.href = 'login.html';
}

// INIT

(async function init() {
  if (!getToken()) { window.location.href = 'login.html'; return; }
  await loadDashboard();
})();
