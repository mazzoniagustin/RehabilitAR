const API_PUBLIC_URL = "https://stabilize-avalanche-ability.ngrok-free.dev";

const queryParameters =
  new URLSearchParams(window.location.search);

const attendanceToken =
  queryParameters.get('token');


function showAttendanceMessage(
  message,
  type = 'error'
) {
  const alertElement = document.getElementById(
    'attendancePublicAlert'
  );

  alertElement.textContent = message;
  alertElement.className = `alert ${type} show`;
}


async function submitQrAttendance() {
  const emailInput = document.getElementById(
    'attendanceEmail'
  );

  const submitButton = document.getElementById(
    'attendanceSubmitButton'
  );

  const email = emailInput.value.trim().toLowerCase();

  if (!attendanceToken) {
    return showAttendanceMessage(
      'El enlace de asistencia no es válido.'
    );
  }

  if (!email) {
    return showAttendanceMessage(
      'Ingresá tu correo electrónico.'
    );
  }

  const emailFormat = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (!emailFormat.test(email)) {
    return showAttendanceMessage(
      'Ingresá un correo electrónico válido.'
    );
  }

  submitButton.disabled = true;
  submitButton.textContent = 'Registrando...';

  try {
    const response = await fetch(
      `${API_PUBLIC_URL}/attendance/qr/register`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({
          token: attendanceToken,
          email: email
        })
      }
    );

    const data = await response.json();

    if (!response.ok) {
      return showAttendanceMessage(
        typeof data.detail === 'string'
          ? data.detail
          : 'No se pudo registrar la asistencia.'
      );
    }

    showAttendanceMessage(
      data.message ||
      'Asistencia registrada correctamente.',
      'success'
    );

    document.getElementById(
      'attendancePublicForm'
    ).style.display = 'none';

  } catch (error) {
    console.error(error);

    showAttendanceMessage(
      'No se pudo conectar con el servidor.'
    );

  } finally {
    submitButton.disabled = false;
    submitButton.textContent = 'Registrar presente';
  }
}