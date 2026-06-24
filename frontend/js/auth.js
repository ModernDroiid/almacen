// ══ AUTENTICACION ════════════════════════════════════════════
// El token se guarda en localStorage para sobrevivir recargas

let authToken = localStorage.getItem('authToken') || null;
let usuarioActual = JSON.parse(localStorage.getItem('usuarioActual')) || null;

async function iniciarSesion() {
    const correo   = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const errorEl  = document.getElementById('login-error');

    errorEl.style.display = 'none';

    if (!correo || !password) {
        errorEl.textContent = 'Completa todos los campos';
        errorEl.style.display = 'block';
        return;
    }

    try {
        const res = await fetch(`${API}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ correo, password })
        });

        const data = await res.json();

        if (!res.ok) {
            errorEl.textContent = data.error || 'Credenciales incorrectas';
            errorEl.style.display = 'block';
            return;
        }

        authToken     = data.token;
        usuarioActual = { correo: data.correo, nombre: data.nombre, rol: data.rol };

        // Guardamos en localStorage para sobrevivir recargas
        localStorage.setItem('authToken', authToken);
        localStorage.setItem('usuarioActual', JSON.stringify(usuarioActual));

        mostrarApp();

    } catch (e) {
        errorEl.textContent = 'No se pudo conectar con el servidor';
        errorEl.style.display = 'block';
    }
}

function mostrarApp() {
    // Quitamos la regla anti-parpadeo, porque ya sabemos qué pantalla mostrar
    const estiloAntiParpadeo = document.getElementById('estilo-anti-parpadeo');
    if (estiloAntiParpadeo) estiloAntiParpadeo.remove();

    const iniciales = usuarioActual.nombre.split(' ').map(n => n[0]).join('').slice(0,2).toUpperCase();
    document.getElementById('sidebar-avatar').textContent = iniciales;
    document.getElementById('sidebar-nombre').textContent = usuarioActual.nombre;
    document.getElementById('sidebar-rol').textContent    = usuarioActual.rol === 'admin' ? 'Administrador' : 'Consulta';

    if (usuarioActual.rol !== 'admin') {
        document.body.classList.add('rol-consulta');
    } else {
        document.body.classList.remove('rol-consulta');
    }

    document.getElementById('pantalla-login').style.display  = 'none';
    document.getElementById('app-principal').style.display   = 'flex';

    cargarProductos();
    cargarCatalogos();
}

function cerrarSesion() {
    authToken     = null;
    usuarioActual = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('usuarioActual');
    document.body.classList.remove('rol-consulta');
    document.getElementById('login-email').value    = '';
    document.getElementById('login-password').value = '';
    document.getElementById('app-principal').style.display  = 'none';
    document.getElementById('pantalla-login').style.display = 'flex';

    // Quitamos la regla CSS que se inyectó al cargar la página,
    // porque tenía !important y bloqueaba mostrar el login de nuevo
    const estiloAntiParpadeo = document.getElementById('estilo-anti-parpadeo');
    if (estiloAntiParpadeo) estiloAntiParpadeo.remove();
}

// Al cargar la página, si ya hay sesión guardada, entra directo a la app
document.addEventListener('DOMContentLoaded', () => {
    if (authToken && usuarioActual) {
        mostrarApp();
    }

    document.getElementById('login-password').addEventListener('keydown', e => {
        if (e.key === 'Enter') iniciarSesion();
    });
});