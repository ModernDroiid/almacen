const API = '/api';

function sanitizar(texto) {
    if (!texto) return '—';
    return String(texto)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function mostrarNotificacion(mensaje, tipo = 'exito') {
    let notificacion = document.getElementById('notificacion-app');

    if (!notificacion) {
        notificacion = document.createElement('div');
        notificacion.id = 'notificacion-app';
        document.body.appendChild(notificacion);
    }

    notificacion.className = `notificacion-app ${tipo}`;

    notificacion.innerHTML = `
        <span class="notificacion-icono">✓</span>
        <span>${sanitizar(mensaje)}</span>
    `;

    requestAnimationFrame(() => {
        notificacion.classList.add('visible');
    });

    setTimeout(() => {
        notificacion.classList.remove('visible');
    }, 3000);
}
// ══ SESION ══════════════════════════════════════════════════

const token   = localStorage.getItem('token');
const usuario = JSON.parse(localStorage.getItem('usuario') || '{}');

if (!token) {
    window.location.href = 'login.html';
} else {
    document.getElementById('app-principal').style.display = 'flex';
}

async function apiFetch(url, opciones = {}) {
    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...(opciones.headers || {})
    };
    const res = await fetch(url, { ...opciones, headers });

    if (res.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('usuario');
        window.location.href = 'login.html';
        return;
    }
    return res;
}

function cerrarSesion() {
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
    window.location.href = 'login.html';
}

// ══ SEDES (solo admin) ══════════════════════════════════════

let sedeActual = usuario.rol === 'admin' ? null : (parseInt(localStorage.getItem('sedeActual')) || usuario.sede_id || 1);

async function inicializarSelectorSede() {

    // Solo admin y consulta pueden seleccionar sedes
    if (
        usuario.rol !== 'admin' &&
        usuario.rol !== 'consulta'
    ) {
        return;
    }

    const select = document.getElementById('selector-sede');

    if (!select) return;

    const res = await apiFetch(`${API}/auth/sedes`);

    if (!res) return;

    const sedes = await res.json();

    select.innerHTML =
        '<option value="">&#8212; Todas las sedes &#8212;</option>';

    select.innerHTML += sedes.map(sede =>
        `<option value="${sede.id}">
            ${sede.nombre}
        </option>`
    ).join('');

    select.value = '';

    sedeActual = null;

    select.style.display = 'block';
}

function cambiarSedeActual() {
    const val = document.getElementById('selector-sede').value;
    sedeActual = val ? parseInt(val) : null;
    localStorage.setItem('sedeActual', sedeActual || '');
    cargarProductos();
}

function urlConSede(base) {
    if (
        (usuario.rol === 'admin' || usuario.rol === 'consulta') &&
        sedeActual
    ) {
        const sep = base.includes('?') ? '&' : '?';
        return `${base}${sep}sede_id=${sedeActual}`;
    }
    return base;
}

function mostrarSeccion(nombre, btn) {
    if (nombre === 'usuarios' && usuario.rol !== 'admin') return;

    // Portería solo tiene acceso a la sección de Salidas.
    if (usuario.rol === 'porteria' && nombre !== 'salidas') return;

    document.querySelectorAll('.seccion').forEach(s => s.classList.remove('activa'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    document.getElementById('sec-' + nombre).classList.add('activa');
    btn.classList.add('active');

    if (nombre === 'productos')     cargarProductos();
    if (nombre === 'entradas')      cargarEntradas();
    if (nombre === 'salidas')       cargarSalidas();
    if (nombre === 'devoluciones')  cargarDevoluciones();
    if (nombre === 'traslados')     cargarTraslados();
    if (nombre === 'consolidado') cargarPuntos();
    if (nombre === 'modelos')       cargarModelos();
    if (nombre === 'marcas')        cargarMarcas();
    if (nombre === 'clientes')      cargarClientesLista();
    if (nombre === 'usuarios')      cargarUsuarios();
}

function abrirModal(id) {
    document.getElementById(id).classList.add('visible');

   if (id === 'modal-entrada') {
        const hoy = new Date().toISOString().split('T')[0];
        document.getElementById('ent-fecha').value = hoy;
        generarNumeroEntrada();
    }

    if (id === 'modal-entrada' && usuario.rol === 'admin') {
        apiFetch(`${API}/auth/sedes`).then(r => r.json()).then(sedes => {
            const sel = document.getElementById('ent-sede');
            sel.innerHTML = '<option value="">&#8212; Selecciona la sede &#8212;</option>';
            sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                `<option value="${s.id}" ${s.id === sedeActual ? 'selected' : ''}>${s.nombre}</option>`
            ));
            document.getElementById('campo-sede-entrada').style.display = 'block';
        });
    } else if (id === 'modal-entrada') {
        document.getElementById('campo-sede-entrada').style.display = 'none';
    }
    if (id === 'modal-salida') {
        const hoy = new Date().toISOString().split('T')[0];
        document.getElementById('sal-fecha').value = hoy;
        generarNumeroSalida();
        cargarClientesDatalist();
    }

    if (id === 'modal-salida' && usuario.rol === 'admin') {
            apiFetch(`${API}/auth/sedes`).then(r => r.json()).then(sedes => {
                const sel = document.getElementById('sal-sede');
                sel.innerHTML = '<option value="">&#8212; Selecciona la sede &#8212;</option>';
                sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                    `<option value="${s.id}" ${s.id === sedeActual ? 'selected' : ''}>${s.nombre}</option>`
                ));
                document.getElementById('campo-sede-salida').style.display = 'block';
            });
    } else if (id === 'modal-salida') {
        document.getElementById('campo-sede-salida').style.display = 'none';
    }
    if (id === 'modal-devolucion') {
        const hoy = new Date().toISOString().split('T')[0];
        document.getElementById('dev-fecha').value = hoy;
        cargarSelectorSalidas();
    }

    if (id === 'modal-devolucion' && usuario.rol === 'admin') {
        apiFetch(`${API}/auth/sedes`).then(r => r.json()).then(sedes => {
            const sel = document.getElementById('dev-sede');
            sel.innerHTML = '<option value="">&#8212; Selecciona la sede &#8212;</option>';
            sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                `<option value="${s.id}" ${s.id === sedeActual ? 'selected' : ''}>${s.nombre}</option>`
            ));
            document.getElementById('campo-sede-devolucion').style.display = 'block';
        });
    } else if (id === 'modal-devolucion') {
        document.getElementById('campo-sede-devolucion').style.display = 'none';
    }

    if (id === 'modal-traslado') {

        // Limpiar completamente el formulario antes de abrirlo
        limpiarFormTraslado();
        
        const ahora = new Date();
        
        const fecha =
            ahora.getFullYear().toString() +
            String(ahora.getMonth() + 1).padStart(2, '0') +
            String(ahora.getDate()).padStart(2, '0');
        
        const hora =
            String(ahora.getHours()).padStart(2, '0') +
            String(ahora.getMinutes()).padStart(2, '0') +
            String(ahora.getSeconds()).padStart(2, '0');
        
        document.getElementById('tras-numero').value =
            `TR-${fecha}-${hora}`;
        
        cargarSedesTraslado();
    }
    
    if (id === 'modal-producto' && usuario.rol === 'admin') {
        apiFetch(`${API}/auth/sedes`).then(r => r.json()).then(sedes => {
            const sel = document.getElementById('prod-sede');
            sel.innerHTML = '<option value="">&#8212; Selecciona la sede &#8212;</option>';
            sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                `<option value="${s.id}" ${s.id === sedeActual ? 'selected' : ''}>${s.nombre}</option>`
            ));
            document.getElementById('campo-sede-producto').style.display = 'block';
        });
    } else if (id === 'modal-producto') {
        document.getElementById('campo-sede-producto').style.display = 'none';
    }
}

function cerrarModal(id) {
    document.getElementById(id).classList.remove('visible');
    if (id === 'modal-producto')   limpiarFormProducto();
    if (id === 'modal-entrada')    limpiarFormEntrada();
    if (id === 'modal-salida')     limpiarFormSalida();
    if (id === 'modal-modelo')     limpiarFormModelo();
    if (id === 'modal-marca')      limpiarFormMarca();
    if (id === 'modal-cliente')    limpiarFormCliente();
    if (id === 'modal-devolucion') limpiarFormDevolucion();
}

// ══ CATALOGOS (compartidos entre sedes) ══════════════════════

let catalogoModelos = [];
let catalogoMarcas  = [];

async function cargarCatalogos() {
    const [resModelos, resMarcas] = await Promise.all([
        apiFetch(`${API}/catalogos/modelos`),
        apiFetch(`${API}/catalogos/marcas`)
    ]);
    catalogoModelos = await resModelos.json();
    catalogoMarcas  = await resMarcas.json();
}

// ================================================================
// CLIENTES (Salidas)
//
// Se maneja igual que marcas/modelos: es un catálogo simple.
// Cargamos los nombres ya existentes para sugerirlos con un
// desplegable propio (mismo estilo que el buscador de productos).
// Si el usuario escribe uno que no está en la lista, el backend
// lo crea solo al guardar la salida — no hace falta un botón de
// "+ Nuevo cliente".
// ================================================================

let clientesCache = [];

async function cargarClientesDatalist() {
    const res = await apiFetch(`${API}/catalogos/clientes`);

    if (!res) return;

    const clientes = await res.json();

    if (!Array.isArray(clientes)) return;

    clientesCache = clientes;

    inicializarBuscadorCliente();
}

function inicializarBuscadorCliente() {

    const buscador = document.getElementById('sal-cliente');
    const resultados = document.getElementById('resultados-cliente');

    if (!buscador || !resultados) return;

    if (buscador.dataset.buscadorListo === '1') return;
    buscador.dataset.buscadorListo = '1';

    function cerrarResultados() {
        resultados.style.display = 'none';
        resultados.innerHTML = '';
    }

    function seleccionarCliente(cliente) {
        buscador.value = cliente.nombre;
        cerrarResultados();
    }

    function filtrar() {

        const texto = normalizarBusqueda(buscador.value);

        if (!texto) {
            cerrarResultados();
            return;
        }

        const coincidencias = clientesCache.filter(c =>
            normalizarBusqueda(c.nombre).includes(texto)
        );

        resultados.innerHTML = '';

        if (coincidencias.length === 0) {
            resultados.innerHTML = `
                <div style="
                    padding:10px 12px;
                    font-size:12px;
                    color:#6b8aab;
                ">
                    Cliente nuevo — se creará al guardar la salida.
                </div>
            `;
            resultados.style.display = 'block';
            return;
        }

        coincidencias.slice(0, 50).forEach(c => {

            const opcionDiv = document.createElement('div');

            opcionDiv.style.cssText = `
                padding:8px 10px;
                cursor:pointer;
                border-bottom:0.5px solid #edf2f7;
                font-size:12.5px;
                color:#0d2137;
            `;

            opcionDiv.innerHTML = sanitizar(c.nombre);

            opcionDiv.onmouseenter = () => {
                opcionDiv.style.background = '#f5f8fc';
            };

            opcionDiv.onmouseleave = () => {
                opcionDiv.style.background = 'white';
            };

            // mousedown (no click) para que se dispare antes
            // del "blur" del campo de texto
            opcionDiv.onmousedown = (ev) => {
                ev.preventDefault();
                seleccionarCliente(c);
            };

            resultados.appendChild(opcionDiv);
        });

        resultados.style.display = 'block';
    }

    buscador.addEventListener('input', filtrar);

    buscador.addEventListener('focus', () => {
        filtrar();
    });

    buscador.addEventListener('blur', () => {
        setTimeout(cerrarResultados, 150);
    });
}

async function guardarMarcaEnCatalogo(nombre) {
    nombre = (nombre || '').trim();

    if (!nombre) {
        throw new Error('Escribe el nombre de la marca.');
    }

    // Si ya existe, usamos su ID
    let existente = catalogoMarcas.find(m =>
        m.activa !== false &&
        m.nombre.trim().toLowerCase() === nombre.toLowerCase()
    );

    if (existente) {
        return Number(existente.id);
    }

    // Crear nueva marca
    const res = await apiFetch(`${API}/catalogos/marcas`, {
        method: 'POST',
        body: JSON.stringify({
            nombre: nombre
        })
    });

    if (!res) {
        throw new Error('No se pudo conectar con el servidor.');
    }

    const resultado = await res.json();

    if (!res.ok) {
        throw new Error(resultado.error || 'No se pudo guardar la marca.');
    }

    // Recargar catálogo
    await cargarCatalogos();

    existente = catalogoMarcas.find(m =>
        m.activa !== false &&
        m.nombre.trim().toLowerCase() === nombre.toLowerCase()
    );

    return existente
        ? Number(existente.id)
        : Number(resultado.id);
}


async function guardarModeloEnCatalogo(nombre, marcaId) {
    nombre = (nombre || '').trim();
    marcaId = Number(marcaId);

    if (!nombre) {
        throw new Error('Escribe el nombre del modelo.');
    }

    if (!marcaId) {
        throw new Error('Primero selecciona una marca.');
    }

    // Si ya existe para esa marca, usamos su ID
    let existente = catalogoModelos.find(m =>
        m.activo !== false &&
        Number(m.marca_id) === marcaId &&
        m.nombre.trim().toLowerCase() === nombre.toLowerCase()
    );

    if (existente) {
        return Number(existente.id);
    }

    // Crear nuevo modelo asociado a la marca
    const res = await apiFetch(`${API}/catalogos/modelos`, {
        method: 'POST',
        body: JSON.stringify({
            nombre: nombre,
            marca_id: marcaId
        })
    });

    if (!res) {
        throw new Error('No se pudo conectar con el servidor.');
    }

    const resultado = await res.json();

    if (!res.ok) {
        throw new Error(resultado.error || 'No se pudo guardar el modelo.');
    }

    // Recargar catálogo
    await cargarCatalogos();

    existente = catalogoModelos.find(m =>
        m.activo !== false &&
        Number(m.marca_id) === marcaId &&
        m.nombre.trim().toLowerCase() === nombre.toLowerCase()
    );

    return existente
        ? Number(existente.id)
        : Number(resultado.id);
}

function crearComboHTML(tipo, placeholder) {
    return `
        <div class="combo-wrap" data-tipo="${tipo}">
            <input type="text" class="combo-input" placeholder="${placeholder}" autocomplete="off">
            <span class="combo-flecha">▼</span>
            <div class="combo-lista"></div>
        </div>
    `;
}

function activarCombo(wrapEl) {
    const tipo  = wrapEl.dataset.tipo;
    const input = wrapEl.querySelector('.combo-input');
    const lista = wrapEl.querySelector('.combo-lista');

    function obtenerNombres() {
        const fuente = tipo === 'modelo' ? catalogoModelos : catalogoMarcas;
        return fuente.map(x => x.nombre);
    }

    function renderizarOpciones() {
        const texto = input.value.trim().toLowerCase();
        const todas = obtenerNombres();
        let filtradas = todas.filter(op => op.toLowerCase().includes(texto));
        if (!texto) filtradas = todas.slice(0, 30);

        let html = filtradas.map(op =>
            `<div class="combo-opcion" data-valor="${op}">${op}</div>`
        ).join('');

        const yaExiste = todas.some(op => op.toLowerCase() === texto);
        if (texto && !yaExiste) {
            html += `<div class="combo-opcion nueva" data-valor="${input.value.trim()}">+ Agregar "${input.value.trim()}"</div>`;
        }

        lista.innerHTML = html;
        lista.classList.toggle('visible', html.length > 0);
    }

    input.addEventListener('focus', renderizarOpciones);
    input.addEventListener('input', renderizarOpciones);

    lista.addEventListener('click', (e) => {
        const opcion = e.target.closest('.combo-opcion');
        if (!opcion) return;
        input.value = opcion.dataset.valor;
        lista.classList.remove('visible');
    });

    document.addEventListener('click', (e) => {
        if (!wrapEl.contains(e.target)) lista.classList.remove('visible');
    });
}

// ══ MODELOS ══════════════════════════════════════════════════

async function cargarModelos() {
    const res     = await apiFetch(`${API}/catalogos/modelos`);
    const modelos = await res.json();
    catalogoModelos = modelos;

    document.getElementById('subtitulo-modelos').textContent =
        `${modelos.length} modelos registrados`;

    const tbody = document.getElementById('tabla-modelos');
    tbody.innerHTML = '';

    if (modelos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" style="text-align:center;color:#6b8aab;padding:2rem">Sin modelos registrados</td></tr>';
        return;
    }

    modelos.forEach(m => {
        tbody.insertAdjacentHTML('beforeend', `
            <tr>
                <td><strong>${m.nombre}</strong></td>
                <td>
                    <div class="acciones">
                        ${usuario.rol !== 'consulta' ? `
                            <button class="btn-accion" onclick="editarModelo(${m.id}, '${m.nombre}')">✏️ Editar</button>
                            <button class="btn-accion danger" onclick="eliminarModelo(${m.id}, '${m.nombre}')">🗑️ Eliminar</button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `);
    });
}

function editarModelo(id, nombre) {
    document.getElementById('modal-modelo-titulo').textContent = 'Editar modelo';
    document.getElementById('modelo-id').value     = id;
    document.getElementById('modelo-nombre').value = nombre;
    abrirModal('modal-modelo');
}

async function guardarModelo(event) {
    event.preventDefault();
    const id     = document.getElementById('modelo-id').value;
    const nombre = document.getElementById('modelo-nombre').value;
    const url    = id ? `${API}/catalogos/modelos/${id}` : `${API}/catalogos/modelos`;
    const metodo = id ? 'PUT' : 'POST';
    await apiFetch(url, {
        method: metodo,
        body: JSON.stringify({ nombre })
    });
    cerrarModal('modal-modelo');
    cargarModelos();
}

async function eliminarModelo(id, nombre) {
    if (!await mostrarConfirm(`¿Eliminar el modelo "${nombre}"?`)) return;
    await apiFetch(`${API}/catalogos/modelos/${id}`, { method: 'DELETE' });
    cargarModelos();
}

function limpiarFormModelo() {
    document.getElementById('modelo-id').value     = '';
    document.getElementById('modelo-nombre').value = '';
    document.getElementById('modal-modelo-titulo').textContent = 'Nuevo modelo';
}

// ══ MARCAS ════════════════════════════════════════════════════

async function cargarMarcas() {
    const res    = await apiFetch(`${API}/catalogos/marcas`);
    const marcas = await res.json();
    catalogoMarcas = marcas;

    document.getElementById('subtitulo-marcas').textContent =
        `${marcas.length} marcas registradas`;

    const tbody = document.getElementById('tabla-marcas');
    tbody.innerHTML = '';

    if (marcas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" style="text-align:center;color:#6b8aab;padding:2rem">Sin marcas registradas</td></tr>';
        return;
    }

    marcas.forEach(m => {
        tbody.insertAdjacentHTML('beforeend', `
            <tr>
                <td><strong>${m.nombre}</strong></td>
                <td>
                    <div class="acciones">
                        ${usuario.rol !== 'consulta' ? `
                            <button class="btn-accion" onclick="editarMarca(${m.id}, '${m.nombre}')">✏️ Editar</button>
                            <button class="btn-accion danger" onclick="eliminarMarca(${m.id}, '${m.nombre}')">🗑️ Eliminar</button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `);
    });
}

function editarMarca(id, nombre) {
    document.getElementById('modal-marca-titulo').textContent = 'Editar marca';
    document.getElementById('marca-id').value     = id;
    document.getElementById('marca-nombre').value = nombre;
    abrirModal('modal-marca');
}

async function guardarMarca(event) {
    event.preventDefault();
    const id     = document.getElementById('marca-id').value;
    const nombre = document.getElementById('marca-nombre').value;
    const url    = id ? `${API}/catalogos/marcas/${id}` : `${API}/catalogos/marcas`;
    const metodo = id ? 'PUT' : 'POST';
    await apiFetch(url, {
        method: metodo,
        body: JSON.stringify({ nombre })
    });
    cerrarModal('modal-marca');
    cargarMarcas();
}

async function eliminarMarca(id, nombre) {
    if (!await mostrarConfirm(`¿Eliminar la marca "${nombre}"?`)) return;
    await apiFetch(`${API}/catalogos/marcas/${id}`, { method: 'DELETE' });
    cargarMarcas();
}

function limpiarFormMarca() {
    document.getElementById('marca-id').value     = '';
    document.getElementById('marca-nombre').value = '';
    document.getElementById('modal-marca-titulo').textContent = 'Nueva marca';
}

// ══ CLIENTES (catálogo) ══════════════════════════════════════
//
// Sección dedicada para ver/editar/eliminar clientes. Admin,
// almacenista y consulta pueden VER esta lista; solo admin
// puede editar o eliminar (igual que marcas/modelos). La
// creación "sobre la marcha" desde el modal de Salidas sigue
// funcionando aparte (ver cargarClientesDatalist más abajo).

async function cargarClientesLista() {
    const res = await apiFetch(`${API}/catalogos/clientes`);
    if (!res) return;
    const clientes = await res.json();

    document.getElementById('subtitulo-clientes').textContent =
        `${clientes.length} clientes registrados`;

    const tbody = document.getElementById('tabla-clientes');
    tbody.innerHTML = '';

    if (clientes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" style="text-align:center;color:#6b8aab;padding:2rem">Sin clientes registrados</td></tr>';
        return;
    }

    clientes.forEach(c => {
        tbody.insertAdjacentHTML('beforeend', `
            <tr>
                <td><strong>${sanitizar(c.nombre)}</strong></td>
                <td>
                    <div class="acciones">
                        ${usuario.rol === 'admin' ? `
                            <button class="btn-accion" onclick="editarCliente(${c.id}, '${sanitizar(c.nombre)}')">✏️ Editar</button>
                            <button class="btn-accion danger" onclick="eliminarCliente(${c.id}, '${sanitizar(c.nombre)}')">🗑️ Eliminar</button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `);
    });
}

function editarCliente(id, nombre) {
    document.getElementById('modal-cliente-titulo').textContent = 'Editar cliente';
    document.getElementById('cliente-id').value     = id;
    document.getElementById('cliente-nombre').value = nombre;
    abrirModal('modal-cliente');
}

async function guardarCliente(event) {
    event.preventDefault();
    const id     = document.getElementById('cliente-id').value;
    const nombre = document.getElementById('cliente-nombre').value;
    const url    = id ? `${API}/catalogos/clientes/${id}` : `${API}/catalogos/clientes`;
    const metodo = id ? 'PUT' : 'POST';

    const res = await apiFetch(url, {
        method: metodo,
        body: JSON.stringify({ nombre })
    });
    if (!res) return;
    const resultado = await res.json();
    if (!res.ok) { alert('Error: ' + resultado.error); return; }

    cerrarModal('modal-cliente');
    cargarClientesLista();
}

async function eliminarCliente(id, nombre) {
    if (!await mostrarConfirm(`¿Eliminar el cliente "${nombre}"?`)) return;
    const res = await apiFetch(`${API}/catalogos/clientes/${id}`, { method: 'DELETE' });
    if (!res) return;
    const resultado = await res.json();
    if (!res.ok) { alert('Error: ' + resultado.error); return; }
    cargarClientesLista();
}

function limpiarFormCliente() {
    document.getElementById('cliente-id').value     = '';
    document.getElementById('cliente-nombre').value = '';
    document.getElementById('modal-cliente-titulo').textContent = 'Nuevo cliente';
}

// ══ PRODUCTOS/SERIALES (separados por sede) ════════════════════════════

async function cargarProductos() {

    const respuesta = await apiFetch(
        urlConSede(`${API}/productos/`)
    );

    if (!respuesta) return;

    const productos = await respuesta.json();

    // Guardar productos para búsqueda y filtro
    productosFiltrables = productos;

    // Estadísticas
    const total = productos.length;

    const agotados =
        productos.filter(
            p => p.stock === 0
        ).length;

    const bajos =
        productos.filter(
            p => p.stock > 0 && p.stock <= 5
        ).length;

    const enstock =
        total - agotados - bajos;

    document.getElementById(
        'stat-total'
    ).textContent = total;

    document.getElementById(
        'stat-enstock'
    ).textContent = enstock;

    document.getElementById(
        'stat-bajo'
    ).textContent = bajos;

    document.getElementById(
        'stat-agotados'
    ).textContent = agotados;

    document.getElementById(
        'subtitulo-productos'
    ).textContent =
        `${total} productos registrados`;

    // Pintar todos los productos
    pintarProductos(productos);
}


// ============================================================
// PINTAR TABLA DE PRODUCTOS
// ============================================================

function pintarProductos(productos) {

    const tbody =
        document.getElementById(
            'tabla-productos'
        );

    if (!tbody) return;

    tbody.innerHTML = '';

    if (productos.length === 0) {

        tbody.innerHTML = `
            <tr>
                <td
                    colspan="7"
                    style="
                        text-align:center;
                        color:#6b8aab;
                        padding:2rem
                    "
                >
                    Sin productos registrados
                </td>
            </tr>
        `;

        return;
    }

    productos.forEach(p => {

        let badgeClase;
        let badgeTexto;

        if (p.stock === 0) {

            badgeClase = 'badge-agotado';
            badgeTexto = 'Agotado';

        } else if (p.stock <= 5) {

            badgeClase = 'badge-minimo';
            badgeTexto = 'Stock bajo';

        } else {

            badgeClase = 'badge-ok';
            badgeTexto = 'En stock';
        }


        // Botón para productos serializados
        const botonEquipos =
            p.requiere_serial
                ? `
                    <button
                        class="btn-accion"
                        onclick="verEquiposProducto(${p.id})">
                        👁️ Ver equipos
                    </button>
                  `
                : '';


        // Crear fila
        tbody.insertAdjacentHTML(
            'beforeend',
            `
            <tr>

                <td>
                    <span
                        style="
                            font-family:monospace;
                            font-size:12px;
                            color:#1a6fc4;
                            font-weight:600
                        "
                    >
                        ${p.codigo || '—'}
                    </span>
                </td>

                <td>
                    <strong>
                        ${sanitizar(p.nombre)}
                    </strong>

                    <div class="sub">
                        ${sanitizar(p.descripcion)}
                    </div>
                </td>

                <td>
                    <span
                        style="
                            font-size:11px;
                            color:#4a6080
                        "
                    >
                        ${sanitizar(
                            p.sede_nombre || '—'
                        )}
                    </span>
                </td>

                <td>
                    ${sanitizar(
                        p.unidad || 'UND'
                    )}
                </td>

                <td>
                    ${p.stock}
                </td>

                <td>
                    <span
                        class="badge ${badgeClase}"
                    >
                        ${badgeTexto}
                    </span>
                </td>

                <td>
                    <div class="acciones">

                        ${botonEquipos}

                        ${
                            usuario.rol === 'admin'
                                ? `
                                    <button
                                        class="btn-accion"
                                        onclick="editarProducto(${p.id})"
                                    >
                                        ✏️ Editar
                                    </button>

                                    <button
                                        class="btn-accion danger"
                                        onclick="eliminarProducto(
                                            ${p.id},
                                            '${String(
                                                p.nombre || ''
                                            ).replace(
                                                /'/g,
                                                "\\'"
                                            )}'
                                        )"
                                    >
                                        🗑️ Eliminar
                                    </button>
                                  `
                                : ''
                        }

                    </div>
                </td>

            </tr>
            `
        );
    });
}

// Cuando el producto es serializado, el "Stock inicial" no se
// pone aquí (cada unidad necesita su propio serial), sino con
// una Entrada. Este ajuste visual desactiva y limpia ESE campo
// nada más (el de "Stock mínimo" no se toca, sigue siendo
// editable siempre — es solo el umbral de alerta, no depende de
// si el producto es serializado).
function actualizarCampoStockProducto() {
    const requiereSerial = document.getElementById('prod-requiere-serial').checked;
    const inputStockInicial = document.getElementById('prod-stock-inicial');
    const nota = document.getElementById('nota-stock-serializado');

    inputStockInicial.disabled = requiereSerial;
    nota.style.display = requiereSerial ? 'block' : 'none';

    if (requiereSerial) {
        inputStockInicial.value = '0';
    }
}

async function guardarProducto(event) {
    event.preventDefault();
    const id = document.getElementById('prod-id').value;

    const sede_id = parseInt(document.getElementById('prod-sede').value) || sedeActual;

    if (usuario.rol === 'admin' && !sede_id) {
        alert('Selecciona una sede para el producto');
        return;
    }

    const requiereSerial = document.getElementById('prod-requiere-serial').checked;

    // "Stock inicial" (cantidad con la que nace el producto) y
    // "Stock mínimo" (umbral para la alerta de "Stock bajo") son
    // dos cosas distintas en la base de datos, así que van en
    // campos separados. El backend solo usa "stock" al CREAR
    // (POST); al editar (PUT) lo ignora, así que no importa qué
    // se mande ahí en ese caso.
    const stockInicial = requiereSerial
        ? 0
        : parseInt(document.getElementById('prod-stock-inicial').value) || 0;

    const stockMinimo = parseInt(document.getElementById('prod-stock-minimo').value) || 0;

    const datos = {
        codigo:          document.getElementById('prod-codigo').value,
        nombre:          document.getElementById('prod-nombre').value,
        descripcion:     document.getElementById('prod-descripcion').value,
        unidad:          document.getElementById('prod-unidad').value,
        stock:           stockInicial,
        stock_minimo:    stockMinimo,
        sede_id:         sede_id,
        requiere_serial: requiereSerial,
    };

    const url    = id ? `${API}/productos/${id}` : urlConSede(`${API}/productos/`);
    const metodo = id ? 'PUT' : 'POST';

    const res = await apiFetch(url, {
        method: metodo,
        body: JSON.stringify(datos)
    });

    if (!res) return;

    const resultado = await res.json();

    if (!res.ok) {
        // Muestra el mensaje de error que manda el backend
        alert(resultado.error || 'Error al guardar el producto');
        return;
    }

    cerrarModal('modal-producto');
    cargarProductos();
}

async function editarProducto(id) {
    const res       = await apiFetch(urlConSede(`${API}/productos/`));
    if (!res) return;
    const productos = await res.json();
    const p         = productos.find(x => x.id === id);
    if (!p) return;
    document.getElementById('modal-producto-titulo').textContent = 'Editar producto';
    document.getElementById('prod-id').value           = p.id;
    document.getElementById('prod-codigo').value       = p.codigo || '';
    document.getElementById('prod-nombre').value       = p.nombre;
    document.getElementById('prod-descripcion').value  = p.descripcion || '';
    document.getElementById('prod-unidad').value       = p.unidad;
    document.getElementById('prod-stock-minimo').value = p.stock_minimo;

    // El "Stock inicial" solo tiene sentido al CREAR (el backend
    // lo ignora al editar), así que se esconde por completo aquí
    // para no dar a entender que cambiarlo hace algo.
    document.getElementById('campo-stock-inicial-producto').style.display = 'none';

    // El "requiere serial" de un producto ya creado no se deja
    // cambiar desde aquí: si ya tiene stock o equipos registrados
    // de una forma, cambiarlo a mitad de camino puede dejar datos
    // inconsistentes. Solo se muestra cómo quedó al crearlo.
    const chkSerial = document.getElementById('prod-requiere-serial');
    chkSerial.checked  = !!p.requiere_serial;
    chkSerial.disabled = true;

    document.getElementById('nota-stock-serializado').style.display = 'none';

    abrirModal('modal-producto');
}

async function eliminarProducto(id, nombre) {

    // Confirmar antes de eliminar
    if (!await mostrarConfirm(
        `¿Eliminar "${nombre}"? Esta acción no se puede deshacer.`
    )) {
        return;
    }

    try {

        // Intentar eliminar el producto
        const respuesta = await apiFetch(
            `${API}/productos/${id}`,
            {
                method: 'DELETE'
            }
        );

        if (!respuesta) return;

        // Leer respuesta del servidor
        const datos = await respuesta.json();

        // ------------------------------------------------
        // EL SERVIDOR RECHAZÓ EL BORRADO
        // ------------------------------------------------

        if (!respuesta.ok) {

            if (datos.detalle) {

                const entradas =
                    datos.detalle.entradas || 0;

                const salidas =
                    datos.detalle.salidas || 0;

                const devoluciones =
                    datos.detalle.devoluciones || 0;

                await mostrarConfirm(
                    `⚠️ No se puede eliminar "${nombre}".\n\n` +
                    `Este producto tiene movimientos históricos asociados.\n\n` +
                    `📥 Entradas: ${entradas}\n` +
                    `📤 Salidas: ${salidas}\n` +
                    `↩️ Devoluciones: ${devoluciones}\n\n` +
                    `El historial del almacén debe conservarse.`
                );

            } else {

                await mostrarConfirm(
                    `❌ No se pudo eliminar "${nombre}".\n\n` +
                    `${datos.error || 'El servidor rechazó la eliminación.'}`
                );
            }

            return;
        }

        // ------------------------------------------------
        // ELIMINACIÓN CORRECTA
        // ------------------------------------------------

        await mostrarConfirm(
            `✅ Producto eliminado correctamente.\n\n` +
            `"${nombre}" ya no aparece en el inventario.`
        );

        // Actualizar la tabla
        await cargarProductos();

    } catch (error) {

        console.error(
            'Error al eliminar producto:',
            error
        );

        await mostrarConfirm(
            `❌ Ocurrió un error al intentar eliminar "${nombre}".`
        );
    }
}

function limpiarFormProducto() {
    document.getElementById('prod-id').value            = '';
    document.getElementById('prod-codigo').value        = '';
    document.getElementById('prod-nombre').value         = '';
    document.getElementById('prod-descripcion').value   = '';
    document.getElementById('prod-unidad').value         = 'UND';
    document.getElementById('prod-stock-inicial').value = '0';
    document.getElementById('prod-stock-minimo').value  = '0';
    document.getElementById('modal-producto-titulo').textContent = 'Nuevo producto';
    document.getElementById('prod-sede').value = '';

    // El campo de "Stock inicial" solo se esconde al EDITAR
    // (ver editarProducto); al abrir para un producto nuevo
    // siempre debe volver a verse.
    document.getElementById('campo-stock-inicial-producto').style.display = '';

    const chkSerial = document.getElementById('prod-requiere-serial');
    chkSerial.checked  = false;
    chkSerial.disabled = false;
    actualizarCampoStockProducto();
}

// ══ ENTRADAS ════════════════════════════════════════════════

let productosCache = [];

async function generarNumeroEntrada() {
    const fecha =
        document.getElementById('ent-fecha')?.value || '';

    const campoOrigen =
        document.getElementById('ent-origen') ||
        document.getElementById('ent-obra');

    const origen =
        campoOrigen
            ? campoOrigen.value.trim()
            : '';

    if (!fecha || !origen) return;

    const base =
        `ENT-${fecha}-${origen.toUpperCase().replace(/\s+/g, '-')}`;

    const res =
        await apiFetch(`${API}/entradas/`);

    if (!res) return;

    const entradas =
        await res.json();

    const existentes =
        entradas.filter(e =>
            String(e.numero_documento || '')
                .startsWith(base)
        );

    document.getElementById('ent-numero').value =
        `${base}-${existentes.length + 1}`;
}

let entradasCache = [];

async function cargarEntradas() {
    const res = await apiFetch(urlConSede(`${API}/entradas/`));
    if (!res) return;
    entradasCache = await res.json();

    if (usuario.rol === 'admin' || usuario.rol === 'consulta') {
        const sel = document.getElementById('filtro-sede-entradas');
        const valorActual = sel.value; // ✅ guardamos el valor antes de recargar

        const resSedes = await apiFetch(`${API}/auth/sedes`);
        if (resSedes) {
            const sedes = await resSedes.json();
            sel.innerHTML = '<option value="">&#8212; Todas las sedes &#8212;</option>';
            sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                `<option value="${s.id}">${s.nombre}</option>`
            ));
            sel.style.display = 'block';
            sel.value = valorActual; // ✅ restauramos el valor después
        }
    }

    renderizarEntradas(entradasCache);
    filtrarEntradas(); // ✅ aplicamos el filtro con la sede restaurada
}

function renderizarEntradas(entradas) {
    document.getElementById('subtitulo-entradas').textContent =
        `${entradas.length} entradas registradas`;

    const tbody = document.getElementById('tabla-entradas');
    tbody.innerHTML = '';

    if (entradas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#6b8aab;padding:2rem">Sin entradas registradas</td></tr>';
        return;
    }

    entradas.forEach(e => {
        const fecha = new Date(e.fecha).toLocaleDateString('es-CO', {
            day: '2-digit', month: '2-digit', year: 'numeric'
        });
        tbody.insertAdjacentHTML('beforeend', `
            <tr>
                <td><strong>${e.numero_documento}</strong></td>
                <td>${e.obra || '—'}</td>
                <td>${e.destino || 'Almacen'}</td>
                <td><span style="font-size:11px;color:#4a6080">${e.sede_nombre || '—'}</span></td> 
                <td>${e.total_items} producto(s)</td>
                <td>${fecha}</td>
                <td>
                    <div class="acciones">
                        <button class="btn-accion" onclick="verPDFEntrada(${e.id})">📄 PDF</button>
                        ${usuario.rol === 'admin' ? `
                            <button class="btn-accion danger" onclick="eliminarEntrada(${e.id}, '${e.numero_documento}')">🗑️ Eliminar</button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `);
    });
}

function filtrarEntradas() {
    const texto = document.getElementById('buscar-entradas').value.trim().toLowerCase();
    const sedeFiltro = document.getElementById('filtro-sede-entradas')?.value;

    let filtradas = entradasCache;

    if (texto) {
        filtradas = filtradas.filter(e =>
            (e.numero_documento || '').toLowerCase().includes(texto) ||
            (e.obra || '').toLowerCase().includes(texto) ||
            (e.destino || '').toLowerCase().includes(texto)
        );
    }

    if (sedeFiltro) {
        filtradas = filtradas.filter(e => String(e.sede_id) === sedeFiltro);
    }

    renderizarEntradas(filtradas);
}

async function agregarItemEntrada() {

    const sedeEntrada =
        parseInt(document.getElementById('ent-sede').value) || sedeActual;

    const urlProductos =
        usuario.rol === 'admin' && sedeEntrada
            ? `${API}/productos/?sede_id=${sedeEntrada}`
            : urlConSede(`${API}/productos/`);

    const res = await apiFetch(urlProductos);

    if (!res) return;

    productosCache = await res.json();

    if (!Array.isArray(productosCache)) {
        alert('No se pudieron cargar los productos.');
        return;
    }

    // Cargar catálogos
    await cargarCatalogos();

    const opciones = productosCache.map(p => `
        <option
            value="${p.id}"
            data-unidad="${p.unidad || 'UND'}"
            data-requiere-serial="${p.requiere_serial ? 'true' : 'false'}">
            [${p.codigo || '—'}] ${p.nombre}
        </option>
    `).join('');

    const unidadesDisponibles = [
        'UND',
        'MTS',
        'KG',
        'CAJA',
        'ROLLO',
        'LITRO'
    ];

    const opcionesUnidad = unidadesDisponibles
        .map(u => `<option value="${u}">${u}</option>`)
        .join('');

    const item = document.createElement('div');

    item.className = 'item-entrada';

    item.style.cssText = `
        display:grid;
        grid-template-columns:2fr 100px 70px;
        gap:6px;
        align-items:start;
        margin-bottom:10px;
        padding:8px;
        border:1px solid #dbe5f0;
        border-radius:8px;
        background:#f8fbff;
    `;

    item.innerHTML = `
        <div style="position:relative;">

            <input
                type="text"
                class="buscador-producto"
                placeholder="Escribe código o nombre..."
                autocomplete="off"
                style="
                    width:100%;
                    padding:8px;
                    border:1px solid #ccd8e5;
                    border-radius:6px;
                    box-sizing:border-box;
                ">

            <div
                class="resultados-producto"
                style="
                    display:none;
                    position:absolute;
                    left:0;
                    right:0;
                    top:100%;
                    background:white;
                    border:1px solid #ccd8e5;
                    border-radius:8px;
                    margin-top:4px;
                    max-height:220px;
                    overflow-y:auto;
                    z-index:50;
                    box-shadow:0 4px 15px rgba(0,0,0,.12);
                ">
            </div>

            <select
                class="select-producto"
                style="display:none">
                ${opciones}
            </select>

        </div>

        <select
            class="select-unidad"
            style="
                width:100%;
                padding:8px;
                border:1px solid #ccd8e5;
                border-radius:6px;
            ">
            ${opcionesUnidad}
        </select>

        <input
            type="number"
            class="input-cantidad"
            min="1"
            value="1"
            style="
                width:100%;
                padding:8px;
                border:1px solid #ccd8e5;
                border-radius:6px;
            ">

        <div
            class="seriales-container"
            style="
                grid-column:1 / -1;
                display:none;
                padding:10px;
                margin-top:4px;
                border-top:1px solid #dbe5f0;
            ">
        </div>

        <button
            type="button"
            style="
                grid-column:1 / -1;
                width:max-content;
                padding:5px 10px;
                border:none;
                border-radius:6px;
                background:#dc3545;
                color:white;
                cursor:pointer;
            "
            onclick="this.parentElement.remove()">
            ✕ Quitar producto
        </button>
    `;

    document
        .getElementById('ent-items')
        .appendChild(item);

    const selectProducto =
        item.querySelector('.select-producto');

    const selectUnidad =
        item.querySelector('.select-unidad');

    const inputCantidad =
        item.querySelector('.input-cantidad');

    const serialesContainer =
        item.querySelector('.seriales-container');

    inicializarBuscadorProducto(
        item,
        selectProducto,
        productosCache
    );


    // =========================================================
    // UNIDAD AUTOMÁTICA
    // =========================================================

    function autocompletarUnidad() {

        const opcion =
            selectProducto.options[
                selectProducto.selectedIndex
            ];

        selectUnidad.value =
            opcion?.dataset.unidad || 'UND';

        actualizarSeriales();
    }


    // =========================================================
    // EQUIPOS SERIALIZADOS
    // =========================================================

    function actualizarSeriales() {

        const opcion =
            selectProducto.options[
                selectProducto.selectedIndex
            ];

        const requiereSerial =
            opcion?.dataset.requiereSerial === 'true';

        const cantidad =
            parseInt(inputCantidad.value) || 1;


        // -----------------------------------------------------
        // PRODUCTO NORMAL
        // -----------------------------------------------------

        if (!requiereSerial) {

            serialesContainer.style.display = 'none';
            serialesContainer.innerHTML = '';

            return;
        }


        // -----------------------------------------------------
        // PRODUCTO SERIALIZADO
        // -----------------------------------------------------

        serialesContainer.style.display = 'block';

        serialesContainer.innerHTML = `
            <div style="
                font-weight:600;
                margin-bottom:10px;
                color:#294d73;
            ">
                📦 Equipos serializados
            </div>
        `;


        for (let i = 0; i < cantidad; i++) {

            const fila =
                document.createElement('div');

            fila.style.cssText = `
                display:grid;
                grid-template-columns:40px 1fr 1fr 1fr;
                gap:8px;
                margin-bottom:8px;
                align-items:center;
            `;


            // =================================================
            // MARCAS
            // =================================================

            const opcionesMarcas =
                catalogoMarcas
                    .filter(m => m.activa !== false)
                    .map(m => `
                        <option value="${m.id}">
                            ${m.nombre}
                        </option>
                    `)
                    .join('');


            fila.innerHTML = `
                <strong style="color:#4a6080;">
                    #${i + 1}
                </strong>

                <input
                    type="text"
                    class="serial-equipo"
                    placeholder="Serial"
                    style="
                        width:100%;
                        padding:8px;
                        border:1px solid #ccd8e5;
                        border-radius:6px;
                    ">

                <select
                    class="marca-equipo"
                    style="
                        width:100%;
                        padding:8px;
                        border:1px solid #ccd8e5;
                        border-radius:6px;
                    ">

                    <option value="">
                        — Selecciona marca —
                    </option>

                    ${opcionesMarcas}

                    <option value="__nueva__">
                        + Nueva marca...
                    </option>

                </select>

                <select
                    class="modelo-equipo"
                    style="
                        width:100%;
                        padding:8px;
                        border:1px solid #ccd8e5;
                        border-radius:6px;
                    ">

                    <option value="">
                        — Selecciona modelo —
                    </option>

                </select>

                <input
                    type="text"
                    class="nueva-marca"
                    placeholder="Escribe la nueva marca"
                    style="
                        display:none;
                        grid-column:3 / 5;
                        width:100%;
                        padding:8px;
                        border:1px solid #ccd8e5;
                        border-radius:6px;
                    ">

                <input
                    type="text"
                    class="nuevo-modelo"
                    placeholder="Escribe el nuevo modelo"
                    style="
                        display:none;
                        grid-column:3 / 5;
                        width:100%;
                        padding:8px;
                        border:1px solid #ccd8e5;
                        border-radius:6px;
                    ">
            `;


            const selectMarca =
                fila.querySelector('.marca-equipo');

            const selectModelo =
                fila.querySelector('.modelo-equipo');

            const nuevaMarca =
                fila.querySelector('.nueva-marca');

            const nuevoModelo =
                fila.querySelector('.nuevo-modelo');


            // =================================================
            // CAMBIAR MARCA
            // =================================================

            selectMarca.addEventListener('change', () => {

                const marcaId =
                    selectMarca.value;


                // -----------------------------
                // Nueva marca
                // -----------------------------

                if (marcaId === '__nueva__') {

                    nuevaMarca.style.display = 'block';

                    selectModelo.innerHTML = `
                        <option value="">
                            — Escribe primero la marca —
                        </option>
                    `;

                    nuevoModelo.style.display = 'block';

                    return;
                }


                // -----------------------------
                // Marca existente
                // -----------------------------

                nuevaMarca.style.display = 'none';
                nuevaMarca.value = '';

                nuevoModelo.style.display = 'none';
                nuevoModelo.value = '';


                const modelosFiltrados =
                    catalogoModelos.filter(m =>
                        m.activo !== false &&
                        Number(m.marca_id) === Number(marcaId)
                    );


                selectModelo.innerHTML = `
                    <option value="">
                        — Selecciona modelo —
                    </option>

                    ${modelosFiltrados.map(m => `
                        <option value="${m.id}">
                            ${m.nombre}
                        </option>
                    `).join('')}

                    <option value="__nuevo__">
                        + Nuevo modelo...
                    </option>
                `;
            });


            // =================================================
            // NUEVO MODELO
            // =================================================

            selectModelo.addEventListener('change', () => {

                if (selectModelo.value === '__nuevo__') {

                    nuevoModelo.style.display = 'block';

                } else {

                    nuevoModelo.style.display = 'none';
                    nuevoModelo.value = '';
                }
            });


            serialesContainer.appendChild(fila);
        }
    }


    // =========================================================
    // EVENTOS
    // =========================================================

    selectProducto.addEventListener(
        'change',
        autocompletarUnidad
    );

    inputCantidad.addEventListener(
        'input',
        actualizarSeriales
    );


    // =========================================================
    // INICIALIZAR
    // =========================================================

    autocompletarUnidad();
    actualizarSeriales();
}

async function guardarEntrada(event) {
    event.preventDefault();

    try {
        // =====================================================
        // NÚMERO DE DOCUMENTO
        // =====================================================

        const numero = document
            .getElementById('ent-numero')
            .value
            .trim();

        if (!numero) {
            alert('Escribe el número de documento.');
            return;
        }


        // =====================================================
        // FILAS DE PRODUCTOS
        // =====================================================

        const filas = document
            .getElementById('ent-items')
            .querySelectorAll(':scope > .item-entrada');

        if (filas.length === 0) {
            alert('Agrega al menos un producto.');
            return;
        }


        const detalle = [];


        // =====================================================
        // PROCESAR PRODUCTOS
        // =====================================================

        for (const fila of filas) {

            const selectProducto =
                fila.querySelector('.select-producto');

            const selectUnidad =
                fila.querySelector('.select-unidad');

            const inputCantidad =
                fila.querySelector('.input-cantidad');

            const serialesContainer =
                fila.querySelector('.seriales-container');

            const productoId =
                parseInt(selectProducto?.value);

            const cantidad =
                parseInt(inputCantidad?.value) || 1;

            const unidad =
                selectUnidad?.value || 'UND';


            // =================================================
            // VALIDAR PRODUCTO
            // =================================================

            if (!productoId) {
                throw new Error(
                    'Selecciona un producto.'
                );
            }


            const producto =
                productosCache.find(
                    p => Number(p.id) === productoId
                );


            if (!producto) {
                throw new Error(
                    'No se encontró el producto seleccionado.'
                );
            }


            const requiereSerial =
                producto.requiere_serial === true ||
                producto.requiere_serial === 1;


            const item = {
                producto_id: productoId,
                unidad: unidad,
                cantidad: cantidad,
                unidades: []
            };


            // =====================================================
            // PRODUCTO SERIALIZADO
            // =====================================================

            if (requiereSerial) {

                if (!serialesContainer) {
                    throw new Error(
                        `No se encontró el área de seriales para "${producto.nombre}".`
                    );
                }


                const inputsSerial =
                    serialesContainer.querySelectorAll(
                        '.serial-equipo'
                    );


                if (inputsSerial.length !== cantidad) {

                    throw new Error(
                        `El producto "${producto.nombre}" requiere ${cantidad} equipo(s) serializado(s).`
                    );
                }


                // =================================================
                // PROCESAR CADA EQUIPO
                // =================================================

                for (const inputSerial of inputsSerial) {

                    const filaEquipo =
                        inputSerial.closest('div');


                    const serial =
                        inputSerial.value.trim();


                    const selectMarca =
                        filaEquipo.querySelector(
                            '.marca-equipo'
                        );


                    const selectModelo =
                        filaEquipo.querySelector(
                            '.modelo-equipo'
                        );


                    const inputNuevaMarca =
                        filaEquipo.querySelector(
                            '.nueva-marca'
                        );


                    const inputNuevoModelo =
                        filaEquipo.querySelector(
                            '.nuevo-modelo'
                        );


                    // =============================================
                    // SERIAL
                    // =============================================

                    if (!serial) {

                        throw new Error(
                            'Todos los equipos serializados deben tener serial.'
                        );
                    }


                    // =============================================
                    // MARCA
                    // =============================================

                    let marcaId = null;


                    // ---------------------------------------------
                    // Marca nueva
                    // ---------------------------------------------

                    if (
                        selectMarca &&
                        selectMarca.value === '__nueva__'
                    ) {

                        const nombreMarca =
                            inputNuevaMarca?.value.trim();


                        if (!nombreMarca) {

                            throw new Error(
                                `Escribe la nueva marca para el equipo ${serial}.`
                            );
                        }


                        marcaId =
                            await guardarMarcaEnCatalogo(
                                nombreMarca
                            );

                    }


                    // ---------------------------------------------
                    // Marca existente
                    // ---------------------------------------------

                    else {

                        marcaId =
                            parseInt(
                                selectMarca?.value
                            );


                        if (!marcaId) {

                            throw new Error(
                                `Selecciona una marca para el equipo ${serial}.`
                            );
                        }
                    }


                    // =================================================
                    // MODELO
                    // =================================================

                    let modeloId = null;


                    // ---------------------------------------------
                    // Modelo nuevo
                    // ---------------------------------------------

                    if (
                        selectModelo &&
                        selectModelo.value === '__nuevo__'
                    ) {

                        const nombreModelo =
                            inputNuevoModelo?.value.trim();


                        if (!nombreModelo) {

                            throw new Error(
                                `Escribe el nuevo modelo para el equipo ${serial}.`
                            );
                        }


                        modeloId =
                            await guardarModeloEnCatalogo(
                                nombreModelo,
                                marcaId
                            );
                    }


                    // ---------------------------------------------
                    // Marca nueva
                    // El modelo también se escribe manualmente
                    // ---------------------------------------------

                    else if (
                        selectMarca &&
                        selectMarca.value === '__nueva__'
                    ) {

                        const nombreModelo =
                            inputNuevoModelo?.value.trim();


                        if (!nombreModelo) {

                            throw new Error(
                                `Escribe el nuevo modelo para el equipo ${serial}.`
                            );
                        }


                        modeloId =
                            await guardarModeloEnCatalogo(
                                nombreModelo,
                                marcaId
                            );
                    }


                    // ---------------------------------------------
                    // Modelo existente
                    // ---------------------------------------------

                    else {

                        modeloId =
                            parseInt(
                                selectModelo?.value
                            );


                        if (!modeloId) {

                            throw new Error(
                                `Selecciona un modelo para el equipo ${serial}.`
                            );
                        }
                    }


                    // =================================================
                    // VERIFICAR MODELO
                    // =================================================

                    const modelo =
                        catalogoModelos.find(
                            m =>
                                Number(m.id) ===
                                Number(modeloId)
                        );


                    if (!modelo) {

                        throw new Error(
                            `No se encontró el modelo para el equipo ${serial}.`
                        );
                    }


                    if (
                        Number(modelo.marca_id) !==
                        Number(marcaId)
                    ) {

                        throw new Error(
                            `El modelo "${modelo.nombre}" no pertenece a la marca seleccionada.`
                        );
                    }


                    // =================================================
                    // AGREGAR EQUIPO
                    // =================================================

                    item.unidades.push({

                        serial: serial,

                        modelo_id:
                            Number(modeloId)

                    });
                }
            }


            // =====================================================
            // PRODUCTO NO SERIALIZADO
            // =====================================================

            else {

                item.unidades = [];
            }


            // =====================================================
            // AGREGAR DETALLE
            // =====================================================

            detalle.push(item);
        }


        // =========================================================
        // ORIGEN
        // =========================================================
        //
        // IMPORTANTE:
        // El HTML antiguo probablemente tiene ent-obra.
        //
        // Primero intentamos ent-origen.
        // Si todavía existe ent-obra, lo usamos como respaldo.
        //
        // Así no se rompe mientras actualizamos el HTML.
        // =========================================================

        const campoOrigen =
            document.getElementById('ent-origen') ||
            document.getElementById('ent-obra');


        const origen =
            campoOrigen
                ? campoOrigen.value.trim()
                : '';

        console.log('ORIGEN LEÍDO DEL FORMULARIO:', origen);
        console.log('CAMPO ORIGEN:', campoOrigen);

        // =========================================================
        // DESTINO
        // =========================================================
        //
        // Para una entrada normal siempre es Almacén.
        // Si posteriormente quieres manejar otros destinos,
        // podremos convertirlo nuevamente en un campo seleccionable.
        // =========================================================

        const destino =
            'Almacén';


        // =========================================================
        // OBSERVACIONES
        // =========================================================

        const campoObservaciones =
            document.getElementById(
                'ent-observaciones'
            );


        const observaciones =
            campoObservaciones
                ? campoObservaciones.value.trim()
                : '';


        // =========================================================
        // SEDE
        // =========================================================

        const campoSede =
            document.getElementById(
                'ent-sede'
            );


        const sedeId =
            parseInt(
                campoSede?.value
            ) || sedeActual;


        // =========================================================
        // DATOS DE LA ENTRADA
        // =========================================================

        const datos = {

            numero_documento:
                numero,

            origen:
                origen,

            destino:
                destino,

            observaciones:
                observaciones,

            sede_id:
                sedeId,

            detalle:
                detalle
        };


        console.log(
            'DATOS ENVIADOS ENTRADA:',
            datos
        );

        console.log('DATOS QUE SE ENVIARÁN A ENTRADAS:', datos);

        // =========================================================
        // ENVIAR AL BACKEND
        // =========================================================

        const res =
            await apiFetch(
                `${API}/entradas/`,
                {
                    method: 'POST',

                    body:
                        JSON.stringify(datos)
                }
            );


        if (!res) return;


        const resultado =
            await res.json();


        // =========================================================
        // ERROR
        // =========================================================

        if (!res.ok) {

            console.error(
                'RESPUESTA DEL BACKEND AL GUARDAR ENTRADA:',
                resultado
            );
        
            throw new Error(
                resultado.error ||
                'No se pudo guardar la entrada.'
            );
        }


        // =========================================================
        // ÉXITO
        // =========================================================

        mostrarNotificacion(
            'Entrada registrada correctamente.',
            'exito'
        );


        cerrarModal(
            'modal-entrada'
        );


        limpiarFormEntrada();


        await cargarEntradas();


        await cargarProductos();


    } catch (error) {

        console.error(
            'Error al guardar entrada:',
            error
        );


        alert(
            'No se pudo guardar la entrada:\n\n' +
            error.message
        );
    }
}

function limpiarFormEntrada() {
    const entNumero = document.getElementById('ent-numero');
    const entFecha = document.getElementById('ent-fecha');
    const entOrigen = document.getElementById('ent-origen');
    const entObra = document.getElementById('ent-obra');
    const entDestino = document.getElementById('ent-destino');
    const entObservaciones = document.getElementById('ent-observaciones');
    const entSede = document.getElementById('ent-sede');
    const entItems = document.getElementById('ent-items');

    if (entNumero) {
        entNumero.value = '';
    }

    if (entFecha) {
        entFecha.value = '';
    }

    if (entOrigen) {
        entOrigen.value = '';
    }

    if (entObra) {
        entObra.value = '';
    }

    if (entDestino) {
        entDestino.value = 'Almacén';
    }

    if (entObservaciones) {
        entObservaciones.value = '';
    }

    if (entSede) {
        entSede.value = '';
    }

    if (entItems) {
        entItems.innerHTML = '';
    }
}

function verPDFEntrada(id) {
    window.open(`${API}/pdf/entrada/${id}?token=${token}`, '_blank');
}

async function eliminarEntrada(id, numero) {
    if (!await mostrarConfirm(`¿Eliminar la entrada "${numero}"? Esto revertira el stock.`)) return;
    await apiFetch(`${API}/entradas/${id}`, { method: 'DELETE' });
    cargarEntradas();
    cargarProductos();
}

// ══ SALIDAS ═════════════════════════════════════════════════

let productosCacheSalida = [];

async function generarNumeroSalida() {
    const fecha   = document.getElementById('sal-fecha').value;
    const destino = document.getElementById('sal-destino').value.trim();
    if (!fecha || !destino) return;
    const base       = `SAL-${fecha}-${destino.toUpperCase().replace(/ /g, '-')}`;
    const res        = await apiFetch(`${API}/salidas/`);
    if (!res) return;
    const salidas    = await res.json();
    const existentes = salidas.filter(s => s.numero_documento.startsWith(base));
    document.getElementById('sal-numero').value = `${base}-${existentes.length + 1}`;
}

let salidasCache = [];
let devolucionesCache = [];

async function cargarSalidas() {
    const res = await apiFetch(urlConSede(`${API}/salidas/`));
    if (!res) return;
    salidasCache = await res.json();

    // Guarda el id más alto ya visto para que, cuando arranque
    // el sondeo de portería, solo suene la alarma por salidas
    // que lleguen DESPUÉS de esta carga inicial. Se establece
    // la base SIEMPRE (incluso en 0, si todavía no hay ninguna
    // salida) — si no, la primera salida que llegue se toma
    // por error como si fuera solo el punto de partida, y
    // nunca suena la alarma.
    if (
        usuario.rol === 'porteria' &&
        ultimoIdSalidaPorteria === null
    ) {
        ultimoIdSalidaPorteria =
            Array.isArray(salidasCache) && salidasCache.length > 0
                ? Math.max(...salidasCache.map(s => s.id))
                : 0;
    }

    if (usuario.rol === 'admin' || usuario.rol === 'consulta') {
        const sel = document.getElementById('filtro-sede-salidas');
        const valorActual = sel.value;

        const resSedes = await apiFetch(`${API}/auth/sedes`);
        if (resSedes) {
            const sedes = await resSedes.json();
            sel.innerHTML = '<option value="">&#8212; Todas las sedes &#8212;</option>';
            sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                `<option value="${s.id}">${s.nombre}</option>`
            ));
            sel.style.display = 'block';
            sel.value = valorActual;
        }
    }

    renderizarSalidas(salidasCache);
    filtrarSalidas();
}

// ══ ALERTA DE PORTERÍA ═══════════════════════════════════════
//
// Portería solo necesita ver Salidas, pero además debe
// enterarse apenas se registre una nueva sin tener que estar
// refrescando la página. Como es un puesto fijo con la
// pantalla siempre abierta, basta con revisar cada cierto
// tiempo si hay salidas nuevas (comparando el id más alto
// visto) y, si las hay, sonar un aviso y refrescar la tabla.

let ultimoIdSalidaPorteria = null;
let audioCtxPorteria       = null;

function iniciarPollingPorteria() {

    if (usuario.rol !== 'porteria') return;

    // Revisa cada 15 segundos.
    setInterval(
        verificarSalidasNuevasPorteria,
        15000
    );
}

async function verificarSalidasNuevasPorteria() {

    const res = await apiFetch(urlConSede(`${API}/salidas/`));

    if (!res || !res.ok) return;

    const salidas = await res.json();

    if (!Array.isArray(salidas)) return;

    const idMaximo =
        salidas.length > 0
            ? Math.max(...salidas.map(s => s.id))
            : 0;

    if (ultimoIdSalidaPorteria === null) {
        // No debería pasar (cargarSalidas ya deja la base
        // lista antes de que arranque este sondeo), pero por
        // si acaso: solo guardamos la referencia sin sonar la
        // alarma todavía.
        ultimoIdSalidaPorteria = idMaximo;
        return;
    }

    if (idMaximo > ultimoIdSalidaPorteria) {
        ultimoIdSalidaPorteria = idMaximo;

        salidasCache = salidas;
        renderizarSalidas(salidasCache);
        filtrarSalidas();

        reproducirSonidoAlertaPorteria();
        mostrarNotificacion('Nueva salida registrada', 'exito');
    }
}

function reproducirSonidoAlertaPorteria() {

    try {

        if (!audioCtxPorteria) {
            audioCtxPorteria =
                new (window.AudioContext || window.webkitAudioContext)();
        }

        const ctx   = audioCtxPorteria;
        const ahora = ctx.currentTime;

        // Dos tonos cortos para que se note claramente.
        [880, 1046].forEach((frecuencia, i) => {

            const osc  = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.type = 'sine';
            osc.frequency.value = frecuencia;

            const inicio = ahora + i * 0.35;

            gain.gain.setValueAtTime(0.3, inicio);
            gain.gain.exponentialRampToValueAtTime(0.001, inicio + 0.3);

            osc.start(inicio);
            osc.stop(inicio + 0.3);
        });

    } catch (error) {
        console.warn('No se pudo reproducir el sonido de alerta:', error);
    }
}

function renderizarSalidas(salidas) {
    document.getElementById('subtitulo-salidas').textContent =
        `${salidas.length} salidas registradas`;

    const tbody = document.getElementById('tabla-salidas');
    tbody.innerHTML = '';

    if (salidas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#6b8aab;padding:2rem">Sin salidas registradas</td></tr>';
        return;
    }

    salidas.forEach(s => {
        const fecha = new Date(s.fecha).toLocaleDateString('es-CO', {
            day: '2-digit', month: '2-digit', year: 'numeric'
        });
        tbody.insertAdjacentHTML('beforeend', `
            <tr>
                <td><strong>${s.numero_documento}</strong></td>
                <td>${s.obra || 'Almacen'}</td>
                <td>${s.destino || '—'}</td>
                <td><span style="font-size:11px;color:#4a6080">${s.sede_nombre || '—'}</span></td> 
                <td>${s.total_items} producto(s)</td>
                <td>${fecha}</td>
                <td>
                    <div class="acciones">
                        <button class="btn-accion" onclick="verPDFSalida(${s.id})">📄 PDF</button>
                        ${usuario.rol === 'admin' ? `
                            <button class="btn-accion danger" onclick="eliminarSalida(${s.id}, '${s.numero_documento}')">🗑️ Eliminar</button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `);
    });
}

function filtrarSalidas() {
    const texto = document.getElementById('buscar-salidas').value.trim().toLowerCase();
    const sedeFiltro = document.getElementById('filtro-sede-salidas')?.value;

    let filtradas = salidasCache;

    if (texto) {
        filtradas = filtradas.filter(s =>
            (s.numero_documento || '').toLowerCase().includes(texto) ||
            (s.obra || '').toLowerCase().includes(texto) ||
            (s.destino || '').toLowerCase().includes(texto)
        );
    }

    if (sedeFiltro) {
        filtradas = filtradas.filter(s => String(s.sede_id) === sedeFiltro);
    }

    renderizarSalidas(filtradas);
}

async function agregarItemSalida() {
    const sedeSalida =
        parseInt(document.getElementById('sal-sede').value) || sedeActual;

    const urlProductos =
        usuario.rol === 'admin' && sedeSalida
            ? `${API}/productos/?sede_id=${sedeSalida}`
            : urlConSede(`${API}/productos/`);

    const res = await apiFetch(urlProductos);
    if (!res) return;

    productosCacheSalida = await res.json();

    if (catalogoModelos.length === 0 && catalogoMarcas.length === 0) {
        await cargarCatalogos();
    }

    const opciones = productosCacheSalida
        .map(p => `
            <option
                value="${p.id}"
                data-stock="${p.stock || 0}"
                data-unidad="${p.unidad || 'UND'}"
                data-serializado="${p.requiere_serial ? '1' : '0'}">
                [${p.codigo || '—'}] ${p.nombre}
                (disp: ${p.stock || 0})
            </option>
        `)
        .join('');

    const unidadesDisponibles = [
        'UND',
        'MTS',
        'KG',
        'CAJA',
        'ROLLO',
        'LITRO'
    ];

    const opcionesUnidad = unidadesDisponibles
        .map(u => `<option value="${u}">${u}</option>`)
        .join('');

    const item = document.createElement('div');

    item.className = 'item-salida';

    item.style.cssText = `
        border:1px solid #d5e2f0;
        border-radius:8px;
        padding:8px;
        margin-bottom:8px;
        background:#f8fbff;
    `;

    item.innerHTML = `
        <div style="
            display:grid;
            grid-template-columns:1.6fr 70px 70px;
            gap:6px;
            align-items:start;
        ">

            <div style="position:relative;">

                <input
                    type="text"
                    class="buscador-producto"
                    placeholder="Escribe código o nombre..."
                    autocomplete="off"
                    style="
                        border:0.5px solid #c8d8ea;
                        border-radius:8px;
                        padding:6px 8px;
                        font-size:12px;
                        color:#0d2137;
                        width:100%;
                        height:32px;
                        box-sizing:border-box;
                    ">

                <div
                    class="resultados-producto"
                    style="
                        display:none;
                        position:absolute;
                        left:0;
                        right:0;
                        top:100%;
                        background:white;
                        border:0.5px solid #c8d8ea;
                        border-radius:8px;
                        margin-top:4px;
                        max-height:220px;
                        overflow-y:auto;
                        z-index:50;
                        box-shadow:0 4px 15px rgba(0,0,0,.12);
                    ">
                </div>

                <select
                    class="select-producto"
                    style="display:none">
                    <option value="">-- Selecciona un producto --</option>
                    ${opciones}
                </select>

            </div>

            <select
                class="select-unidad"
                style="
                    border:0.5px solid #c8d8ea;
                    border-radius:8px;
                    padding:6px 4px;
                    font-size:12px;
                    color:#0d2137;
                    width:100%;
                    height:32px;
                ">
                ${opcionesUnidad}
            </select>

            <input
                type="number"
                class="input-cantidad-salida"
                min="1"
                value="1"
                style="
                    border:0.5px solid #c8d8ea;
                    border-radius:8px;
                    padding:6px 8px;
                    font-size:12px;
                    text-align:center;
                    width:100%;
                    height:32px;
                    box-sizing:border-box;
                ">
        </div>

        <div
            class="equipos-salida-container"
            style="
                display:none;
                margin-top:8px;
                border-top:1px solid #dce7f2;
                padding-top:8px;
            ">

            <div style="
                font-weight:600;
                color:#315b87;
                font-size:13px;
                margin-bottom:7px;
            ">
                📦 Equipos serializados
            </div>

            <div class="equipos-salida-lista"></div>
        </div>

        <div style="
            margin-top:8px;
            display:flex;
            justify-content:flex-start;
        ">
            <button
                type="button"
                class="btn-quitar-salida"
                style="
                    background:#fdecea;
                    border:none;
                    border-radius:6px;
                    color:#c0392b;
                    cursor:pointer;
                    font-size:12px;
                    padding:6px 10px;
                ">
                ✕ Quitar producto
            </button>
        </div>
    `;

    document.getElementById('sal-items').appendChild(item);

    const selectProducto =
        item.querySelector('.select-producto');

    const selectUnidad =
        item.querySelector('.select-unidad');

    const inputCantidad =
        item.querySelector('.input-cantidad-salida');

    const contenedorEquipos =
        item.querySelector('.equipos-salida-container');

    const listaEquipos =
        item.querySelector('.equipos-salida-lista');

    const botonQuitar =
        item.querySelector('.btn-quitar-salida');

    let equiposDisponibles = [];

    inicializarBuscadorProducto(
        item,
        selectProducto,
        productosCacheSalida,
        true
    );

    botonQuitar.addEventListener('click', () => {
        item.remove();
    });

    function autocompletarUnidad() {
        const opcion =
            selectProducto.options[
                selectProducto.selectedIndex
            ];

        if (opcion) {
            selectUnidad.value =
                opcion.dataset.unidad || 'UND';
        }
    }

    function obtenerEquiposSeleccionados() {
        return Array.from(
            listaEquipos.querySelectorAll('.select-equipo-salida')
        )
            .map(select => parseInt(select.value))
            .filter(Boolean);
    }

    function refrescarOpcionesEquipos() {

        const filas =
            listaEquipos.querySelectorAll(
                '.fila-equipo-salida'
            );

        const usados = new Set();

        filas.forEach(fila => {

            const inputSerial =
                fila.querySelector(
                    '.input-serial-equipo'
                );

            const inputEquipoId =
                fila.querySelector(
                    '.select-equipo-salida'
                );

            const serial =
                inputSerial?.value
                    ?.trim()
                    ?.toLowerCase();

            const equipoId =
                parseInt(inputEquipoId?.value) || 0;

            if (serial) {

                if (usados.has(serial)) {

                    inputSerial.style.borderColor =
                        '#e74c3c';

                } else {

                    usados.add(serial);

                    if (equipoId) {
                        inputSerial.style.borderColor =
                            '#27ae60';
                    }
                }
            }
        });
    }

function crearFilaEquipo(indice) {

    const fila = document.createElement('div');

    fila.className = 'fila-equipo-salida';

    fila.style.cssText = `
        display:grid;
        grid-template-columns:45px 1.2fr 1fr 1fr;
        gap:6px;
        align-items:start;
        margin-bottom:6px;
    `;

    // Datalist con los seriales disponibles
    const idDatalist = `lista-seriales-salida-${Date.now()}-${indice}`;

    const opcionesSeriales = equiposDisponibles
        .filter(equipo => equipo.estado === 'DISPONIBLE')
        .map(equipo => `
            <option value="${equipo.serial || ''}">
                ${equipo.serial || 'SIN SERIAL'}
            </option>
        `)
        .join('');

    fila.innerHTML = `
        <div style="
            display:flex;
            align-items:center;
            justify-content:center;
            height:32px;
            background:#e8f1fa;
            border-radius:6px;
            color:#315b87;
            font-size:12px;
            font-weight:600;
        ">
            #${indice}
        </div>

        <!-- ID DEL EQUIPO -->
        <input
            type="hidden"
            class="select-equipo-salida"
            value=""
        >

        <!-- SERIAL -->
        <div>
            <input
                type="text"
                class="input-serial-equipo"
                list="${idDatalist}"
                placeholder="Escribe o escanea el serial"
                autocomplete="off"
                style="
                    width:100%;
                    height:32px;
                    box-sizing:border-box;
                    border:1px solid #c8d8ea;
                    border-radius:8px;
                    padding:6px 8px;
                    font-size:12px;
                    color:#0d2137;
                    background:white;
                "
            >

            <datalist id="${idDatalist}">
                ${opcionesSeriales}
            </datalist>
        </div>

        <!-- MARCA -->
        <input
            type="text"
            class="input-marca-equipo"
            placeholder="Marca"
            readonly
            style="
                width:100%;
                height:32px;
                box-sizing:border-box;
                border:1px solid #c8d8ea;
                border-radius:8px;
                padding:6px 8px;
                font-size:12px;
                color:#0d2137;
                background:#f1f5f9;
            "
        >

        <!-- MODELO -->
        <input
            type="text"
            class="input-modelo-equipo"
            placeholder="Modelo"
            readonly
            style="
                width:100%;
                height:32px;
                box-sizing:border-box;
                border:1px solid #c8d8ea;
                border-radius:8px;
                padding:6px 8px;
                font-size:12px;
                color:#0d2137;
                background:#f1f5f9;
            "
        >
    `;

    listaEquipos.appendChild(fila);

    const inputSerial =
        fila.querySelector('.input-serial-equipo');

    const inputEquipoId =
        fila.querySelector('.select-equipo-salida');

    const inputMarca =
        fila.querySelector('.input-marca-equipo');

    const inputModelo =
        fila.querySelector('.input-modelo-equipo');


    // --------------------------------------------------------
    // BUSCAR EQUIPO POR SERIAL
    // --------------------------------------------------------

    function buscarEquipoPorSerial(serial) {

        const serialBuscado =
            String(serial || '')
                .trim()
                .toLowerCase();

        if (!serialBuscado) {
            return null;
        }

        return equiposDisponibles.find(equipo =>
            String(equipo.serial || '')
                .trim()
                .toLowerCase() === serialBuscado
        );
    }


    // --------------------------------------------------------
    // VERIFICAR SI EL SERIAL YA ESTÁ UTILIZADO
    // --------------------------------------------------------

    function serialYaSeleccionado(serial) {

        const serialBuscado =
            String(serial || '')
                .trim()
                .toLowerCase();

        if (!serialBuscado) {
            return false;
        }

        const inputs =
            listaEquipos.querySelectorAll(
                '.input-serial-equipo'
            );

        let cantidad = 0;

        inputs.forEach(input => {

            const valor =
                String(input.value || '')
                    .trim()
                    .toLowerCase();

            if (valor === serialBuscado) {
                cantidad++;
            }
        });

        return cantidad > 1;
    }


    // --------------------------------------------------------
    // PROCESAR SERIAL
    // --------------------------------------------------------

    function procesarSerial() {

        const serial =
            inputSerial.value.trim();

        // Limpiar si está vacío
        if (!serial) {

            inputEquipoId.value = '';
            inputMarca.value = '';
            inputModelo.value = '';

            inputSerial.style.borderColor =
                '#c8d8ea';

            return;
        }

        // Buscar equipo
        const equipo =
            buscarEquipoPorSerial(serial);

        // No existe
        if (!equipo) {

            inputEquipoId.value = '';
            inputMarca.value = '';
            inputModelo.value = '';

            inputSerial.style.borderColor =
                '#e74c3c';

            return;
        }

        // Verificar duplicado
        if (serialYaSeleccionado(serial)) {

            mostrarNotificacionSalida(
                `El serial "${equipo.serial}" ya fue seleccionado.`,
                'error'
            );
        
            inputSerial.value = '';
            inputEquipoId.value = '';
            inputMarca.value = '';
            inputModelo.value = '';

            inputSerial.style.borderColor =
                '#e74c3c';

            inputSerial.focus();

            refrescarOpcionesEquipos();

            return;
        }

        // Guardar ID
        inputEquipoId.value =
            equipo.id;

        // Autocompletar marca
        inputMarca.value =
            equipo.marca_nombre || '';

        // Autocompletar modelo
        inputModelo.value =
            equipo.modelo_nombre || '';

        // Serial correcto
        inputSerial.style.borderColor =
            '#27ae60';

        refrescarOpcionesEquipos();
    }


    // --------------------------------------------------------
    // MIENTRAS ESCRIBE / ESCANEA
    // --------------------------------------------------------

    inputSerial.addEventListener(
        'input',
        () => {

            const serial =
                inputSerial.value.trim();

            const equipo =
                buscarEquipoPorSerial(serial);

            if (!equipo) {

                inputEquipoId.value = '';
                inputMarca.value = '';
                inputModelo.value = '';

                inputSerial.style.borderColor =
                    '#c8d8ea';

                return;
            }

            // Si encontró el serial automáticamente,
            // rellenamos marca y modelo
            procesarSerial();
        }
    );


    // --------------------------------------------------------
    // AL TERMINAR DE ESCRIBIR / ESCANEAR
    // --------------------------------------------------------

    inputSerial.addEventListener(
        'change',
        procesarSerial
    );

    inputSerial.addEventListener(
        'blur',
        () => {

            if (inputSerial.value.trim()) {
                procesarSerial();
            }
        }
    );
}

    async function actualizarEquiposSerializados() {
        const opcion =
            selectProducto.options[
                selectProducto.selectedIndex
            ];

        if (!opcion || !selectProducto.value) {
            contenedorEquipos.style.display = 'none';
            listaEquipos.innerHTML = '';
            return;
        }

        autocompletarUnidad();

        const esSerializado =
            opcion.dataset.serializado === '1';

        const stock =
            parseInt(opcion.dataset.stock) || 0;

        listaEquipos.innerHTML = '';

        if (!esSerializado) {
            contenedorEquipos.style.display = 'none';
            inputCantidad.max = stock || '';
            inputCantidad.value = Math.min(
                parseInt(inputCantidad.value) || 1,
                stock || 1
            );
            return;
        }

        const productoId =
            parseInt(selectProducto.value);

        contenedorEquipos.style.display = 'block';

        const respuesta =
            await apiFetch(
                `${API}/productos/${productoId}/equipos`
            );

        if (!respuesta) return;

        const datos =
            await respuesta.json();

        equiposDisponibles =
            (datos.equipos || [])
                .filter(
                    equipo =>
                        equipo.estado === 'DISPONIBLE'
                );

        if (equiposDisponibles.length === 0) {

            listaEquipos.innerHTML = `
                <div style="
                    color:#c0392b;
                    font-size:12px;
                    padding:5px;
                ">
                    No hay equipos disponibles para este producto.
                </div>
            `;

            inputCantidad.value = 0;
            inputCantidad.min = 0;
            inputCantidad.max = 0;

            return;
        }

        inputCantidad.min = 1;
        inputCantidad.max =
            equiposDisponibles.length;

        let cantidad =
            parseInt(inputCantidad.value) || 1;

        cantidad = Math.max(
            1,
            Math.min(
                cantidad,
                equiposDisponibles.length
            )
        );

        inputCantidad.value = cantidad;

        for (let i = 1; i <= cantidad; i++) {
            crearFilaEquipo(i);
        }

        refrescarOpcionesEquipos();
    }

    inputCantidad.addEventListener('input', () => {

        // Permitir borrar temporalmente el campo
        if (inputCantidad.value === '') {
            return;
        }

        const opcion =
            selectProducto.options[
                selectProducto.selectedIndex
            ];

        if (!opcion) return;

        const esSerializado =
            opcion.dataset.serializado === '1';

        let cantidad =
            parseInt(inputCantidad.value) || 1;

        // ==========================================================
        // PRODUCTOS NO SERIALIZADOS
        // ==========================================================

        if (!esSerializado) {

            const stock =
                parseInt(opcion.dataset.stock) || 0;

            cantidad = Math.max(1, cantidad);

            if (stock > 0) {
                cantidad = Math.min(cantidad, stock);
            }

            inputCantidad.value = cantidad;

            return;
        }

        // ==========================================================
        // PRODUCTOS SERIALIZADOS
        // ==========================================================

        cantidad = Math.max(
            1,
            Math.min(
                cantidad,
                equiposDisponibles.length || 1
            )
        );

        inputCantidad.value = cantidad;

        // ==========================================================
        // GUARDAR LOS SERIALES QUE YA EXISTEN
        // ==========================================================

        const anteriores =
            Array.from(
                listaEquipos.querySelectorAll(
                    '.fila-equipo-salida'
                )
            ).map(fila => {

                const inputSerial =
                    fila.querySelector(
                        '.input-serial-equipo'
                    );

                return {
                    serial:
                        inputSerial?.value?.trim() || ''
                };
            });

        // ==========================================================
        // RECREAR FILAS
        // ==========================================================

        listaEquipos.innerHTML = '';

        for (
            let i = 1;
            i <= cantidad;
            i++
        ) {
            crearFilaEquipo(i);
        }

        // ==========================================================
        // RESTAURAR LOS SERIALES ANTERIORES
        // ==========================================================

        const filasNuevas =
            listaEquipos.querySelectorAll(
                '.fila-equipo-salida'
            );

        anteriores.forEach(
            (anterior, index) => {

                if (
                    index >= cantidad ||
                    !anterior.serial
                ) {
                    return;
                }

                const fila =
                    filasNuevas[index];

                if (!fila) return;

                const inputSerial =
                    fila.querySelector(
                        '.input-serial-equipo'
                    );

                if (!inputSerial) return;

                inputSerial.value =
                    anterior.serial;

                inputSerial.dispatchEvent(
                    new Event('change')
                );
            }
        );

        refrescarOpcionesEquipos();
    });


    /* ==========================================================
    CORREGIR CANTIDAD AL SALIR DEL CAMPO
    ========================================================== */

    inputCantidad.addEventListener('blur', () => {

        const opcion =
            selectProducto.options[
                selectProducto.selectedIndex
            ];

        if (!opcion) return;

        const esSerializado =
            opcion.dataset.serializado === '1';

        let cantidad =
            parseInt(inputCantidad.value);

        if (!cantidad || cantidad < 1) {
            cantidad = 1;
        }

        // PRODUCTO NORMAL
        if (!esSerializado) {

            const stock =
                parseInt(opcion.dataset.stock) || 0;

            cantidad = Math.max(1, cantidad);

            if (stock > 0) {
                cantidad = Math.min(cantidad, stock);
            }
        
            inputCantidad.value = cantidad;
        
            return;
        }

        // PRODUCTO SERIALIZADO
        cantidad = Math.min(
            cantidad,
            equiposDisponibles.length
        );

        cantidad = Math.max(1, cantidad);

        inputCantidad.value = cantidad;

        inputCantidad.dispatchEvent(
            new Event('input')
        );
    });

    selectProducto.addEventListener(
        'change',
        async () => {
            equiposDisponibles = [];
            await actualizarEquiposSerializados();
        }
    );

    autocompletarUnidad();

    await actualizarEquiposSerializados();
}

function mostrarNotificacionSalida(mensaje, tipo = 'error') {

    let contenedor =
        document.getElementById('notificaciones-salida');

    if (!contenedor) {

        contenedor = document.createElement('div');

        contenedor.id =
            'notificaciones-salida';

        contenedor.style.cssText = `
            position:fixed;
            top:20px;
            right:20px;
            z-index:99999;
            display:flex;
            flex-direction:column;
            gap:10px;
            pointer-events:none;
        `;

        document.body.appendChild(contenedor);
    }

    const notificacion =
        document.createElement('div');

    const esError =
        tipo === 'error';

    notificacion.style.cssText = `
        min-width:300px;
        max-width:420px;
        padding:14px 16px;
        border-radius:10px;
        background:${esError ? '#fff5f5' : '#f0fff4'};
        border:1px solid ${esError ? '#f5c2c7' : '#b7e4c7'};
        box-shadow:0 6px 20px rgba(0,0,0,0.15);
        color:#263238;
        font-size:13px;
        display:flex;
        align-items:flex-start;
        gap:10px;
        pointer-events:auto;
        animation:entradaNotificacion .25s ease;
    `;

    notificacion.innerHTML = `
        <div style="
            font-size:18px;
            line-height:1;
        ">
            ${esError ? '⚠️' : '✓'}
        </div>

        <div style="
            flex:1;
            line-height:1.4;
        ">
            ${mensaje}
        </div>

        <button
            type="button"
            style="
                border:none;
                background:transparent;
                color:#777;
                font-size:16px;
                cursor:pointer;
                padding:0;
            "
        >
            ×
        </button>
    `;

    const botonCerrar =
        notificacion.querySelector('button');

    botonCerrar.addEventListener(
        'click',
        () => notificacion.remove()
    );

    contenedor.appendChild(notificacion);

    setTimeout(() => {

        if (notificacion.parentNode) {
            notificacion.remove();
        }

    }, 3500);
}

async function guardarSalida(event) {
    event.preventDefault();

    const numero =
        document.getElementById('sal-numero').value;

    if (!numero) {
        mostrarNotificacionSalida(
            'Escribe el Destino para generar el número de documento.',
            'error'
        );
        return;
    }

    const filas =
        document
            .getElementById('sal-items')
            .querySelectorAll(':scope > .item-salida');

    if (filas.length === 0) {
        mostrarNotificacionSalida(
            'Agrega al menos un producto.',
            'error'
        );
        return;
    }

    const detalle = [];

    for (const fila of filas) {

        const selectProducto =
            fila.querySelector('.select-producto');

        const selectUnidad =
            fila.querySelector('.select-unidad');

        const inputCantidad =
            fila.querySelector('.input-cantidad-salida');

        const opcion =
            selectProducto.options[
                selectProducto.selectedIndex
            ];

        if (!opcion || !selectProducto.value) {
            mostrarNotificacionSalida(
                'Selecciona un producto en todas las filas.',
                'error'
            );
            return;
        }

        const productoId =
            parseInt(selectProducto.value);

        const esSerializado =
            opcion.dataset.serializado === '1';

        const cantidad =
            parseInt(inputCantidad.value) || 0;

        if (cantidad <= 0) {
            mostrarNotificacionSalida(
                'La cantidad debe ser mayor que cero.',
                'error'
            );
            return;
        }

        // ==========================================================
        // PRODUCTO SERIALIZADO
        // ==========================================================

        if (esSerializado) {

            const filasEquipos =
                fila.querySelectorAll(
                    '.fila-equipo-salida'
                );

            if (
                filasEquipos.length !==
                cantidad
            ) {
                mostrarNotificacionSalida(
                    'La cantidad de equipos seleccionados no coincide con la cantidad indicada.',
                    'error'
                );
                return;
            }

            const unidades = [];

            for (
                const filaEquipo
                of filasEquipos
            ) {

                // ID interno del equipo
                const inputEquipoId =
                    filaEquipo.querySelector(
                        '.select-equipo-salida'
                    );

                const equipoId =
                    parseInt(
                        inputEquipoId?.value
                    ) || 0;

                // Serial escrito o escaneado
                const inputSerial =
                    filaEquipo.querySelector(
                        '.input-serial-equipo'
                    );

                const serial =
                    inputSerial?.value?.trim() || '';

                // --------------------------------------------------
                // VALIDAR SERIAL VACÍO
                // --------------------------------------------------

                if (!serial) {

                    mostrarNotificacionSalida(
                        'Debes escribir o escanear un serial para cada equipo.',
                        'error'
                    );

                    inputSerial?.focus();

                    return;
                }

                // --------------------------------------------------
                // VALIDAR EQUIPO
                // --------------------------------------------------

                if (!equipoId) {

                    mostrarNotificacionSalida(
                        `El serial "${serial}" no corresponde a un equipo disponible.`,
                        'error'
                    );

                    inputSerial?.focus();

                    return;
                }

                // --------------------------------------------------
                // VALIDAR DUPLICADO POR SERIAL
                // --------------------------------------------------

                const serialesActuales =
                    unidades.map(
                        u =>
                            String(u.serial)
                                .trim()
                                .toLowerCase()
                    );

                if (
                    serialesActuales.includes(
                        serial.toLowerCase()
                    )
                ) {

                    mostrarNotificacionSalida(
                        `El serial "${serial}" está repetido. No puedes utilizar el mismo serial más de una vez.`,
                        'error'
                    );

                    inputSerial.focus();

                    return;
                }

                // --------------------------------------------------
                // AGREGAR EQUIPO
                // --------------------------------------------------

                unidades.push({
                    equipo_id: equipoId,
                    serial: serial
                });
            }

            // ------------------------------------------------------
            // VALIDAR DUPLICADOS POR ID
            // ------------------------------------------------------

            const ids =
                unidades.map(
                    u => u.equipo_id
                );

            if (
                new Set(ids).size !==
                ids.length
            ) {

                mostrarNotificacionSalida(
                    'No puedes seleccionar el mismo equipo/serial más de una vez.',
                    'error'
                );

                return;
            }

            // ------------------------------------------------------
            // AGREGAR DETALLE
            // ------------------------------------------------------

            detalle.push({
                producto_id: productoId,

                unidad:
                    selectUnidad.value ||
                    'UND',

                cantidad:
                    cantidad,

                unidades:
                    unidades
            });

        } else {

            // ======================================================
            // PRODUCTO NORMAL
            // ======================================================

            detalle.push({
                producto_id: productoId,

                unidad:
                    selectUnidad.value ||
                    'UND',

                cantidad:
                    cantidad,

                unidades: []
            });
        }
    }

    // ==========================================================
    // DATOS DE LA SALIDA
    // ==========================================================

    const datos = {

        numero_documento:
            numero,

        obra:
            document.getElementById('sal-obra').value ||
            'Almacen',

        destino:
            document.getElementById('sal-destino').value,

        cliente:
            document.getElementById('sal-cliente')?.value
                ?.trim() || '',

        observaciones:
            document.getElementById(
                'sal-observaciones'
            ).value,

        sede_id:
            parseInt(
                document.getElementById(
                    'sal-sede'
                ).value
            ) || sedeActual,

        detalle:
            detalle
    };

    console.log(
        'DATOS ENVIADOS SALIDA:',
        datos
    );

    // ==========================================================
    // GUARDAR EN BACKEND
    // ==========================================================

    const res =
        await apiFetch(
            `${API}/salidas/`,
            {
                method: 'POST',

                body:
                    JSON.stringify(datos)
            }
        );

    if (!res) return;

    const resultado =
        await res.json();

    // ==========================================================
    // ÉXITO
    // ==========================================================

    if (res.ok) {

        await cargarCatalogos();

        cerrarModal(
            'modal-salida'
        );

        limpiarFormSalida();

        cargarSalidas();

        cargarProductos();

    } else {

        mostrarNotificacionSalida(
            'Error: ' +
            (
                resultado.error ||
                'No se pudo registrar la salida.'
            ),
            'error'
        );
    }
}

function limpiarFormSalida() {
    document.getElementById('sal-numero').value        = '';
    document.getElementById('sal-fecha').value         = '';
    document.getElementById('sal-obra').value          = 'Almacen';
    document.getElementById('sal-destino').value       = '';
    document.getElementById('sal-cliente').value       = '';
    document.getElementById('sal-observaciones').value = '';
    document.getElementById('sal-items').innerHTML     = '';
    document.getElementById('sal-sede').value = '';
    productosCacheSalida = [];
}

function verPDFSalida(id) {
    window.open(`${API}/pdf/salida/${id}?token=${token}`, '_blank');
}

async function eliminarSalida(id, numero) {
    if (!await mostrarConfirm(`¿Eliminar la salida "${numero}"? Esto devolvera el stock descontado.`)) return;
    await apiFetch(`${API}/salidas/${id}`, { method: 'DELETE' });
    cargarSalidas();
    cargarProductos();
}

// ══ DEVOLUCIONES ════════════════════════════════════════════

async function cargarSelectorSalidas() {
    const sedeDev = parseInt(document.getElementById('dev-sede').value) || sedeActual;
    const url = usuario.rol === 'admin' && sedeDev
        ? `${API}/devoluciones/salidas-disponibles?sede_id=${sedeDev}`
        : `${API}/devoluciones/salidas-disponibles`;

    const res = await apiFetch(url);
    if (!res) return;
    const salidas = await res.json();

    const select = document.getElementById('dev-salida');
    select.innerHTML = '<option value="">— Selecciona la salida —</option>';

    salidas.forEach(s => {
        const fecha = new Date(s.fecha).toLocaleDateString('es-CO', {
            day: '2-digit', month: '2-digit', year: 'numeric'
        });
        select.insertAdjacentHTML('beforeend',
            `<option value="${s.id}" data-destino="${s.destino || ''}">${s.numero_documento} — ${s.destino || 'sin destino'} (${fecha})</option>`
        );
    });
}

// Normaliza texto para comparar búsquedas sin que le afecten
// espacios "raros" (espacios de ancho fijo, NBSP, etc.) ni
// caracteres invisibles de ancho cero que a veces quedan
// pegados en datos digitados o copiados desde Word/otras apps.
// Visualmente son indistinguibles de un espacio normal, pero
// una comparación exacta de texto los trata como diferentes.
function normalizarBusqueda(texto) {
    return String(texto || '')
        .normalize('NFKC')
        .replace(/[\u200B-\u200D\uFEFF]/g, '')
        .replace(/\s+/g, ' ')
        .trim()
        .toLowerCase();
}

// ================================================================
// BUSCADOR DE PRODUCTOS (Entradas, Salidas, Traslados)
//
// Convierte un <select> normal (oculto) en un campo donde se
// puede escribir el c\u00F3digo o el nombre del producto para
// filtrarlo, en vez de tener que buscarlo uno por uno en una
// lista larga.
//
// El <select> original NO se toca ni se elimina: sigue teniendo
// todas sus <option> con sus data-* (unidad, stock, serializado,
// etc.), as\u00ED que todo el c\u00F3digo que ya lee ese <select> (unidad
// autom\u00E1tica, seriales, stock disponible...) sigue funcionando
// igual. Solo se oculta visualmente y se controla desde el
// campo de texto de al lado.
// ================================================================

function inicializarBuscadorProducto(
    fila,
    selectOculto,
    listaProductos,
    mostrarTodoSiVacio = false
) {

    const buscador =
        fila.querySelector('.buscador-producto');

    const resultados =
        fila.querySelector('.resultados-producto');

    if (!buscador || !resultados || !selectOculto) return;

    function sincronizarTexto() {

        const opcion =
            selectOculto.options[selectOculto.selectedIndex];

        buscador.value = (opcion && opcion.value)
            ? opcion.textContent.replace(/\s+/g, ' ').trim()
            : '';
    }

    function cerrarResultados() {
        resultados.style.display = 'none';
        resultados.innerHTML = '';
    }

    function seleccionarProducto(producto) {

        selectOculto.value = producto.id;
        selectOculto.dispatchEvent(new Event('change'));

        sincronizarTexto();
        cerrarResultados();
    }

    function filtrar() {

        const texto = normalizarBusqueda(buscador.value);

        if (!texto) {
            if (mostrarTodoSiVacio) {
                pintarResultados(listaProductos);
            } else {
                cerrarResultados();
            }
            return;
        }

        const coincidencias = listaProductos.filter(p =>
            normalizarBusqueda(p.codigo).includes(texto) ||
            normalizarBusqueda(p.nombre).includes(texto)
        );

        pintarResultados(coincidencias);
    }

    function pintarResultados(coincidencias) {

        resultados.innerHTML = '';

        if (coincidencias.length === 0) {
            resultados.innerHTML = `
                <div style="
                    padding:10px 12px;
                    font-size:12px;
                    color:#6b8aab;
                ">
                    No se encontraron productos con ese c\u00F3digo o nombre.
                </div>
            `;
            resultados.style.display = 'block';
            return;
        }

        coincidencias.slice(0, 50).forEach(p => {

            const opcionDiv = document.createElement('div');

            opcionDiv.style.cssText = `
                padding:8px 10px;
                cursor:pointer;
                border-bottom:0.5px solid #edf2f7;
                font-size:12.5px;
                color:#0d2137;
            `;

            opcionDiv.innerHTML = `
                <strong>[${sanitizar(p.codigo || '\u2014')}]</strong>
                ${sanitizar(p.nombre)}
                ${p.stock !== undefined
                    ? `<span style="color:#6b8aab;font-size:11px"> (disp: ${p.stock || 0})</span>`
                    : ''}
            `;

            opcionDiv.onmouseenter = () => {
                opcionDiv.style.background = '#f5f8fc';
            };

            opcionDiv.onmouseleave = () => {
                opcionDiv.style.background = 'white';
            };

            // mousedown (no click) para que se dispare antes
            // del "blur" del campo de texto
            opcionDiv.onmousedown = (ev) => {
                ev.preventDefault();
                seleccionarProducto(p);
            };

            resultados.appendChild(opcionDiv);
        });

        resultados.style.display = 'block';
    }

    buscador.addEventListener('input', filtrar);

    buscador.addEventListener('focus', () => {
        buscador.select();
        filtrar();
    });

    buscador.addEventListener('blur', () => {
        setTimeout(() => {
            cerrarResultados();
            sincronizarTexto();
        }, 150);
    });

    sincronizarTexto();
}

function filtrarPuntos() {
    const texto = normalizarBusqueda(
        document.getElementById('buscar-punto').value
    );

    const filtrados = !texto
        ? puntosCache
        : puntosCache.filter(p =>
            normalizarBusqueda(p.destino).includes(texto) ||
            normalizarBusqueda(p.sede_nombre).includes(texto)
        );

    pintarSelectorPuntos(filtrados);

    // Si al escribir queda un solo punto que coincide, se
    // selecciona y se carga su historial automáticamente,
    // sin que el usuario tenga que abrir el desplegable y
    // elegirlo a mano.
    if (texto && filtrados.length === 1) {
        const select = document.getElementById('selector-punto');
        select.value = filtrados[0].destino;
        cargarHistorialPunto();
    }
}

async function cargarItemsDeSalida() {

    const salidaHidden =
        document.getElementById('dev-salida');

    const salidaId =
        salidaHidden.value;

    const contenedor =
        document.getElementById('dev-items');

    if (!salidaId) {

        contenedor.innerHTML =
            '<p style="font-size:12px;color:#6b8aab">' +
            'Selecciona primero una salida arriba.' +
            '</p>';

        document.getElementById('dev-origen').value = '';

        return;
    }

    generarNumeroDevolucion();

    const res = await apiFetch(
        `${API}/devoluciones/salida/${salidaId}/items`
    );

    if (!res) return;

    const items = await res.json();

    if (items.length === 0) {

        contenedor.innerHTML =
            '<p style="font-size:12px;color:#6b8aab">' +
            'Esta salida no tiene productos pendientes por devolver.' +
            '</p>';

        return;
    }

    contenedor.innerHTML = items.map(item => {

        const serializado =
            item.requiere_serial;

        const serial =
            item.serial || '—';

        const modelo =
            item.modelo_nombre || '—';

        const marca =
            item.marca_nombre || '—';

        return `

            <div
                class="dev-item-fila"

                data-producto-id="${item.producto_id}"

                data-equipo-id="${item.equipo_id || ''}"

                data-serial="${serial}"

                data-modelo="${modelo}"

                data-marca="${marca}"

                data-unidad="${item.unidad || 'UND'}"

                data-requiere-serial="${serializado}"

                style="
                    display:grid;
                    grid-template-columns:
                        24px
                        2fr
                        1fr
                        70px;

                    gap:8px;
                    align-items:center;

                    padding:8px;

                    border:
                        0.5px solid #dce6f0;

                    border-radius:8px;

                    margin-bottom:6px;
                "
            >

                <input
                    type="checkbox"
                    class="dev-check"

                    style="
                        width:16px;
                        height:16px;
                    "
                >

                <div>

                    <strong
                        style="font-size:12.5px"
                    >
                        ${item.nombre}
                    </strong>

                    <div
                        style="
                            font-size:11px;
                            color:#6b8aab;
                            margin-top:3px;
                        "
                    >

                        ${serializado ? `

                            <strong>
                                🔢 Serial:
                            </strong>

                            ${serial}

                            <br>

                            <strong>
                                📦 Modelo:
                            </strong>

                            ${modelo}

                            <br>

                            <strong>
                                🏷️ Marca:
                            </strong>

                            ${marca}

                        ` : `

                            Producto no serializado

                        `}

                    </div>

                </div>

                <div
                    style="
                        font-size:11px;
                        color:#6b8aab;
                    "
                >

                    Salió:
                    ${item.cantidad_original || item.cantidad}

                    ${item.unidad || ''}

                    <br>

                    Pendiente:
                    ${item.cantidad}

                </div>

                <input

                    type="number"

                    class="dev-cantidad"

                    min="1"

                    max="${item.cantidad}"

                    value="${item.cantidad}"

                    ${serializado ? 'readonly' : ''}

                    style="
                        border:
                            0.5px solid #c8d8ea;

                        border-radius:8px;

                        padding:6px;

                        font-size:12px;

                        text-align:center;
                    "
                >

            </div>

        `;

    }).join('');

}

async function generarNumeroDevolucion() {
    const fecha  = document.getElementById('dev-fecha').value;
    const origen = document.getElementById('dev-origen').value.trim();
    if (!fecha || !origen) return;

    const base       = `DEV-${fecha}-${origen.toUpperCase().replace(/ /g, '-')}`;
    const res        = await apiFetch(`${API}/devoluciones/`);
    if (!res) return;
    const devs       = await res.json();
    const existentes = devs.filter(d => d.numero_documento.startsWith(base));
    document.getElementById('dev-numero').value = `${base}-${existentes.length + 1}`;
}

function abrirNuevaDevolucion() {

    limpiarFormDevolucion();

    const fecha =
        document.getElementById('dev-fecha');

    if (fecha) {
        fecha.value =
            new Date()
                .toISOString()
                .split('T')[0];
    }

    cargarSalidasDisponibles();

    abrirModal('modal-devolucion');
}

function buscarSalidasDevolucion() {

    const buscador =
        document.getElementById('dev-salida-busqueda');

    const resultados =
        document.getElementById('dev-salida-resultados');

    const salidaHidden =
        document.getElementById('dev-salida');

    if (!buscador || !resultados || !salidaHidden) return;

    const texto =
        buscador.value
            .trim()
            .toLowerCase();

    // Si el usuario vuelve a escribir,
    // quitamos la salida seleccionada anteriormente
    salidaHidden.value = '';

    if (!texto) {

        resultados.innerHTML = '';
        resultados.style.display = 'none';

        return;
    }

    const coincidencias =
        salidasDisponiblesDevolucion.filter(salida => {

            const numero =
                String(
                    salida.numero_documento || ''
                ).toLowerCase();

            const destino =
                String(
                    salida.destino || ''
                ).toLowerCase();

            return (
                numero.includes(texto) ||
                destino.includes(texto)
            );
        });

    resultados.innerHTML = '';

    if (coincidencias.length === 0) {

        resultados.innerHTML =
            '<div style="' +
            'padding:12px;' +
            'font-size:12px;' +
            'color:#6b8aab;' +
            '">' +
            'No se encontraron salidas con ese nombre.' +
            '</div>';

        resultados.style.display = 'block';

        return;
    }

    coincidencias.forEach(salida => {

        const fecha =
            salida.fecha
                ? new Date(
                    salida.fecha
                ).toLocaleDateString(
                    'es-CO',
                    {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric'
                    }
                )
                : '';

        const resultado =
            document.createElement('div');

        resultado.style.cssText = `
            padding:10px 12px;
            cursor:pointer;
            border-bottom:0.5px solid #edf2f7;
            font-size:12.5px;
            color:#0d2137;
        `;

        resultado.innerHTML = `
            <strong>
                ${salida.numero_documento || 'Sin número'}
            </strong>

            <span style="color:#4a6080">
                — ${salida.destino || 'Sin destino'}
            </span>

            <div style="
                font-size:11px;
                color:#6b8aab;
                margin-top:3px;
            ">
                ${fecha}
            </div>
        `;

        resultado.onmouseenter = () => {
            resultado.style.background = '#f5f8fc';
        };

        resultado.onmouseleave = () => {
            resultado.style.background = 'white';
        };

        resultado.onclick = () => {

            seleccionarSalidaDevolucion(salida);

        };

        resultados.appendChild(resultado);
    });

    resultados.style.display = 'block';
}

function seleccionarSalidaDevolucion(salida) {

    const buscador =
        document.getElementById('dev-salida-busqueda');

    const salidaHidden =
        document.getElementById('dev-salida');

    const resultados =
        document.getElementById('dev-salida-resultados');

    const origen =
        document.getElementById('dev-origen');

    const cliente =
        document.getElementById('dev-cliente');

    if (!buscador || !salidaHidden) return;

    // Guardar el ID real de la salida
    salidaHidden.value = salida.id;

    // Mostrar la salida seleccionada
    buscador.value =
        `${salida.numero_documento} — ${salida.destino || 'Sin destino'}`;

    // Mostrar de dónde procede
    if (origen) {
        origen.value =
            salida.destino || '';
    }

    // Mostrar el cliente de esa salida (solo lectura,
    // se toma tal cual quedó registrado en la salida)
    if (cliente) {
        cliente.value =
            salida.cliente_nombre || '—';
    }

    // Ocultar resultados
    if (resultados) {
        resultados.style.display = 'none';
    }

    // Cargar productos de la salida
    cargarItemsDeSalida();
}

async function cargarDevoluciones() {
    const res = await apiFetch(urlConSede(`${API}/devoluciones/`));

    if (!res) return;

    devolucionesCache = await res.json();

    if (usuario.rol === 'admin' || usuario.rol === 'consulta') {
        const sel = document.getElementById('filtro-sede-devoluciones');

        if (sel) {
            const valorActual = sel.value;

            const resSedes =
                await apiFetch(`${API}/auth/sedes`);

            if (resSedes) {
                const sedes = await resSedes.json();

                sel.innerHTML =
                    '<option value="">&#8212; Todas las sedes &#8212;</option>';

                sedes.forEach(s => {
                    sel.insertAdjacentHTML(
                        'beforeend',
                        `<option value="${s.id}">
                            ${s.nombre}
                        </option>`
                    );
                });

                sel.style.display = 'block';
                sel.value = valorActual;
            }
        }
    }

    renderizarDevoluciones(devolucionesCache);
    filtrarDevoluciones();
}

let salidasDisponiblesDevolucion = [];

async function cargarSalidasDisponibles() {

    const buscador =
        document.getElementById('dev-salida-busqueda');

    const resultados =
        document.getElementById('dev-salida-resultados');

    const salidaHidden =
        document.getElementById('dev-salida');

    if (!buscador || !resultados || !salidaHidden) return;

    buscador.value = '';
    salidaHidden.value = '';

    resultados.innerHTML = '';
    resultados.style.display = 'none';

    buscador.placeholder = 'Cargando salidas...';

    const res =
        await apiFetch(
            urlConSede(
                `${API}/devoluciones/salidas-disponibles`
            )
        );

    if (!res) return;

    const salidas = await res.json();

    salidasDisponiblesDevolucion =
        Array.isArray(salidas)
            ? salidas
            : [];

    buscador.placeholder =
        'Escribe nombre clave, destino o N° de salida...';

    if (salidasDisponiblesDevolucion.length === 0) {

        resultados.innerHTML =
            '<div style="padding:12px;font-size:12px;color:#6b8aab">' +
            'No hay salidas disponibles para devolver.' +
            '</div>';

        return;
    }
}

function renderizarDevoluciones(devoluciones) {

    document.getElementById(
        'subtitulo-devoluciones'
    ).textContent =
        `${devoluciones.length} devoluciones registradas`;

    const tbody =
        document.getElementById(
            'tabla-devoluciones'
        );

    tbody.innerHTML = '';

    if (devoluciones.length === 0) {

        tbody.innerHTML = `
            <tr>
                <td colspan="8"
                    style="text-align:center;
                           color:#6b8aab;
                           padding:2rem">
                    Sin devoluciones registradas
                </td>
            </tr>
        `;

        return;
    }

    devoluciones.forEach(d => {

        const fecha =
            d.fecha
                ? new Date(d.fecha).toLocaleDateString(
                    'es-CO',
                    {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric'
                    }
                )
                : '—';

        tbody.insertAdjacentHTML(
            'beforeend',
            `
            <tr>

                <td>
                    <strong>
                        ${d.numero_documento || '—'}
                    </strong>
                </td>

                <td>
                    ${d.salida_numero || '—'}
                </td>

                <td>
                    ${d.salida_numero
                        ? 'Salida de almacén'
                        : '—'}
                </td>

                <td>
                    ${d.motivo || '—'}
                </td>

                <td>
                    ${d.total_items || 0} producto(s)
                </td>

                <td>
                    <span style="
                        font-size:11px;
                        color:#4a6080">
                        ${d.sede_nombre || '—'}
                    </span>
                </td>

                <td>
                    ${fecha}
                </td>

                <td>

                    <div class="acciones">

                        <button
                            class="btn-accion"
                            onclick="verPDFDevolucion(${d.id})">
                            📄 PDF
                        </button>

                        ${
                            usuario.rol === 'admin'
                            ? `
                                <button
                                    class="btn-accion danger"
                                    onclick="anularDevolucion(
                                        ${d.id},
                                        '${String(
                                            d.numero_documento || ''
                                        ).replace(/'/g, "\\'")}'
                                    )">
                                    🗑️ Anular
                                </button>
                            `
                            : ''
                        }

                    </div>

                </td>

            </tr>
            `
        );
    });
}

function filtrarDevoluciones() {

    const input =
        document.getElementById(
            'buscar-devoluciones'
        );

    const texto =
        input?.value
            ?.trim()
            ?.toLowerCase() || '';

    const sedeFiltro =
        document.getElementById(
            'filtro-sede-devoluciones'
        )?.value || '';

    let filtradas =
        devolucionesCache || [];

    if (texto) {

        filtradas =
            filtradas.filter(d =>

                String(
                    d.numero_documento || ''
                )
                .toLowerCase()
                .includes(texto)

                ||

                String(
                    d.salida_numero || ''
                )
                .toLowerCase()
                .includes(texto)

                ||

                String(
                    d.motivo || ''
                )
                .toLowerCase()
                .includes(texto)

                ||

                String(
                    d.sede_nombre || ''
                )
                .toLowerCase()
                .includes(texto)

            );
    }

    if (sedeFiltro) {

        filtradas =
            filtradas.filter(
                d =>
                    String(d.sede_id) ===
                    String(sedeFiltro)
            );
    }

    renderizarDevoluciones(
        filtradas
    );
}

async function guardarDevolucion(event) {

    event.preventDefault();

    const salidaId =
        document.getElementById('dev-salida').value;

    if (!salidaId) {

        alert(
            'Selecciona la salida de la que está regresando la mercancía'
        );

        return;
    }

    const numero =
        document.getElementById('dev-numero').value;

    if (!numero) {

        alert(
            'No se pudo generar el número de documento. Verifica fecha y salida.'
        );

        return;
    }

    // =====================================================
    // DETALLE DE PRODUCTOS
    // =====================================================

    const filas =
        document.querySelectorAll('.dev-item-fila');

    const detalle = [];

    // El motivo de la devolución decide con qué condición
    // regresa el equipo. Por ahora solo distinguimos "Dañado"
    // (pasa a condición DANADO y a mantenimiento) de todo lo
    // demás (regresa en buen estado, sin cambiar su condición).
    const motivoDevolucion =
        document.getElementById('dev-motivo')?.value || '';

    const condicionRetorno =
        motivoDevolucion === 'Dañado'
            ? 'DANADO'
            : 'BUEN_ESTADO';

    filas.forEach(fila => {

        const check =
            fila.querySelector('.dev-check');

        // Solo enviar los productos seleccionados
        if (!check.checked) return;

        const inputCantidad =
            fila.querySelector('.dev-cantidad');

        const productoId =
            parseInt(fila.dataset.productoId);

        const equipoId =
            fila.dataset.equipoId
                ? parseInt(fila.dataset.equipoId)
                : null;

        const cantidad =
            parseInt(inputCantidad.value) || 1;

        // =================================================
        // AGREGAR PRODUCTO
        // =================================================

        detalle.push({

            producto_id: productoId,

            // IMPORTANTE:
            // Para productos serializados se envía
            // automáticamente el equipo_id original
            // de la salida.
            equipo_id: equipoId,

            cantidad: cantidad,

            condicion_retorno:
                condicionRetorno,

            observaciones: ''

        });

    });


    // =====================================================
    // VALIDAR DETALLE
    // =====================================================

    if (detalle.length === 0) {

        alert(
            'Marca al menos un producto que esté regresando'
        );

        return;
    }


    // =====================================================
    // DATOS DE LA DEVOLUCIÓN
    // =====================================================

    const datos = {

        numero_documento:
            numero,

        salida_id:
            parseInt(salidaId),

        motivo:
            document.getElementById(
                'dev-motivo'
            ).value,

        observaciones:
            document.getElementById(
                'dev-observaciones'
            ).value,

        sede_id:

            parseInt(
                document.getElementById(
                    'dev-sede'
                ).value
            ) || sedeActual,

        detalle:
            detalle

    };


    // =====================================================
    // ENVIAR AL BACKEND
    // =====================================================

    const res = await apiFetch(

        `${API}/devoluciones/`,

        {

            method: 'POST',

            body:
                JSON.stringify(datos)

        }

    );


    if (!res) return;


    const resultado =
        await res.json();


    // =====================================================
    // RESULTADO
    // =====================================================

    if (res.ok) {

        cerrarModal(
            'modal-devolucion'
        );

        limpiarFormDevolucion();

        cargarDevoluciones();

        cargarProductos();

    } else {

        alert(
            'Error: ' +
            (resultado.error ||
                'No se pudo registrar la devolución')
        );

    }

}

function verPDFDevolucion(id) {
    window.open(`${API}/pdf/devolucion/${id}?token=${token}`, '_blank');
}

async function anularDevolucion(id, numero) {

    const confirmar =
        await mostrarConfirm(
            `¿Anular la devolución "${numero}"?`
        );

    if (!confirmar) return;

    const motivo =
        prompt(
            'Escribe el motivo de la anulación:'
        );

    if (!motivo || !motivo.trim()) {
        mostrarNotificacionSalida(
            'Debes indicar el motivo de la anulación.',
            'error'
        );
        return;
    }

    const res =
        await apiFetch(
            `${API}/devoluciones/${id}/anular`,
            {
                method: 'PUT',
                body: JSON.stringify({
                    motivo_anulacion:
                        motivo.trim()
                })
            }
        );

    if (!res) return;

    const resultado =
        await res.json();

    if (res.ok) {

        mostrarNotificacionSalida(
            'Devolución anulada correctamente.',
            'success'
        );

        await cargarDevoluciones();
        await cargarProductos();

    } else {

        mostrarNotificacionSalida(
            resultado.error ||
            'No se pudo anular la devolución.',
            'error'
        );
    }
}

function limpiarFormDevolucion() {
    document.getElementById('dev-numero').value        = '';
    document.getElementById('dev-fecha').value         = '';
    document.getElementById('dev-salida').value        = '';
    document.getElementById('dev-origen').value        = '';
    document.getElementById('dev-cliente').value       = '';
    document.getElementById('dev-motivo').value        = 'No se uso';
    document.getElementById('dev-observaciones').value = '';
    document.getElementById('dev-sede').value = '';
    document.getElementById('dev-items').innerHTML     =
        '<p style="font-size:12px;color:#6b8aab">Selecciona primero una salida arriba.</p>';
}

// ══ MODAL DE CONFIRMACION ════════════════════════════════════

let _resolverConfirm = null;

function mostrarConfirm(mensaje, titulo = '¿Eliminar?', icono = '🗑️', textoBtn = 'Eliminar') {
    document.getElementById('confirm-mensaje').textContent = mensaje;
    document.getElementById('confirm-titulo').textContent  = titulo;
    document.getElementById('confirm-icono').textContent   = icono;

    const boton = document.getElementById('confirm-btn-ok');

    boton.textContent = textoBtn;

    // Cambiar color según la acción
    if (textoBtn === 'Confirmar') {
        boton.style.background = '#27ae60';
        boton.style.color = '#fff';
    } else {
        boton.style.background = '';
        boton.style.color = '';
    }

    document.getElementById('modal-confirm').classList.add('visible');

    return new Promise(resolve => {
        _resolverConfirm = resolve;
    });
}

function resolverConfirm(valor) {
    document.getElementById('modal-confirm').classList.remove('visible');
    if (_resolverConfirm) _resolverConfirm(valor);
    _resolverConfirm = null;
}

// ══ INICIO ══════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
    // IMPORTANTE: hay que esperar a que el selector de sede termine
    // de inicializarse (y de resetear sedeActual) ANTES de cargar
    // productos. Si no, cargarProductos() se dispara con el
    // sedeActual viejo (guardado en el navegador de una sesión
    // anterior) mientras inicializarSelectorSede() todavía está
    // resolviendo su petición al backend, y la tabla queda "pegada"
    // con el filtro de sede antiguo aunque el selector ya muestre
    // "Todas las sedes".
    await inicializarSelectorSede();

    if (usuario.rol === 'porteria') {
        // Portería no necesita productos ni catálogos —
        // solo entra directo a ver las salidas de su sede.
        document.body.classList.add('rol-porteria');
        mostrarSeccion('salidas', document.getElementById('nav-salidas'));
        iniciarPollingPorteria();
    } else {
        await cargarProductos();
        cargarCatalogos();
    }

    if (usuario.rol === 'consulta') {
        document.body.classList.add('rol-consulta');
    }

    // Los filtros de "— Todas las sedes —" son solo para admin y
    // consulta. Para almacenistas (rol "sede") y cualquier otro
    // rol se ocultan de forma explícita aquí, sin depender de que
    // el CSS ya los tenga ocultos por defecto.
    if (usuario.rol !== 'admin' && usuario.rol !== 'consulta') {
        [
            'selector-sede',
            'filtro-sede-productos',
            'filtro-sede-entradas',
            'filtro-sede-salidas',
            'filtro-sede-devoluciones',
            'filtro-sede-consolidado',
            'filtro-sede-traslados',
        ].forEach(id => {
            const el = document.getElementById(id);
            // Se usa setProperty(..., 'important') porque hay una
            // regla en el CSS con !important que, si no, le gana
            // a un simple el.style.display = 'none' y el cuadro
            // se seguiría viendo aunque aquí digamos que se oculte.
            if (el) el.style.setProperty('display', 'none', 'important');
        });
    }

    // Elementos marcados con la clase "admin-only" (el menú de
    // "Usuarios", "+ Nuevo modelo", "+ Nueva marca" y
    // "+ Nuevo usuario") son solo para admin.
    if (usuario.rol !== 'admin') {
        document.querySelectorAll('.admin-only').forEach(el => {
            el.style.setProperty('display', 'none', 'important');
        });
    }

    // Elementos marcados con "no-consulta" ("+ Nuevo producto",
    // "+ Nueva entrada", "+ Nueva salida", "+ Nuevo traslado") sí
    // los puede usar el almacenista (rol "sede"), pero no un
    // usuario de consulta ni uno de portería, que son de solo
    // lectura.
    if (usuario.rol === 'consulta' || usuario.rol === 'porteria') {
        document.querySelectorAll('.no-consulta').forEach(el => {
            el.style.setProperty('display', 'none', 'important');
        });
    }

    // Portería solo ve la sección de Salidas en el menú lateral.
    if (usuario.rol === 'porteria') {
        document.querySelectorAll('.nav-btn').forEach(btn => {
            if (btn.id !== 'nav-salidas') {
                btn.style.setProperty('display', 'none', 'important');
            }
        });
    }

    const nom = usuario.nombre || 'Usuario';
    const rolTexto = usuario.rol === 'admin'
    ? 'Administrador'
    : usuario.rol === 'sede'
        ? 'Almacenista'
        : usuario.rol === 'porteria'
            ? 'Portería'
            : 'Consulta';

    document.getElementById('nombre-usuario').textContent = nom;
    document.getElementById('rol-usuario').textContent    = rolTexto;
    document.getElementById('sede-usuario').textContent   = usuario.sede_nombre || usuario.ciudad || '';
    document.getElementById('avatar-usuario').textContent =
        nom.split(' ').map(p => p[0]).join('').substring(0, 2).toUpperCase();

    const entSede = document.getElementById('ent-sede');
    if (entSede) {
        entSede.addEventListener('change', () => {
            document.getElementById('ent-items').innerHTML = '';
            productosCache = [];
        });
    }

    const salSede = document.getElementById('sal-sede');
    if (salSede) {
        salSede.addEventListener('change', () => {
            document.getElementById('sal-items').innerHTML = '';
            productosCacheSalida = [];
        });
    }

    const devSede = document.getElementById('dev-sede');
    if (devSede) {
        devSede.addEventListener('change', () => {
            document.getElementById('dev-salida').innerHTML = '<option value="">— Selecciona la salida —</option>';
            document.getElementById('dev-items').innerHTML = '<p style="font-size:12px;color:#6b8aab">Selecciona primero una salida arriba.</p>';
            cargarSelectorSalidas();
        });
    }
});

// ══ USUARIOS ════════════════════════════════════════════════
// Agregar estas funciones al final de app.js

async function cargarUsuarios() {
    const res      = await apiFetch(`${API}/auth/usuarios`);
    if (!res) return;
    const usuarios = await res.json();

    document.getElementById('subtitulo-usuarios').textContent =
        `${usuarios.length} usuarios registrados`;

    const tbody = document.getElementById('tabla-usuarios');
    tbody.innerHTML = '';

    if (usuarios.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#6b8aab;padding:2rem">Sin usuarios registrados</td></tr>';
        return;
    }

    usuarios.forEach(u => {
        const rolTexto  = u.rol === 'admin' ? 'Administrador' : u.rol === 'sede' ? 'Almacenista' : u.rol === 'porteria' ? 'Portería' : 'Consulta';
        const rolColor  = u.rol === 'admin' ? '#1a6fc4' : u.rol === 'sede' ? '#1a7a4a' : u.rol === 'porteria' ? '#a5680c' : '#6b8aab';
        const rolBg     = u.rol === 'admin' ? '#e8f0fb' : u.rol === 'sede' ? '#e6f4ec' : u.rol === 'porteria' ? '#fbf1e0' : '#f0f4f8';
        const estadoBadge = u.activo
            ? '<span class="badge badge-ok">Activo</span>'
            : '<span class="badge badge-agotado">Inactivo</span>';

        tbody.insertAdjacentHTML('beforeend', `
            <tr>
                <td><strong>${u.nombre}</strong></td>
                <td style="color:#6b8aab;font-size:12px">${u.email || u.correo || '—'}</td>
                <td>
                    <span style="background:${rolBg};color:${rolColor};padding:3px 10px;border-radius:20px;font-size:11px;font-weight:500">
                        ${rolTexto}
                    </span>
                </td>
                <td>${u.sede_nombre || '—'}</td>
                <td>${estadoBadge}</td>
                <td>
                    <div class="acciones">
                        <button class="btn-accion" onclick="editarUsuario(${u.id})">✏️ Editar</button>
                        <button class="btn-accion danger" onclick="toggleUsuario(${u.id}, ${u.activo}, '${u.nombre}')">
                            ${u.activo ? '🔒 Desactivar' : '🔓 Activar'}
                        </button>
                    </div>
                </td>
            </tr>
        `);
    });
}

async function abrirModalUsuario() {
    // Cargamos las sedes en el select antes de abrir
    const res = await apiFetch(`${API}/auth/sedes`);
    if (!res) return;
    const sedes = await res.json();

    const select = document.getElementById('usr-sede');
    select.innerHTML = '<option value="">— Sin sede —</option>';
    sedes.forEach(s => {
        select.insertAdjacentHTML('beforeend',
            `<option value="${s.id}">${s.nombre}</option>`
        );
    });
    abrirModal('modal-usuario');
}

async function editarUsuario(id) {
    const res      = await apiFetch(`${API}/auth/usuarios`);
    if (!res) return;
    const usuarios = await res.json();
    const u        = usuarios.find(x => x.id === id);
    if (!u) return;

    // Cargamos sedes
    const resSedes = await apiFetch(`${API}/auth/sedes`);
    if (!resSedes) return;
    const sedes = await resSedes.json();
    const selectSede = document.getElementById('usr-sede');
    selectSede.innerHTML = '<option value="">— Sin sede —</option>';
    sedes.forEach(s => {
        selectSede.insertAdjacentHTML('beforeend',
            `<option value="${s.id}" ${s.id === u.sede_id ? 'selected' : ''}>${s.nombre}</option>`
        );
    });

    document.getElementById('modal-usuario-titulo').textContent = 'Editar usuario';
    document.getElementById('usr-id').value     = u.id;
    document.getElementById('usr-nombre').value = u.nombre;
    document.getElementById('usr-correo').value = u.email;
    document.getElementById('usr-rol').value    = u.rol;

    // En edicion mostramos campo de nueva contrasena opcional
    document.getElementById('campo-password').style.display       = 'none';
    document.getElementById('campo-password-editar').style.display = 'block';
    document.getElementById('usr-password-nuevo').value           = '';

    abrirModal('modal-usuario');
}

async function guardarUsuario(event) {
    event.preventDefault();

    const id      = document.getElementById('usr-id').value;
    const nombre  = document.getElementById('usr-nombre').value;
    const correo  = document.getElementById('usr-correo').value;
    const rol     = document.getElementById('usr-rol').value;
    const sede_id = document.getElementById('usr-sede').value || null;

    if (id) {
        // Editar usuario existente
        const datos = { nombre, email: correo, rol, sede_id };
        const nuevaPassword = document.getElementById('usr-password-nuevo').value;
        if (nuevaPassword) {
            if (nuevaPassword.length < 6) {
                alert('La contrasena debe tener al menos 6 caracteres');
                return;
            }
            datos.password = nuevaPassword;
        }

        const res = await apiFetch(`${API}/auth/usuarios/${id}`, {
            method: 'PUT',
            body: JSON.stringify(datos)
        });
        if (!res) return;
        const resultado = await res.json();
        if (!res.ok) { alert('Error: ' + resultado.error); return; }

    } else {
        // Crear usuario nuevo
        const password = document.getElementById('usr-password').value;
        if (!password || password.length < 6) {
            alert('La contrasena debe tener al menos 6 caracteres');
            return;
        }

        const res = await apiFetch(`${API}/auth/usuarios`, {
            method: 'POST',
            body: JSON.stringify({ nombre, email: correo, password, rol, sede_id })
        });
        if (!res) return;
        const resultado = await res.json();
        if (!res.ok) { alert('Error: ' + resultado.error); return; }
    }

    cerrarModal('modal-usuario');
    cargarUsuarios();
}

async function toggleUsuario(id, activo, nombre) {
    const accion = activo ? 'desactivar' : 'activar';
    if (!await mostrarConfirm(`¿${accion.charAt(0).toUpperCase() + accion.slice(1)} al usuario "${nombre}"?`, '¿Confirmar accion?', '👤', accion.charAt(0).toUpperCase() + accion.slice(1))) return;

    const res = await apiFetch(`${API}/auth/usuarios/${id}/toggle`, {
        method: 'PUT'
    });
    if (!res) return;
    cargarUsuarios();
}

function limpiarFormUsuario() {
    document.getElementById('usr-id').value            = '';
    document.getElementById('usr-nombre').value        = '';
    document.getElementById('usr-correo').value        = '';
    document.getElementById('usr-rol').value           = 'sede';
    document.getElementById('usr-password').value      = '';
    document.getElementById('usr-password-nuevo').value = '';
    document.getElementById('campo-password').style.display        = 'block';
    document.getElementById('campo-password-editar').style.display = 'none';
    document.getElementById('modal-usuario-titulo').textContent    = 'Nuevo usuario';
}

// ══ CONSOLIDADO POR PUNTO ════════════════════════════════════

let puntosCache = [];

async function cargarPuntos() {
    // Carga sedes en filtro si es admin o consulta
    if (usuario.rol === 'admin' || usuario.rol === 'consulta') {
        const sel = document.getElementById('filtro-sede-consolidado');
        const valorActual = sel.value;
        const resSedes = await apiFetch(`${API}/auth/sedes`);
        if (resSedes) {
            const sedes = await resSedes.json();
            sel.innerHTML = '<option value="">&#8212; Todas las sedes &#8212;</option>';
            sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                `<option value="${s.id}">${s.nombre}</option>`
            ));
            sel.style.display = 'block';
            sel.value = valorActual;
        }
    }

    const sedeFiltro = document.getElementById('filtro-sede-consolidado')?.value;
    const url = sedeFiltro
        ? `${API}/consolidado/puntos?sede_id=${sedeFiltro}`
        : `${API}/consolidado/puntos`;

    const res = await apiFetch(url);
    if (!res) return;
    const puntos = await res.json();

    puntosCache = puntos;

    document.getElementById('subtitulo-consolidado').textContent =
        `${puntos.length} puntos con movimientos`;

    // Vuelve a pintar el selector aplicando el texto de
    // búsqueda actual (si había algo escrito antes de recargar).
    filtrarPuntos();
}

function pintarSelectorPuntos(lista) {
    const select = document.getElementById('selector-punto');
    const valorActual = select.value;

    select.innerHTML = '<option value="">— Selecciona un punto —</option>';

    lista.forEach(p => {
        const sede = p.sede_nombre ? ` (${p.sede_nombre})` : '';
        select.insertAdjacentHTML('beforeend',
            `<option value="${p.destino}">${p.destino}${sede} — ${p.total_salidas} salida(s)</option>`
        );
    });

    // Si el punto que estaba seleccionado ya no está en la
    // lista filtrada, se pierde la selección y se limpia el
    // historial mostrado.
    const sigueExistiendo = lista.some(p => p.destino === valorActual);

    if (valorActual && sigueExistiendo) {
        select.value = valorActual;
    } else if (valorActual) {
        select.value = '';
        document.getElementById('consolidado-contenido').innerHTML =
            '<p style="color:#6b8aab;font-size:13px;padding:2rem 0">Selecciona un punto arriba para ver su historial.</p>';
    }
}

async function cargarHistorialPunto() {
    const destino = document.getElementById('selector-punto').value;
    const contenedor = document.getElementById('consolidado-contenido');

    if (!destino) {
        contenedor.innerHTML = '<p style="color:#6b8aab;font-size:13px;padding:2rem 0">Selecciona un punto arriba para ver su historial.</p>';
        return;
    }

    const sedeFiltro = document.getElementById('filtro-sede-consolidado')?.value;

    const url = sedeFiltro
        ? `${API}/consolidado/punto?destino=${encodeURIComponent(destino)}&sede_id=${sedeFiltro}`
        : `${API}/consolidado/punto?destino=${encodeURIComponent(destino)}`;

    const res = await apiFetch(url);

    if (!res) return;

    const data = await res.json();

    let html = '';


    // ========================================================
    // RESUMEN NETO
    // ========================================================

    if (data.resumen && data.resumen.length > 0) {

        html += `
            <h3 style="font-size:13px;color:#0d2137;margin:1rem 0 0.5rem">
                📦 Equipos en "${destino}"
            </h3>

            <div style="background:white;border:0.5px solid #dce6f0;border-radius:10px;padding:12px 16px;margin-bottom:16px">

                <table style="width:100%;border-collapse:collapse">

                    <thead>
                        <tr>

                            <th style="font-size:10px;color:#6b8aab;text-align:left;padding:4px 8px;background:#f7f9fc">
                                Producto
                            </th>

                            <th style="font-size:10px;color:#6b8aab;text-align:left;padding:4px 8px;background:#f7f9fc">
                                Modelo
                            </th>

                            <th style="font-size:10px;color:#6b8aab;text-align:left;padding:4px 8px;background:#f7f9fc">
                                Serial
                            </th>

                            <th style="font-size:10px;color:#6b8aab;text-align:right;padding:4px 8px;background:#f7f9fc">
                                Salió
                            </th>

                            <th style="font-size:10px;color:#c0392b;text-align:right;padding:4px 8px;background:#f7f9fc">
                                Devuelto
                            </th>

                            <th style="font-size:10px;color:#1a7a4a;text-align:right;padding:4px 8px;background:#f7f9fc">
                                En obra
                            </th>

                        </tr>
                    </thead>

                    <tbody>

                        ${data.resumen.map(r => `

                            <tr>

                                <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8">
                                    ${r.nombre || '—'}
                                </td>

                                <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;color:#6b8aab">
                                    ${r.modelo || '—'}
                                </td>

                                <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;color:#6b8aab">
                                    ${r.serial || '—'}
                                </td>

                                <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;text-align:right">
                                    ${r.salidas || 0} ${r.unidad || 'UND'}
                                </td>

                                <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;text-align:right;color:#c0392b">
                                    ${r.devuelto || 0} ${r.unidad || 'UND'}
                                </td>

                                <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;text-align:right;font-weight:600;color:#1a7a4a">
                                    ${r.neto || 0} ${r.unidad || 'UND'}
                                </td>

                            </tr>

                        `).join('')}

                    </tbody>

                </table>

            </div>
        `;
    }


    // ========================================================
    // DEVOLUCIONES
    // ========================================================

    html += `
        <h3 style="font-size:13px;color:#0d2137;margin:1.5rem 0 0.5rem">
            🔄 Devoluciones desde "${destino}"
        </h3>
    `;


    if (!data.devoluciones || data.devoluciones.length === 0) {

        html += `
            <p style="font-size:12px;color:#6b8aab">
                Sin devoluciones registradas.
            </p>
        `;

    } else {

        data.devoluciones.forEach(d => {

            const fecha = d.fecha
                ? new Date(d.fecha).toLocaleDateString(
                    'es-CO',
                    {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric'
                    }
                )
                : '—';


            html += `

                <div style="background:white;border:0.5px solid #dce6f0;border-radius:10px;padding:12px 16px;margin-bottom:10px">

                    <div style="display:flex;justify-content:space-between;margin-bottom:8px">

                        <strong style="font-size:13px;color:#0d2137">
                            ${d.numero_documento || '—'}
                        </strong>

                        <span style="font-size:11px;color:#6b8aab">
                            ${fecha}${d.sede_nombre ? ' · ' + d.sede_nombre : ''}
                        </span>

                    </div>


                    <div style="font-size:11px;color:#6b8aab;margin-bottom:8px">

                        Motivo: ${d.motivo || '—'}
                        ·
                        Salida origen: ${d.salida_numero || '—'}

                    </div>


                    <table style="width:100%;border-collapse:collapse">

                        <thead>

                            <tr>

                                <th style="font-size:10px;color:#6b8aab;text-align:left;padding:4px 8px;background:#f7f9fc">
                                    Producto
                                </th>

                                <th style="font-size:10px;color:#6b8aab;text-align:left;padding:4px 8px;background:#f7f9fc">
                                    Modelo
                                </th>

                                <th style="font-size:10px;color:#6b8aab;text-align:left;padding:4px 8px;background:#f7f9fc">
                                    Marca
                                </th>

                                <th style="font-size:10px;color:#6b8aab;text-align:left;padding:4px 8px;background:#f7f9fc">
                                    Serial
                                </th>

                                <th style="font-size:10px;color:#6b8aab;text-align:right;padding:4px 8px;background:#f7f9fc">
                                    Cant.
                                </th>

                            </tr>

                        </thead>


                        <tbody>

                            ${(d.detalle || []).map(item => `

                                <tr>

                                    <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8">
                                        ${item.producto_nombre || item.nombre || '—'}
                                    </td>

                                    <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;color:#6b8aab">
                                        ${item.modelo_nombre || item.modelo || '—'}
                                    </td>

                                    <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;color:#6b8aab">
                                        ${item.marca_nombre || item.marca || '—'}
                                    </td>

                                    <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;color:#6b8aab">
                                        ${item.serial || '—'}
                                    </td>

                                    <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;text-align:right">
                                        ${item.cantidad || 0} ${item.unidad || 'UND'}
                                    </td>

                                </tr>

                            `).join('')}

                        </tbody>

                    </table>

                </div>

            `;
        });
    }


    // ========================================================
    // BOTÓN PDF
    // ========================================================

    html = `
        <div style="margin-bottom:1rem">

            <button
                onclick="descargarPDFConsolidado('${destino}')"
                class="btn-primario">
                📄 Exportar PDF
            </button>

        </div>
    ` + html;


    contenedor.innerHTML = html;
}

async function descargarPDFConsolidado(destino) {
    const sedeFiltro = document.getElementById('filtro-sede-consolidado')?.value;
    const url = sedeFiltro
        ? `${API}/pdf/consolidado?destino=${encodeURIComponent(destino)}&sede_id=${sedeFiltro}`
        : `${API}/pdf/consolidado?destino=${encodeURIComponent(destino)}`;

    const res = await apiFetch(url);
    if (!res) return;

    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    window.open(blobUrl, '_blank');
}

// CREAR TRASLADOS ENTRE SEDES

let productosCacheTraslado = [];

async function cargarSedesTraslado() {
    const res = await apiFetch(`${API}/auth/sedes`);
    if (!res) return;

    const sedes = await res.json();

    const origen = document.getElementById('tras-sede-origen');
    const destino = document.getElementById('tras-sede-destino');

    if (!origen || !destino) return;

    origen.innerHTML = '<option value="">— Selecciona origen —</option>';
    destino.innerHTML = '<option value="">— Selecciona destino —</option>';

    // ADMIN
    if (usuario.rol === 'admin') {

        sedes.forEach(s => {

            origen.insertAdjacentHTML(
                'beforeend',
                `<option value="${s.id}">
                    ${sanitizar(s.nombre)} — ${sanitizar(s.ciudad)}
                </option>`
            );

            destino.insertAdjacentHTML(
                'beforeend',
                `<option value="${s.id}">
                    ${sanitizar(s.nombre)} — ${sanitizar(s.ciudad)}
                </option>`
            );

        });

    } else {

        // ALMACENISTA: origen = su propia sede
        const miSede = sedes.find(
            s => Number(s.id) === Number(usuario.sede_id)
        );

        if (miSede) {

            origen.innerHTML = `
                <option value="${miSede.id}" selected>
                    ${sanitizar(miSede.nombre)} — ${sanitizar(miSede.ciudad)}
                </option>
            `;

            // El almacenista puede enviar a cualquier otra sede
            sedes.forEach(s => {

                if (Number(s.id) !== Number(usuario.sede_id)) {

                    destino.insertAdjacentHTML(
                        'beforeend',
                        `<option value="${s.id}">
                            ${sanitizar(s.nombre)} — ${sanitizar(s.ciudad)}
                        </option>`
                    );

                }

            });

            // Cargar productos automáticamente de su sede
            cargarProductosTraslado();
        }
    }
}


async function cargarProductosTraslado() {

    const sedeOrigen = parseInt(
        document.getElementById('tras-sede-origen').value
    );

    const contenedor = document.getElementById('tras-items');

    if (!sedeOrigen) {
        productosCacheTraslado = [];

        contenedor.innerHTML = `
            <p style="font-size:12px;color:#6b8aab">
                Selecciona primero la sede de origen.
            </p>
        `;

        return;
    }

    const res = await apiFetch(
        `${API}/productos/?sede_id=${sedeOrigen}`
    );

    if (!res) return;

    productosCacheTraslado = await res.json();

    contenedor.innerHTML = '';

    if (productosCacheTraslado.length === 0) {
        contenedor.innerHTML = `
            <p style="font-size:12px;color:#6b8aab">
                No hay productos disponibles en esta sede.
            </p>
        `;
        return;
    }

    agregarItemTraslado();
}

async function agregarItemTraslado() {

    const contenedor =
        document.getElementById('tras-items');

    if (!productosCacheTraslado.length) {
        alert('Primero selecciona una sede de origen.');
        return;
    }

    const opciones =
        productosCacheTraslado
            .map(p => `
                <option
                    value="${p.id}"
                    data-stock="${p.stock || 0}"
                    data-unidad="${p.unidad || 'UND'}"
                    data-serializado="${p.requiere_serial ? '1' : '0'}">
                    [${p.codigo || '—'}] ${sanitizar(p.nombre)}
                    (disp: ${p.stock || 0})
                </option>
            `)
            .join('');

    const unidadesDisponibles = [
        'UND',
        'MTS',
        'KG',
        'CAJA',
        'ROLLO',
        'LITRO'
    ];

    const opcionesUnidad =
        unidadesDisponibles
            .map(u => `
                <option value="${u}">
                    ${u}
                </option>
            `)
            .join('');

    const item =
        document.createElement('div');

    item.className =
        'item-traslado';

    item.style.cssText = `
        border:1px solid #d5e2f0;
        border-radius:8px;
        padding:8px;
        margin-bottom:8px;
        background:#f8fbff;
    `;

    item.innerHTML = `
        <div style="
            display:grid;
            grid-template-columns:1.6fr 70px 70px;
            gap:6px;
            align-items:start;
        ">

            <div style="position:relative;">

                <input
                    type="text"
                    class="buscador-producto"
                    placeholder="Escribe código o nombre..."
                    autocomplete="off"
                    style="
                        border:0.5px solid #c8d8ea;
                        border-radius:8px;
                        padding:6px 8px;
                        font-size:12px;
                        color:#0d2137;
                        width:100%;
                        height:32px;
                        box-sizing:border-box;
                    ">

                <div
                    class="resultados-producto"
                    style="
                        display:none;
                        position:absolute;
                        left:0;
                        right:0;
                        top:100%;
                        background:white;
                        border:0.5px solid #c8d8ea;
                        border-radius:8px;
                        margin-top:4px;
                        max-height:220px;
                        overflow-y:auto;
                        z-index:50;
                        box-shadow:0 4px 15px rgba(0,0,0,.12);
                    ">
                </div>

                <select
                    class="tras-producto"
                    style="display:none">
                    ${opciones}
                </select>

            </div>

            <select
                class="tras-unidad"
                style="
                    border:0.5px solid #c8d8ea;
                    border-radius:8px;
                    padding:6px 4px;
                    font-size:12px;
                    color:#0d2137;
                    width:100%;
                    height:32px;
                ">
                ${opcionesUnidad}
            </select>

            <input
                type="number"
                class="tras-cantidad"
                min="1"
                value="1"
                style="
                    border:0.5px solid #c8d8ea;
                    border-radius:8px;
                    padding:6px 8px;
                    font-size:12px;
                    text-align:center;
                    width:100%;
                    height:32px;
                    box-sizing:border-box;
                ">
        </div>

        <div
            class="tras-equipos-container"
            style="
                display:none;
                margin-top:8px;
                border-top:1px solid #dce7f2;
                padding-top:8px;
            ">

            <div style="
                font-weight:600;
                color:#315b87;
                font-size:13px;
                margin-bottom:7px;
            ">
                📦 Equipos serializados
            </div>

            <div class="tras-equipos-lista"></div>
        </div>

        <div style="
            margin-top:8px;
            display:flex;
            justify-content:flex-start;
        ">
            <button
                type="button"
                class="btn-quitar-traslado"
                style="
                    background:#fdecea;
                    border:none;
                    border-radius:6px;
                    color:#c0392b;
                    cursor:pointer;
                    font-size:12px;
                    padding:6px 10px;
                ">
                ✕ Quitar producto
            </button>
        </div>
    `;

    contenedor.appendChild(item);

    const producto =
        item.querySelector('.tras-producto');

    const unidad =
        item.querySelector('.tras-unidad');

    const cantidad =
        item.querySelector('.tras-cantidad');

    const contenedorEquipos =
        item.querySelector(
            '.tras-equipos-container'
        );

    const listaEquipos =
        item.querySelector(
            '.tras-equipos-lista'
        );

    let equiposDisponibles = [];

    inicializarBuscadorProducto(
        item,
        producto,
        productosCacheTraslado
    );

    // ============================================================
    // QUITAR PRODUCTO
    // ============================================================

    item.querySelector(
        '.btn-quitar-traslado'
    ).addEventListener(
        'click',
        () => item.remove()
    );


    // ============================================================
    // UNIDAD
    // ============================================================

    function actualizarUnidad() {

        const opcion =
            producto.options[
                producto.selectedIndex
            ];

        unidad.value =
            opcion?.dataset?.unidad || 'UND';
    }


    // ============================================================
    // BUSCAR EQUIPO POR SERIAL
    // ============================================================

    function buscarEquipoPorSerial(serial) {

        const serialBuscado =
            String(serial || '')
                .trim()
                .toLowerCase();

        if (!serialBuscado) {
            return null;
        }

        return equiposDisponibles.find(
            equipo =>
                String(equipo.serial || '')
                    .trim()
                    .toLowerCase() ===
                serialBuscado
        );
    }


    // ============================================================
    // VERIFICAR SERIAL REPETIDO
    // ============================================================

    function serialYaSeleccionado(
        serial,
        filaActual
    ) {

        const serialBuscado =
            String(serial || '')
                .trim()
                .toLowerCase();

        if (!serialBuscado) {
            return false;
        }

        const inputs =
            listaEquipos.querySelectorAll(
                '.input-serial-traslado'
            );

        let cantidadEncontrada = 0;

        inputs.forEach(input => {

            if (input === filaActual) {
                return;
            }

            const valor =
                String(input.value || '')
                    .trim()
                    .toLowerCase();

            if (
                valor ===
                serialBuscado
            ) {
                cantidadEncontrada++;
            }
        });

        return cantidadEncontrada > 0;
    }


    // ============================================================
    // ACTUALIZAR DATOS DE UNA FILA
    // ============================================================

    function actualizarEquipoFila(fila) {

        const inputSerial =
            fila.querySelector(
                '.input-serial-traslado'
            );

        const inputEquipoId =
            fila.querySelector(
                '.select-equipo-traslado'
            );

        const inputMarca =
            fila.querySelector(
                '.input-marca-traslado'
            );

        const inputModelo =
            fila.querySelector(
                '.input-modelo-traslado'
            );

        const serial =
            inputSerial.value.trim();

        if (!serial) {

            inputEquipoId.value = '';
            inputMarca.value = '';
            inputModelo.value = '';

            inputSerial.style.borderColor =
                '#c8d8ea';

            return;
        }

        const equipo =
            buscarEquipoPorSerial(serial);

        if (!equipo) {

            inputEquipoId.value = '';
            inputMarca.value = '';
            inputModelo.value = '';

            inputSerial.style.borderColor =
                '#e74c3c';

            return;
        }

        if (
            serialYaSeleccionado(
                serial,
                inputSerial
            )
        ) {

            mostrarNotificacionSalida(
                `El serial "${equipo.serial}" ya fue seleccionado.`,
                'error'
            );

            inputSerial.value = '';
            inputEquipoId.value = '';
            inputMarca.value = '';
            inputModelo.value = '';

            inputSerial.style.borderColor =
                '#e74c3c';

            inputSerial.focus();

            return;
        }

        inputEquipoId.value =
            equipo.id;

        inputMarca.value =
            equipo.marca_nombre || '';

        inputModelo.value =
            equipo.modelo_nombre || '';

        inputSerial.style.borderColor =
            '#27ae60';
    }


    // ============================================================
    // CREAR FILA DE EQUIPO
    // ============================================================

    function crearFilaEquipo(
        indice,
        equipoId = null
    ) {

        const fila =
            document.createElement('div');

        fila.className =
            'fila-equipo-traslado';

        fila.style.cssText = `
            display:grid;
            grid-template-columns:45px 1.2fr 1fr 1fr;
            gap:6px;
            align-items:start;
            margin-bottom:6px;
        `;

        const idDatalist =
            `lista-seriales-traslado-${Date.now()}-${indice}-${Math.random()
                .toString(36)
                .slice(2, 7)}`;

        const opcionesSeriales =
            equiposDisponibles
                .filter(
                    equipo =>
                        equipo.estado ===
                        'DISPONIBLE'
                )
                .map(
                    equipo => `
                        <option
                            value="${equipo.serial || ''}">
                            ${equipo.serial || 'SIN SERIAL'}
                        </option>
                    `
                )
                .join('');

        fila.innerHTML = `
            <div style="
                display:flex;
                align-items:center;
                justify-content:center;
                height:32px;
                background:#e8f1fa;
                border-radius:6px;
                color:#315b87;
                font-size:12px;
                font-weight:600;
            ">
                #${indice}
            </div>

            <!-- ID INTERNO -->
            <input
                type="hidden"
                class="select-equipo-traslado"
                value=""
            >

            <!-- SERIAL -->
            <div>
                <input
                    type="text"
                    class="input-serial-traslado"
                    list="${idDatalist}"
                    placeholder="Escribe o escanea el serial"
                    autocomplete="off"
                    style="
                        width:100%;
                        height:32px;
                        box-sizing:border-box;
                        border:1px solid #c8d8ea;
                        border-radius:8px;
                        padding:6px 8px;
                        font-size:12px;
                        color:#0d2137;
                        background:white;
                    "
                >

                <datalist id="${idDatalist}">
                    ${opcionesSeriales}
                </datalist>
            </div>

            <!-- MARCA -->
            <input
                type="text"
                class="input-marca-traslado"
                placeholder="Marca"
                readonly
                style="
                    width:100%;
                    height:32px;
                    box-sizing:border-box;
                    border:1px solid #c8d8ea;
                    border-radius:8px;
                    padding:6px 8px;
                    font-size:12px;
                    color:#0d2137;
                    background:#f1f5f9;
                "
            >

            <!-- MODELO -->
            <input
                type="text"
                class="input-modelo-traslado"
                placeholder="Modelo"
                readonly
                style="
                    width:100%;
                    height:32px;
                    box-sizing:border-box;
                    border:1px solid #c8d8ea;
                    border-radius:8px;
                    padding:6px 8px;
                    font-size:12px;
                    color:#0d2137;
                    background:#f1f5f9;
                "
            >
        `;

        listaEquipos.appendChild(fila);

        const inputSerial =
            fila.querySelector(
                '.input-serial-traslado'
            );

        // --------------------------------------------------------
        // ESCRIBIR / ESCANEAR
        // --------------------------------------------------------

        inputSerial.addEventListener(
            'input',
            () => {
                actualizarEquipoFila(fila);
            }
        );

        inputSerial.addEventListener(
            'change',
            () => {
                actualizarEquipoFila(fila);
            }
        );

        inputSerial.addEventListener(
            'blur',
            () => {

                if (
                    inputSerial.value.trim()
                ) {
                    actualizarEquipoFila(
                        fila
                    );
                }
            }
        );

        // --------------------------------------------------------
        // RESTAURAR EQUIPO
        // --------------------------------------------------------

        if (equipoId) {

            const equipo =
                equiposDisponibles.find(
                    e =>
                        Number(e.id) ===
                        Number(equipoId)
                );

            if (equipo) {

                inputSerial.value =
                    equipo.serial || '';

                const inputEquipoId =
                    fila.querySelector(
                        '.select-equipo-traslado'
                    );

                inputEquipoId.value =
                    equipo.id;

                fila.querySelector(
                    '.input-marca-traslado'
                ).value =
                    equipo.marca_nombre || '';

                fila.querySelector(
                    '.input-modelo-traslado'
                ).value =
                    equipo.modelo_nombre || '';

                inputSerial.style.borderColor =
                    '#27ae60';
            }
        }
    }


    // ============================================================
    // RENDERIZAR EQUIPOS
    // ============================================================

    function renderizarEquipos(cantidadDeseada) {

        if (!equiposDisponibles.length) {
            listaEquipos.innerHTML = '';
            return;
        }

        let cantidadNueva =
            parseInt(
                cantidadDeseada,
                10
            );

        if (
            Number.isNaN(cantidadNueva) ||
            cantidadNueva < 1
        ) {
            cantidadNueva = 1;
        }

        if (
            cantidadNueva >
            equiposDisponibles.length
        ) {

            cantidadNueva =
                equiposDisponibles.length;

            cantidad.value =
                cantidadNueva;
        }

        // --------------------------------------------------------
        // GUARDAR SELECCIONES ACTUALES
        // --------------------------------------------------------

        const anteriores =
            Array.from(
                listaEquipos.querySelectorAll(
                    '.select-equipo-traslado'
                )
            )
                .map(
                    input =>
                        parseInt(
                            input.value,
                            10
                        ) || null
                );

        // --------------------------------------------------------
        // AGREGAR / QUITAR SOLO LO NECESARIO
        // --------------------------------------------------------

        const cantidadActual =
            listaEquipos.querySelectorAll(
                '.fila-equipo-traslado'
            ).length;

        // Agregar
        if (
            cantidadNueva >
            cantidadActual
        ) {

            for (
                let i = cantidadActual + 1;
                i <= cantidadNueva;
                i++
            ) {

                crearFilaEquipo(
                    i,
                    anteriores[i - 1] || null
                );
            }
        }

        // Quitar
        if (
            cantidadNueva <
            cantidadActual
        ) {

            for (
                let i = cantidadActual;
                i > cantidadNueva;
                i--
            ) {

                const fila =
                    listaEquipos.querySelector(
                        `.fila-equipo-traslado:nth-child(${i})`
                    );

                if (fila) {
                    fila.remove();
                }
            }
        }
    }


    // ============================================================
    // CARGAR EQUIPOS DEL PRODUCTO
    // ============================================================

    async function cargarEquipos() {

        const opcion =
            producto.options[
                producto.selectedIndex
            ];

        if (!opcion) return;

        actualizarUnidad();

        const serializado =
            opcion.dataset.serializado === '1';

        // --------------------------------------------------------
        // PRODUCTO NORMAL
        // --------------------------------------------------------

        if (!serializado) {

            contenedorEquipos.style.display =
                'none';

            listaEquipos.innerHTML = '';

            cantidad.min = 1;

            cantidad.max =
                parseInt(
                    opcion.dataset.stock,
                    10
                ) || '';

            return;
        }

        // --------------------------------------------------------
        // PRODUCTO SERIALIZADO
        // --------------------------------------------------------

        contenedorEquipos.style.display =
            'block';

        const productoId =
            parseInt(
                producto.value,
                10
            );

        const respuesta =
            await apiFetch(
                `${API}/productos/${productoId}/equipos`
            );

        if (!respuesta) return;

        const datos =
            await respuesta.json();

        equiposDisponibles =
            (datos.equipos || [])
                .filter(
                    equipo =>
                        equipo.estado ===
                        'DISPONIBLE'
                );

        if (!equiposDisponibles.length) {

            listaEquipos.innerHTML = `
                <div style="
                    color:#c0392b;
                    font-size:12px;
                    padding:5px;
                ">
                    No hay equipos disponibles para trasladar.
                </div>
            `;

            cantidad.value = 0;
            cantidad.min = 0;
            cantidad.max = 0;

            return;
        }

        cantidad.min = 1;

        cantidad.max =
            equiposDisponibles.length;

        let valor =
            parseInt(
                cantidad.value,
                10
            );

        if (
            Number.isNaN(valor) ||
            valor < 1
        ) {
            valor = 1;
        }

        if (
            valor >
            equiposDisponibles.length
        ) {

            valor =
                equiposDisponibles.length;

            cantidad.value =
                valor;
        }

        renderizarEquipos(
            valor
        );
    }


    // ============================================================
    // CAMBIO DE CANTIDAD
    // ============================================================

    cantidad.addEventListener(
        'input',
        () => {

            const opcion =
                producto.options[
                    producto.selectedIndex
                ];

            const serializado =
                opcion?.dataset?.serializado === '1';

            if (!serializado) {
                return;
            }

            // Al borrar el número no destruimos
            // los equipos existentes.
            if (
                cantidad.value === ''
            ) {
                return;
            }

            let valor =
                parseInt(
                    cantidad.value,
                    10
                );

            if (Number.isNaN(valor)) {
                return;
            }

            if (
                equiposDisponibles.length &&
                valor >
                    equiposDisponibles.length
            ) {

                valor =
                    equiposDisponibles.length;

                cantidad.value =
                    valor;
            }

            renderizarEquipos(
                valor
            );
        }
    );


    // ============================================================
    // CAMBIO DE PRODUCTO
    // ============================================================

    producto.addEventListener(
        'change',
        async () => {

            equiposDisponibles = [];

            cantidad.value = 1;

            await cargarEquipos();
        }
    );


    actualizarUnidad();

    await cargarEquipos();
}

async function guardarTraslado(event) {

    event.preventDefault();

    // ============================================================
    // DATOS GENERALES DEL TRASLADO
    // ============================================================

    const campoNumero =
        document.getElementById('tras-numero');

    const campoSedeOrigen =
        document.getElementById('tras-sede-origen');

    const campoSedeDestino =
        document.getElementById('tras-sede-destino');

    const campoObservaciones =
        document.getElementById('tras-observaciones');

    const contenedorItems =
        document.getElementById('tras-items');

    const numero =
        campoNumero?.value?.trim() || '';

    const sedeOrigen =
        parseInt(
            campoSedeOrigen?.value,
            10
        ) || 0;

    const sedeDestino =
        parseInt(
            campoSedeDestino?.value,
            10
        ) || 0;

    const observaciones =
        campoObservaciones?.value?.trim() || '';

    // ============================================================
    // VALIDACIONES GENERALES
    // ============================================================

    if (!numero) {
        alert(
            'Ingresa el número de documento.'
        );
        return;
    }

    if (!sedeOrigen || !sedeDestino) {
        alert(
            'Selecciona la sede de origen y la sede de destino.'
        );
        return;
    }

    if (
        sedeOrigen ===
        sedeDestino
    ) {
        alert(
            'La sede de origen y destino no pueden ser iguales.'
        );
        return;
    }

    if (!contenedorItems) {
        alert(
            'No se encontró el contenedor de productos del traslado.'
        );
        return;
    }

    const filas =
        contenedorItems.querySelectorAll(
            ':scope > .item-traslado'
        );

    if (!filas.length) {
        alert(
            'Agrega al menos un producto.'
        );
        return;
    }

    const detalle = [];

    // ============================================================
    // PROCESAR CADA PRODUCTO
    // ============================================================

    for (const fila of filas) {

        const producto =
            fila.querySelector(
                '.tras-producto'
            );

        const campoCantidad =
            fila.querySelector(
                '.tras-cantidad'
            );

        const campoUnidad =
            fila.querySelector(
                '.tras-unidad'
            );

        if (!producto) {
            alert(
                'Hay una fila de producto sin selector de producto.'
            );
            return;
        }

        if (!campoCantidad) {
            alert(
                'Hay una fila de producto sin cantidad.'
            );
            return;
        }

        const cantidad =
            parseInt(
                campoCantidad.value,
                10
            ) || 0;

        const opcion =
            producto.options[
                producto.selectedIndex
            ];

        if (!producto.value) {
            alert(
                'Selecciona un producto.'
            );
            return;
        }

        if (!opcion) {
            alert(
                'No se pudo identificar el producto seleccionado.'
            );
            return;
        }

        if (cantidad <= 0) {
            alert(
                'La cantidad debe ser mayor que cero.'
            );
            campoCantidad.focus();
            return;
        }

        const serializado =
            opcion.dataset?.serializado === '1';

        // ========================================================
        // PRODUCTO SERIALIZADO
        // ========================================================

        if (serializado) {

            const filasEquipos =
                fila.querySelectorAll(
                    '.fila-equipo-traslado'
                );

            if (
                filasEquipos.length !==
                cantidad
            ) {
                alert(
                    `El producto "${opcion.text}" tiene ` +
                    `${filasEquipos.length} equipo(s) seleccionado(s), ` +
                    `pero la cantidad indicada es ${cantidad}.`
                );
                return;
            }

            const unidades = [];

            const idsSeleccionados =
                new Set();

            const serialesSeleccionados =
                new Set();

            // ----------------------------------------------------
            // PROCESAR EQUIPOS
            // ----------------------------------------------------

            for (
                const filaEquipo
                of filasEquipos
            ) {

                const inputEquipoId =
                    filaEquipo.querySelector(
                        '.select-equipo-traslado'
                    );

                const inputSerial =
                    filaEquipo.querySelector(
                        '.input-serial-traslado'
                    );

                const equipoId =
                    parseInt(
                        inputEquipoId?.value,
                        10
                    ) || 0;

                const serial =
                    inputSerial?.value?.trim() || '';

                // ------------------------------------------------
                // SERIAL OBLIGATORIO
                // ------------------------------------------------

                if (!serial) {

                    alert(
                        'Debes escribir o escanear un serial para cada equipo.'
                    );

                    inputSerial?.focus();

                    return;
                }

                // ------------------------------------------------
                // EQUIPO OBLIGATORIO
                // ------------------------------------------------

                if (!equipoId) {

                    alert(
                        `El serial "${serial}" no corresponde a un equipo disponible.`
                    );

                    inputSerial?.focus();

                    return;
                }

                // ------------------------------------------------
                // NO REPETIR ID
                // ------------------------------------------------

                if (
                    idsSeleccionados.has(
                        equipoId
                    )
                ) {

                    alert(
                        `El equipo con serial "${serial}" está repetido.`
                    );

                    inputSerial?.focus();

                    return;
                }

                // ------------------------------------------------
                // NO REPETIR SERIAL
                // ------------------------------------------------

                const serialNormalizado =
                    serial.toLowerCase();

                if (
                    serialesSeleccionados.has(
                        serialNormalizado
                    )
                ) {

                    alert(
                        `El serial "${serial}" está repetido.`
                    );

                    inputSerial?.focus();

                    return;
                }

                idsSeleccionados.add(
                    equipoId
                );

                serialesSeleccionados.add(
                    serialNormalizado
                );

                unidades.push({
                    equipo_id:
                        equipoId,

                    serial:
                        serial
                });
            }

            // ----------------------------------------------------
            // AGREGAR PRODUCTO SERIALIZADO
            // ----------------------------------------------------

            detalle.push({

                producto_id:
                    parseInt(
                        producto.value,
                        10
                    ),

                cantidad:
                    cantidad,

                unidad:
                    campoUnidad?.value ||
                    'UND',

                unidades:
                    unidades,

                observaciones:
                    ''
            });

        } else {

            // ====================================================
            // PRODUCTO NORMAL
            // ====================================================

            const stock =
                parseInt(
                    opcion.dataset?.stock,
                    10
                ) || 0;

            if (
                cantidad >
                stock
            ) {

                alert(
                    `Stock insuficiente para ${opcion.text}. ` +
                    `Disponible: ${stock}.`
                );

                campoCantidad.focus();

                return;
            }

            detalle.push({

                producto_id:
                    parseInt(
                        producto.value,
                        10
                    ),

                cantidad:
                    cantidad,

                unidad:
                    campoUnidad?.value ||
                    'UND',

                unidades:
                    [],

                observaciones:
                    ''
            });
        }
    }

    // ============================================================
    // VALIDAR QUE HAYA DETALLE
    // ============================================================

    if (!detalle.length) {
        alert(
            'No hay productos válidos para trasladar.'
        );
        return;
    }

    // ============================================================
    // DATOS QUE SE ENVÍAN AL BACKEND
    // ============================================================

    const datos = {

        numero_documento:
            numero,

        sede_origen_id:
            sedeOrigen,

        sede_destino_id:
            sedeDestino,

        observaciones:
            observaciones,

        detalle:
            detalle
    };

    console.log(
        'DATOS ENVIADOS TRASLADO:',
        datos
    );

    // ============================================================
    // ENVIAR AL BACKEND
    // ============================================================

    const res =
        await apiFetch(
            `${API}/traslados/`,
            {
                method: 'POST',

                body:
                    JSON.stringify(
                        datos
                    )
            }
        );

    if (!res) {
        return;
    }

    let resultado = {};

    try {

        resultado =
            await res.json();

    } catch (error) {

        console.error(
            'No se pudo leer la respuesta del servidor:',
            error
        );
    }

    // ============================================================
    // ERROR
    // ============================================================

    if (!res.ok) {

        alert(
            'Error al crear traslado:\n\n' +
            (
                resultado.error ||
                `Error HTTP ${res.status}`
            )
        );

        return;
    }

    // ============================================================
    // ÉXITO
    // ============================================================

    await mostrarConfirm(
        `El traslado ${
            resultado.numero_documento ||
            numero
        } fue creado correctamente.`,
        'Traslado creado',
        '✓',
        'Aceptar'
    );

    cerrarModal(
        'modal-traslado'
    );

    limpiarFormTraslado();

    await cargarTraslados();

    if (
        typeof cargarProductos ===
        'function'
    ) {
        await cargarProductos();
    }
}

let productosFiltrables = [];

function filtrarProductos() {

    const texto =
        (
            document.getElementById(
                'buscar-productos'
            )?.value || ''
        )
        .trim()
        .toLowerCase();

    const sede =
        (
            document.getElementById(
                'filtro-sede-productos'
            )?.value || ''
        )
        .trim();

    const productosFiltrados =
        productosFiltrables.filter(
            p => {

                const codigo =
                    String(
                        p.codigo || ''
                    ).toLowerCase();

                const nombre =
                    String(
                        p.nombre || ''
                    ).toLowerCase();

                const descripcion =
                    String(
                        p.descripcion || ''
                    ).toLowerCase();

                const coincideTexto =
                    !texto ||
                    codigo.includes(texto) ||
                    nombre.includes(texto) ||
                    descripcion.includes(texto);

                const coincideSede =
                    !sede ||
                    String(
                        p.sede_id || ''
                    ) === sede;

                return (
                    coincideTexto &&
                    coincideSede
                );
            }
        );

    pintarProductos(
        productosFiltrados
    );
}

function limpiarFormTraslado() {

    document.getElementById('tras-numero').value = '';

    document.getElementById('tras-sede-origen').value = '';

    document.getElementById('tras-sede-destino').value = '';

    document.getElementById('tras-observaciones').value = '';

    document.getElementById('tras-items').innerHTML = `
        <p style="font-size:12px;color:#6b8aab">
            Selecciona primero la sede de origen.
        </p>
    `;

    productosCacheTraslado = [];
}

// TRASLADOS ENTRE SEDES
let trasladosData = [];
let sedesTrasladosMap = {};

async function cargarTraslados() {
    const res = await apiFetch(`${API}/traslados/`);
    if (!res) return;

    trasladosData = await res.json();

    if (usuario.rol === 'admin' || usuario.rol === 'consulta') {
        const sel = document.getElementById('filtro-sede-traslados');

        if (sel) {
            const valorActual = sel.value;

            const resSedes = await apiFetch(`${API}/auth/sedes`);

            if (resSedes) {
                const sedes = await resSedes.json();

                sedesTrasladosMap = {};
                sedes.forEach(s => {
                    sedesTrasladosMap[s.id] = s.nombre;
                });

                sel.innerHTML = '<option value="">&#8212; Todas las sedes &#8212;</option>';
                sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                    `<option value="${s.id}">${s.nombre}</option>`
                ));
                sel.style.display = 'block';
                sel.value = valorActual;
            }
        }
    }

    renderizarTraslados(trasladosData);

    filtrarTraslados();
}

function formatearFechaTraslado(fechaTexto) {
    if (!fechaTexto) return '—';

    const texto = String(fechaTexto).trim();

    const dias = {
        Sun: 'dom',
        Mon: 'lun',
        Tue: 'mar',
        Wed: 'mié',
        Thu: 'jue',
        Fri: 'vie',
        Sat: 'sáb'
    };

    const meses = {
        Jan: 'ene',
        Feb: 'feb',
        Mar: 'mar',
        Apr: 'abr',
        May: 'may',
        Jun: 'jun',
        Jul: 'jul',
        Aug: 'ago',
        Sep: 'sep',
        Oct: 'oct',
        Nov: 'nov',
        Dec: 'dic'
    };

    const partes = texto.match(
        /^(Sun|Mon|Tue|Wed|Thu|Fri|Sat),\s*(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\s+(\d{2}:\d{2}:\d{2})/
    );

    if (!partes) {
        return texto.replace(/\s+GMT$/i, '');
    }

    const diaSemana = partes[1];
    const dia = partes[2].padStart(2, '0');
    const mes = partes[3];
    const anio = partes[4];
    const hora = partes[5];

    return `${dias[diaSemana]}, ${dia} ${meses[mes]} ${anio} ${hora}`;
}

function renderizarTraslados(lista) {
    const subtitulo = document.getElementById('subtitulo-traslados');
    if (subtitulo) {
        subtitulo.textContent =
            `${lista.length} traslado${lista.length !== 1 ? 's' : ''} registrado${lista.length !== 1 ? 's' : ''}`;
    }

    const tbody = document.getElementById('tabla-traslados');

    if (!tbody) return;

    tbody.innerHTML = '';

    if (lista.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align:center;padding:30px;color:#6b8aab">
                    No hay traslados registrados.
                </td>
            </tr>
        `;
        return;
    }

    lista.forEach(t => {

        let badgeClase = 'badge-ok';
        let badgeTexto = t.estado || 'PENDIENTE';

        if (t.estado === 'PENDIENTE') {
            badgeClase = 'badge-warning';
        }

        if (t.estado === 'RECIBIDO') {
            badgeClase = 'badge-ok';
        }

        if (t.estado === 'CANCELADO') {
            badgeClase = 'badge-danger';
        }

        // Formatear fecha del traslado
        const fechaCreacion = formatearFechaTraslado(t.fecha_creacion);
   
        tbody.insertAdjacentHTML('beforeend', `
            <tr>
                <td>
                    <strong>${sanitizar(t.numero_documento)}</strong>
                </td>

                <td>
                    ${sanitizar(t.sede_origen_nombre || '—')}
                </td>

                <td>
                    ${sanitizar(t.sede_destino_nombre || '—')}
                </td>

                <td>
                    ${t.total_items || 0}
                </td>

                <td>
                    <span class="badge ${badgeClase}">
                        ${sanitizar(badgeTexto)}
                    </span>
                </td>

                <td>
                    ${sanitizar(fechaCreacion)}
                </td>

                <td>
                    <div class="acciones">
                        <button
                            class="btn-accion"
                            onclick="verTraslado(${t.id})">
                            👁️ Ver
                        </button>

                        <button
                            class="btn-accion"
                            onclick="verPDFTraslado(${t.id})">
                            📄 PDF
                        </button>

                        ${
                            usuario.rol === 'admin' && t.estado === 'PENDIENTE'
                            ? `
                                <button
                                    class="btn-accion"
                                    onclick="recibirTraslado(${t.id})">
                                    ✅ Recibir
                                </button>
                            `
                            : ''
                        }
                    </div>
                </td>
            </tr>
        `);
    });
}

function filtrarTraslados() {
    const texto = document
        .getElementById('buscar-traslados')
        .value
        .trim()
        .toLowerCase();

    const sedeFiltro = document.getElementById('filtro-sede-traslados')?.value || '';

    // Nombre de la sede seleccionada (respaldo por si el backend
    // no devuelve sede_origen_id / sede_destino_id en el listado)
    const nombreSedeFiltro =
        sedeFiltro
            ? String(sedesTrasladosMap[sedeFiltro] || '').toLowerCase()
            : '';

    let filtrados = trasladosData.filter(t =>
        String(t.numero_documento || '').toLowerCase().includes(texto) ||
        String(t.sede_origen_nombre || '').toLowerCase().includes(texto) ||
        String(t.sede_destino_nombre || '').toLowerCase().includes(texto) ||
        String(t.estado || '').toLowerCase().includes(texto)
    );

    if (sedeFiltro) {
        filtrados = filtrados.filter(t => {

            const coincideOrigenId =
                t.sede_origen_id != null &&
                String(t.sede_origen_id) === String(sedeFiltro);

            const coincideDestinoId =
                t.sede_destino_id != null &&
                String(t.sede_destino_id) === String(sedeFiltro);

            const coincideOrigenNombre =
                nombreSedeFiltro &&
                String(t.sede_origen_nombre || '').toLowerCase() === nombreSedeFiltro;

            const coincideDestinoNombre =
                nombreSedeFiltro &&
                String(t.sede_destino_nombre || '').toLowerCase() === nombreSedeFiltro;

            // La sede coincide si el traslado la tiene como origen o como destino
            return (
                coincideOrigenId ||
                coincideDestinoId ||
                coincideOrigenNombre ||
                coincideDestinoNombre
            );
        });
    }

    renderizarTraslados(filtrados);
}

async function verTraslado(id) {

    const res =
        await apiFetch(
            `${API}/traslados/${id}`
        );

    if (!res) return;

    const traslado =
        await res.json();

    console.log(
        'Traslado recibido:',
        traslado
    );

    // ============================================================
    // EL SERVIDOR RECHAZÓ O NO ENCONTRÓ EL TRASLADO
    // ============================================================
    //
    // Antes esto seguía de largo y pintaba el modal con todos los
    // campos vacíos (mostrando "—" en todo), sin avisar que la
    // petición había fallado. Ahora se detiene y avisa.
    // ============================================================

    if (!res.ok || !traslado || !traslado.numero_documento) {

        console.error(
            'No se pudo cargar el detalle del traslado:',
            res.status,
            traslado
        );

        alert(
            traslado?.error ||
            'No se pudo cargar el detalle de este traslado. ' +
            'Puede que tu usuario no tenga permiso para verlo, ' +
            'o que el traslado no exista.'
        );

        return;
    }

    // ============================================================
    // INFORMACIÓN GENERAL
    // ============================================================

    document.getElementById(
        'ver-tras-numero'
    ).textContent =
        `Traslado ${traslado.numero_documento || '—'}`;

    // ------------------------------------------------------------
    // ORIGEN
    // ------------------------------------------------------------

    document.getElementById(
        'ver-tras-origen'
    ).textContent =
        traslado.sede_origen_nombre || '—';

    document.getElementById(
        'ver-tras-origen-ciudad'
    ).textContent =
        traslado.sede_origen_ciudad || '—';

    // ------------------------------------------------------------
    // DESTINO
    // ------------------------------------------------------------

    document.getElementById(
        'ver-tras-destino'
    ).textContent =
        traslado.sede_destino_nombre || '—';

    document.getElementById(
        'ver-tras-destino-ciudad'
    ).textContent =
        traslado.sede_destino_ciudad || '—';

    // ------------------------------------------------------------
    // ESTADO
    // ------------------------------------------------------------

    document.getElementById(
        'ver-tras-estado'
    ).textContent =
        traslado.estado || '—';

    // ------------------------------------------------------------
    // FECHA DE CREACIÓN
    // ------------------------------------------------------------

    document.getElementById(
        'ver-tras-fecha'
    ).textContent =
        formatearFechaTraslado(
            traslado.fecha_creacion
        );

    // ------------------------------------------------------------
    // FECHA DE RECEPCIÓN
    // ------------------------------------------------------------

    document.getElementById(
        'ver-tras-finalizacion'
    ).textContent =
        traslado.fecha_recepcion
            ? formatearFechaTraslado(
                traslado.fecha_recepcion
            )
            : 'Pendiente';

    // ------------------------------------------------------------
    // CREADO POR
    //
    // El backend devuelve:
    // creador_nombre
    // ------------------------------------------------------------

    document.getElementById(
        'ver-tras-creado'
    ).textContent =
        traslado.creador_nombre || '—';

    // ------------------------------------------------------------
    // RECIBIDO POR
    //
    // El backend devuelve:
    // recibido_nombre
    // ------------------------------------------------------------

    document.getElementById(
        'ver-tras-recibido'
    ).textContent =
        traslado.recibido_nombre || '—';

    // ------------------------------------------------------------
    // OBSERVACIONES
    // ------------------------------------------------------------

    document.getElementById(
        'ver-tras-observaciones'
    ).textContent =
        traslado.observaciones ||
        'Sin observaciones';

    // ============================================================
    // PRODUCTOS
    // ============================================================

    const tbody =
        document.getElementById(
            'ver-tras-productos'
        );

    tbody.innerHTML = '';

    if (
        !traslado.detalle ||
        traslado.detalle.length === 0
    ) {

        tbody.innerHTML = `
            <tr>
                <td
                    colspan="6"
                    style="
                        text-align:center;
                        color:#6b8aab;
                        padding:20px;
                    "
                >
                    No hay productos registrados.
                </td>
            </tr>
        `;

    } else {

        traslado.detalle.forEach(
            item => {

                const tr =
                    document.createElement(
                        'tr'
                    );

                // ------------------------------------------------
                // PRODUCTO
                // ------------------------------------------------

                const producto =
                    item.producto_nombre ||
                    '—';

                // ------------------------------------------------
                // MODELO
                // ------------------------------------------------

                const modelo =
                    item.modelo_nombre ||
                    '—';

                // ------------------------------------------------
                // MARCA
                // ------------------------------------------------

                const marca =
                    item.marca_nombre ||
                    '—';

                // ------------------------------------------------
                // SERIAL
                // ------------------------------------------------

                const serial =
                    item.equipo_serial ||
                    '—';

                // ------------------------------------------------
                // UNIDAD
                // ------------------------------------------------

                const unidad =
                    item.unidad ||
                    item.unidad_nombre ||
                    'UND';

                // ------------------------------------------------
                // CANTIDAD
                // ------------------------------------------------

                const cantidad =
                    item.cantidad ||
                    0;

                tr.innerHTML = `
                    <td>
                        ${sanitizar(producto)}
                    </td>

                    <td>
                        ${sanitizar(modelo)}
                    </td>

                    <td>
                        ${sanitizar(marca)}
                    </td>

                    <td>
                        ${sanitizar(serial)}
                    </td>

                    <td>
                        ${sanitizar(unidad)}
                    </td>

                    <td>
                        ${cantidad}
                    </td>
                `;

                tbody.appendChild(
                    tr
                );
            }
        );
    }

    // ============================================================
    // ABRIR MODAL
    // ============================================================

    document
        .getElementById(
            'modal-ver-traslado'
        )
        .classList.add(
            'visible'
        );
}

async function recibirTraslado(id) {

    if (usuario.rol !== 'admin') {
        alert('No tienes permisos para recibir traslados.');
        return;
    }

    if (!await mostrarConfirm(
        '¿Confirmar recepción de este traslado?',
        '¿Recibir traslado?',
        '📦',
        'Confirmar'
    )) {
        return;
    }

    const res = await apiFetch(`${API}/traslados/${id}/recibir`, {
        method: 'PUT'
    });

    if (!res) return;

    const datos = await res.json();

    if (!res.ok) {
        alert(datos.error || 'No se pudo recibir el traslado.');
        return;
    }

    mostrarNotificacion(
        'Traslado recibido correctamente.',
        'exito'
    );

    await cargarTraslados();

    if (typeof cargarProductos === 'function') {
        await cargarProductos();
    }
}

function verPDFTraslado(id) {

    const token = localStorage.getItem('token');

    if (!token) {
        alert('Sesión no válida.');
        return;
    }

    window.open(
        `${API}/pdf/traslados/${id}?token=${encodeURIComponent(token)}`,
        '_blank'
    );
}

async function verEquiposProducto(productoId) {
    try {
        const res = await apiFetch(
            `${API}/productos/${productoId}/equipos`
        );

        if (!res) return;

        const resultado = await res.json();

        if (!res.ok) {
            throw new Error(
                resultado.error ||
                'No se pudieron consultar los equipos.'
            );
        }

        const producto = resultado.producto || {};
        const equipos = resultado.equipos || [];

        document.getElementById('modal-equipos-titulo').textContent =
            `${producto.codigo || ''} — ${producto.nombre || 'Producto'}`;

        const tbody =
            document.getElementById('tabla-equipos-producto');

        tbody.innerHTML = '';

        if (equipos.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5"
                        style="text-align:center;color:#6b8aab;padding:2rem">
                        No hay equipos serializados registrados.
                    </td>
                </tr>
            `;
        } else {
            equipos.forEach(equipo => {
                tbody.insertAdjacentHTML(
                    'beforeend',
                    `
                    <tr>
                        <td>
                            <strong>
                                ${sanitizar(equipo.serial || '—')}
                            </strong>
                        </td>

                        <td>
                            ${sanitizar(equipo.marca_nombre || '—')}
                        </td>

                        <td>
                            ${sanitizar(equipo.modelo_nombre || '—')}
                        </td>

                        <td>
                            ${sanitizar(
                                equipo.condicion === 'DANADO'
                                    ? 'Dañado'
                                    : (equipo.condicion || '—')
                            )}
                        </td>

                        <td>
                            ${sanitizar(equipo.estado || '—')}
                        </td>
                    </tr>
                    `
                );
            });
        }

        abrirModal('modal-equipos-producto');

    } catch (error) {
        console.error(
            'Error al consultar equipos:',
            error
        );

        alert(
            'No se pudieron cargar los equipos:\n\n' +
            error.message
        );
    }
}