// CONFIG

const API = 'http://localhost:8000';

// HELPERS
const getToken  = () => localStorage.getItem('token');
const setToken  = t  => localStorage.setItem('token', t);
const clearAuth = () => { localStorage.removeItem('token'); localStorage.removeItem('currentUser'); };

function showAlert(id, msg, type = 'error') {
  const el = document.getElementById(id);
  if (!el) return;
  const text = typeof msg === 'string' ? msg : JSON.stringify(msg);
  el.textContent = text;
  el.className = `alert ${type} show`;
  setTimeout(() => { if (el) el.classList.remove('show'); }, 5000);
}

function setLoading(id, on, label = '') {
  const b = document.getElementById(id);
  if (!b) return;
  b.disabled = on;
  b.innerHTML = on ? `<span class="spinner"></span>Procesando...` : label;
}

// NAVEGACIÓN ENTRE VISTAS

function switchTab(tab) {
  ['loginView', 'registerView', 'recoveryView'].forEach(id => {
    document.getElementById(id).classList.remove('active');
  });
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('alertBox').className = 'alert';

  if (tab === 'login') {
    document.getElementById('loginView').classList.add('active');
    document.querySelectorAll('.tab')[0].classList.add('active');
  } else {
    document.getElementById('registerView').classList.add('active');
    document.querySelectorAll('.tab')[1].classList.add('active');
  }
}

function showRecovery() {
  ['loginView', 'registerView', 'recoveryView'].forEach(id => {
    document.getElementById(id).classList.remove('active');
  });
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('recoveryView').classList.add('active');
}


// LOGIN

async function handleLogin() {
  const email    = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;

  if (!email || !password) return showAlert('alertBox', 'Completá todos los campos.');

  setLoading('loginBtn', true, 'Ingresar');
  try {
    const res  = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (!res.ok) {
      const msg = typeof data.detail === 'string' ? data.detail : 'Error al iniciar sesión.';
      return showAlert('alertBox', msg);
    }

    const token = data.token || data.Token || data.access_token;
    if (!token) return showAlert('alertBox', 'El servidor no devolvió un token válido.');

    setToken(token);
    window.location.href = 'dashboard.html';

  } catch {
    showAlert('alertBox', 'No se pudo conectar con el servidor.');
  } finally {
    setLoading('loginBtn', false, 'Ingresar');
  }
}

// REGISTRO

async function handleRegister() {
  const body = {
    name:     document.getElementById('regName').value.trim(),
    surname:  document.getElementById('regSurname').value.trim(),
    email:    document.getElementById('regEmail').value.trim(),
    dni:      document.getElementById('regDni').value.trim(),
    password: document.getElementById('regPassword').value,
  };

  if (!body.name || !body.surname || !body.email || !body.dni || !body.password)
    return showAlert('alertBox', 'Completá todos los campos obligatorios.');
  if (body.password.length < 6)
    return showAlert('alertBox', 'La contraseña debe tener al menos 6 caracteres.');

  setLoading('registerBtn', true, 'Crear cuenta');
  try {
    const res  = await fetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await res.json();

    if (!res.ok) {
      const msg = typeof data.detail === 'string' ? data.detail : 'Error al registrarse.';
      return showAlert('alertBox', msg);
    }

    showAlert('alertBox', '¡Cuenta creada! Podés iniciar sesión. Recordá subir tu apto físico desde el perfil.', 'success');
    setTimeout(() => switchTab('login'), 3000);

  } catch {
    showAlert('alertBox', 'No se pudo conectar con el servidor.');
  } finally {
    setLoading('registerBtn', false, 'Crear cuenta');
  }
}


// RECUPERAR CONTRASEÑA

async function handleRecovery() {
  const email = document.getElementById('recoveryEmail').value.trim();
  if (!email) return showAlert('alertBox', 'Ingresá tu email.');

  setLoading('recoveryBtn', true, 'Enviar enlace');
  try {
    const res  = await fetch(`${API}/auth/recover-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });
    const data = await res.json();

    if (!res.ok) {
      const msg = typeof data.detail === 'string' ? data.detail : 'Error.';
      return showAlert('alertBox', msg);
    }

    showAlert('alertBox', data.Mensaje || 'Si el email existe, recibirás el enlace.', 'success');
  } catch {
    showAlert('alertBox', 'No se pudo conectar con el servidor.');
  } finally {
    setLoading('recoveryBtn', false, 'Enviar enlace');
  }
}


// INIT — Con token redirige al dashboard

(function init() {
  if (getToken()) window.location.href = 'dashboard.html';
})();

// Enter en el campo contraseña para hacer login
document.addEventListener('DOMContentLoaded', () => {
  const pw = document.getElementById('loginPassword');
  if (pw) pw.addEventListener('keydown', e => { if (e.key === 'Enter') handleLogin(); });
});
