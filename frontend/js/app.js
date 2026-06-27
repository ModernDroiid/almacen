const API = 'https://almacen-backend-ae4l.onrender.com/api';

// ══ SESION ══════════════════════════════════════════════════

const token   = localStorage.getItem('token');
const usuario = JSON.parse(localStorage.getItem('usuario') || '{}');

if (!token) {
    window.location.href = 'login.html';
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
    if (usuario.rol !== 'admin') return;

    const select = document.getElementById('selector-sede');
    const res    = await apiFetch(`${API}/auth/sedes`);
    if (!res) return;
    const sedes  = await res.json();

    select.innerHTML = '<option value="">— Todas las sedes —</option>'; // ✅
    select.innerHTML += sedes.map(s =>
        `<option value="${s.id}">${s.nombre} — ${s.ciudad}</option>`
    ).join('');
    select.value = '';  // ✅ por default muestra todas
    sedeActual = null;  // ✅
    select.style.display = 'block';
}

function cambiarSedeActual() {
    const val = document.getElementById('selector-sede').value;
    sedeActual = val ? parseInt(val) : null;
    localStorage.setItem('sedeActual', sedeActual || '');
    cargarProductos();
}

function urlConSede(base) {
    if (usuario.rol === 'admin' && sedeActual) {
        const sep = base.includes('?') ? '&' : '?';
        return `${base}${sep}sede_id=${sedeActual}`;
    }
    return base;
}

// ══ NAVEGACIÓN ══════════════════════════════════════════════

function mostrarSeccion(nombre, btn) {
    if (nombre === 'usuarios' && usuario.rol !== 'admin') return; // ✅ agrega esto
    document.querySelectorAll('.seccion').forEach(s => s.classList.remove('activa'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('sec-' + nombre).classList.add('activa');
    btn.classList.add('active');
    if (nombre === 'productos')     cargarProductos();
    if (nombre === 'entradas')      cargarEntradas();
    if (nombre === 'salidas')       cargarSalidas();
    if (nombre === 'devoluciones')  cargarDevoluciones();
    if (nombre === 'consolidado') cargarPuntos();
    if (nombre === 'modelos')       cargarModelos();
    if (nombre === 'marcas')        cargarMarcas();
    if (nombre === 'usuarios')      cargarUsuarios();
}

// ══ MODALES ═════════════════════════════════════════════════

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
            sel.innerHTML = '<option value="">— Selecciona la sede —</option>';
            sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                `<option value="${s.id}" ${s.id === sedeActual ? 'selected' : ''}>${s.nombre} — ${s.ciudad}</option>`
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
    }

    if (id === 'modal-salida' && usuario.rol === 'admin') {
            apiFetch(`${API}/auth/sedes`).then(r => r.json()).then(sedes => {
                const sel = document.getElementById('sal-sede');
                sel.innerHTML = '<option value="">— Selecciona la sede —</option>';
                sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                    `<option value="${s.id}" ${s.id === sedeActual ? 'selected' : ''}>${s.nombre} — ${s.ciudad}</option>`
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
            sel.innerHTML = '<option value="">— Selecciona la sede —</option>';
            sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                `<option value="${s.id}" ${s.id === sedeActual ? 'selected' : ''}>${s.nombre} — ${s.ciudad}</option>`
            ));
            document.getElementById('campo-sede-devolucion').style.display = 'block';
        });
    } else if (id === 'modal-devolucion') {
        document.getElementById('campo-sede-devolucion').style.display = 'none';
    }
    
    if (id === 'modal-producto' && usuario.rol === 'admin') {
        apiFetch(`${API}/auth/sedes`).then(r => r.json()).then(sedes => {
            const sel = document.getElementById('prod-sede');
            sel.innerHTML = '<option value="">— Selecciona la sede —</option>';
            sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                `<option value="${s.id}" ${s.id === sedeActual ? 'selected' : ''}>${s.nombre} — ${s.ciudad}</option>`
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

async function guardarModeloEnCatalogo(nombre) {
    if (!nombre || !nombre.trim()) return;
    await apiFetch(`${API}/catalogos/modelos`, {
        method: 'POST',
        body: JSON.stringify({ nombre: nombre.trim() })
    });
}

async function guardarMarcaEnCatalogo(nombre) {
    if (!nombre || !nombre.trim()) return;
    await apiFetch(`${API}/catalogos/marcas`, {
        method: 'POST',
        body: JSON.stringify({ nombre: nombre.trim() })
    });
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
                        <button class="btn-accion" onclick="editarModelo(${m.id}, '${m.nombre}')">✏️ Editar</button>
                        <button class="btn-accion danger" onclick="eliminarModelo(${m.id}, '${m.nombre}')">🗑️ Eliminar</button>
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
    if (!confirm(`Eliminar el modelo "${nombre}"?`)) return;
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
                        <button class="btn-accion" onclick="editarMarca(${m.id}, '${m.nombre}')">✏️ Editar</button>
                        <button class="btn-accion danger" onclick="eliminarMarca(${m.id}, '${m.nombre}')">🗑️ Eliminar</button>
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
    if (!confirm(`Eliminar la marca "${nombre}"?`)) return;
    await apiFetch(`${API}/catalogos/marcas/${id}`, { method: 'DELETE' });
    cargarMarcas();
}

function limpiarFormMarca() {
    document.getElementById('marca-id').value     = '';
    document.getElementById('marca-nombre').value = '';
    document.getElementById('modal-marca-titulo').textContent = 'Nueva marca';
}

// ══ PRODUCTOS (separados por sede) ════════════════════════════

async function cargarProductos() {
    const respuesta = await apiFetch(urlConSede(`${API}/productos/`));
    if (!respuesta) return;
    const productos = await respuesta.json();

    const total    = productos.length;
    const agotados = productos.filter(p => p.stock === 0).length;
    const bajos    = productos.filter(p => p.stock > 0 && p.stock <= 5).length;
    const enstock  = total - agotados - bajos;

    document.getElementById('stat-total').textContent    = total;
    document.getElementById('stat-enstock').textContent  = enstock;
    document.getElementById('stat-bajo').textContent     = bajos;
    document.getElementById('stat-agotados').textContent = agotados;
    document.getElementById('subtitulo-productos').textContent = `${total} productos registrados`;

    const tbody = document.getElementById('tabla-productos');
    tbody.innerHTML = '';

    if (total === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#6b8aab;padding:2rem">Sin productos registrados</td></tr>';
        return;
    }

    productos.forEach(p => {
        let badgeClase, badgeTexto;
        if (p.stock === 0) {
            badgeClase = 'badge-agotado'; badgeTexto = 'Agotado';
        } else if (p.stock <= 5) {
            badgeClase = 'badge-minimo'; badgeTexto = 'Stock bajo';
        } else {
            badgeClase = 'badge-ok'; badgeTexto = 'En stock';
        }

        tbody.insertAdjacentHTML('beforeend', `
            <tr>
                <td><span style="font-family:monospace;font-size:12px;color:#1a6fc4;font-weight:600">${p.codigo || '—'}</span></td>
                <td>
                    <strong>${p.nombre}</strong>
                    <div class="sub">${p.descripcion || '—'}</div>
                </td>
                <td><span style="font-size:11px;color:#4a6080">${p.sede_nombre || '—'}</span></td>
                <td>${p.unidad}</td>
                <td>${p.stock}</td>
                <td><span class="badge ${badgeClase}">${badgeTexto}</span></td>
                <td>
                    <div class="acciones">
                        <button class="btn-accion" onclick="editarProducto(${p.id})">✏️ Editar</button>
                        <button class="btn-accion danger" onclick="eliminarProducto(${p.id}, '${p.nombre}')">🗑️ Eliminar</button>
                    </div>
                </td>
            </tr>
        `);
    });
}

async function guardarProducto(event) {
    event.preventDefault();
    const id = document.getElementById('prod-id').value;
    
    const sede_id = parseInt(document.getElementById('prod-sede').value) || sedeActual;
    
    if (usuario.rol === 'admin' && !sede_id) {
        alert('Selecciona una sede para el producto');
        return;
    }

    const datos = {
        codigo:       document.getElementById('prod-codigo').value,
        nombre:       document.getElementById('prod-nombre').value,
        descripcion:  document.getElementById('prod-descripcion').value,
        unidad:       document.getElementById('prod-unidad').value,
        stock:        parseInt(document.getElementById('prod-stock-minimo').value) || 0,
        stock_minimo: parseInt(document.getElementById('prod-stock-minimo').value) || 0,
        sede_id:      sede_id,
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
    abrirModal('modal-producto');
}

async function eliminarProducto(id, nombre) {
    if (!confirm(`Eliminar "${nombre}"? Esta accion no se puede deshacer.`)) return;
    await apiFetch(`${API}/productos/${id}`, { method: 'DELETE' });
    cargarProductos();
}

function limpiarFormProducto() {
    document.getElementById('prod-id').value           = '';
    document.getElementById('prod-codigo').value       = '';
    document.getElementById('prod-nombre').value       = '';
    document.getElementById('prod-descripcion').value  = '';
    document.getElementById('prod-unidad').value       = 'UND';
    document.getElementById('prod-stock-minimo').value = '0';
    document.getElementById('modal-producto-titulo').textContent = 'Nuevo producto';
    document.getElementById('prod-sede').value = '';
}

// ══ ENTRADAS ════════════════════════════════════════════════

let productosCache = [];

async function generarNumeroEntrada() {
    const fecha = document.getElementById('ent-fecha').value;
    const obra  = document.getElementById('ent-obra').value.trim();
    if (!fecha || !obra) return;
    const base       = `ENT-${fecha}-${obra.toUpperCase().replace(/ /g, '-')}`;
    const res        = await apiFetch(`${API}/entradas/`);
    if (!res) return;
    const entradas   = await res.json();
    const existentes = entradas.filter(e => e.numero_documento.startsWith(base));
    document.getElementById('ent-numero').value = `${base}-${existentes.length + 1}`;
}

let entradasCache = [];

async function cargarEntradas() {
    const res = await apiFetch(urlConSede(`${API}/entradas/`));
    if (!res) return;
    entradasCache = await res.json();

    if (usuario.rol === 'admin') {
        const sel = document.getElementById('filtro-sede-entradas');
        const valorActual = sel.value; // ✅ guardamos el valor antes de recargar

        const resSedes = await apiFetch(`${API}/auth/sedes`);
        if (resSedes) {
            const sedes = await resSedes.json();
            sel.innerHTML = '<option value="">— Todas las sedes —</option>';
            sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                `<option value="${s.id}">${s.nombre} — ${s.ciudad}</option>`
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
                        <button class="btn-accion danger" onclick="eliminarEntrada(${e.id}, '${e.numero_documento}')">🗑️ Eliminar</button>
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
    // ✅ Siempre recarga productos según la sede seleccionada en el modal
    const sedeEntrada = parseInt(document.getElementById('ent-sede').value) || sedeActual;
    const urlProductos = usuario.rol === 'admin' && sedeEntrada
        ? `${API}/productos/?sede_id=${sedeEntrada}`
        : urlConSede(`${API}/productos/`);

    const res = await apiFetch(urlProductos);
    if (!res) return;
    productosCache = await res.json();
    if (catalogoModelos.length === 0 && catalogoMarcas.length === 0) {
        await cargarCatalogos();
    }

    const opciones = productosCache
        .map(p => `<option value="${p.id}" data-unidad="${p.unidad || 'UND'}">[${p.codigo||'—'}] ${p.nombre}</option>`)
        .join('');

    const unidadesDisponibles = ['UND','MTS','KG','CAJA','ROLLO','LITRO'];
    const opcionesUnidad = unidadesDisponibles.map(u => `<option value="${u}">${u}</option>`).join('');

    const item = document.createElement('div');
    item.style.cssText = 'display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 70px 55px 30px;gap:6px;align-items:start';
    item.innerHTML = `
        <select class="select-producto" style="border:0.5px solid #c8d8ea;border-radius:8px;padding:6px 8px;font-size:12px;color:#0d2137;width:100%;min-width:0;height:32px">
            ${opciones}
        </select>
        ${crearComboHTML('modelo', 'Modelo')}
        ${crearComboHTML('marca', 'Marca')}
        <input type="text" placeholder="Serial"
               style="border:0.5px solid #c8d8ea;border-radius:8px;padding:6px 8px;font-size:12px;width:100%;min-width:0;height:32px;box-sizing:border-box">
        <select class="select-unidad" style="border:0.5px solid #c8d8ea;border-radius:8px;padding:6px 4px;font-size:12px;color:#0d2137;width:100%;min-width:0;height:32px">
            ${opcionesUnidad}
        </select>
        <input type="number" min="1" value="1"
               style="border:0.5px solid #c8d8ea;border-radius:8px;padding:6px 8px;font-size:12px;text-align:center;width:100%;min-width:0;height:32px;box-sizing:border-box">
        <button type="button"
                style="background:#fdecea;border:none;border-radius:6px;color:#c0392b;cursor:pointer;font-size:14px;width:30px;height:32px;flex-shrink:0"
                onclick="this.parentElement.remove()">✕</button>
    `;
    document.getElementById('ent-items').appendChild(item);
    item.querySelectorAll('.combo-wrap').forEach(activarCombo);

    const selectProducto = item.querySelector('.select-producto');
    const selectUnidad    = item.querySelector('.select-unidad');
    function autocompletarUnidad() {
        const opcion = selectProducto.options[selectProducto.selectedIndex];
        selectUnidad.value = opcion?.dataset.unidad || 'UND';
    }
    selectProducto.addEventListener('change', autocompletarUnidad);
    autocompletarUnidad();
}

async function guardarEntrada(event) {
    event.preventDefault();

    const numero = document.getElementById('ent-numero').value;
    if (!numero) {
        alert('Escribe el Origen para generar el numero de documento');
        return;
    }

    const filas = document.getElementById('ent-items').querySelectorAll(':scope > div');
    if (filas.length === 0) {
        alert('Agrega al menos un producto');
        return;
    }

    const detalle = Array.from(filas).map(fila => {
        const selectProducto = fila.querySelector('.select-producto');
        const selectUnidad   = fila.querySelector('.select-unidad');
        const comboModelo    = fila.querySelector('[data-tipo="modelo"] .combo-input');
        const comboMarca     = fila.querySelector('[data-tipo="marca"] .combo-input');
        const inputSerial    = fila.querySelectorAll('input[type="text"]')[2];
        const inputCantidad  = fila.querySelector('input[type="number"]');
        return {
            producto_id: parseInt(selectProducto.value),
            unidad:      selectUnidad.value,
            modelo:      comboModelo.value,
            marca:       comboMarca.value,
            serial:      inputSerial ? inputSerial.value : '',
            cantidad:    parseInt(inputCantidad.value) || 1
        };
    });

    const datos = {
        numero_documento: numero,
        obra:             document.getElementById('ent-obra').value,
        destino:          document.getElementById('ent-destino').value || 'Almacen',
        observaciones:    document.getElementById('ent-observaciones').value,
        sede_id:          parseInt(document.getElementById('ent-sede').value) || sedeActual,
        detalle:          detalle
    };

    const res = await apiFetch(`${API}/entradas/`, {
        method: 'POST',
        body: JSON.stringify(datos)
    });

    if (!res) return;
    const resultado = await res.json();

    if (res.ok) {
        for (const item of detalle) {
            await guardarModeloEnCatalogo(item.modelo);
            await guardarMarcaEnCatalogo(item.marca);
        }
        await cargarCatalogos();
        cerrarModal('modal-entrada');
        limpiarFormEntrada();
        cargarEntradas();
        cargarProductos();
    } else {
        alert('Error: ' + resultado.error);
    }
}

function limpiarFormEntrada() {
    document.getElementById('ent-numero').value        = '';
    document.getElementById('ent-fecha').value         = '';
    document.getElementById('ent-obra').value          = '';
    document.getElementById('ent-destino').value       = 'Almacen';
    document.getElementById('ent-observaciones').value = '';
    document.getElementById('ent-items').innerHTML     = '';
    document.getElementById('ent-sede').value = '';
    productosCache = [];
}

function verPDFEntrada(id) {
    window.open(`${API}/pdf/entrada/${id}?token=${token}`, '_blank');
}

async function eliminarEntrada(id, numero) {
    if (!confirm(`Eliminar la entrada "${numero}"?\n\nEsto revertira el stock que se sumo con esta entrada.`)) return;
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

    if (usuario.rol === 'admin') {
        const sel = document.getElementById('filtro-sede-salidas');
        const valorActual = sel.value;

        const resSedes = await apiFetch(`${API}/auth/sedes`);
        if (resSedes) {
            const sedes = await resSedes.json();
            sel.innerHTML = '<option value="">— Todas las sedes —</option>';
            sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                `<option value="${s.id}">${s.nombre} — ${s.ciudad}</option>`
            ));
            sel.style.display = 'block';
            sel.value = valorActual;
        }
    }

    renderizarSalidas(salidasCache);
    filtrarSalidas();
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
                        <button class="btn-accion danger" onclick="eliminarSalida(${s.id}, '${s.numero_documento}')">🗑️ Eliminar</button>
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
    const sedeSalida = parseInt(document.getElementById('sal-sede').value) || sedeActual;
    const urlProductos = usuario.rol === 'admin' && sedeSalida
        ? `${API}/productos/?sede_id=${sedeSalida}`
        : urlConSede(`${API}/productos/`);

    const res = await apiFetch(urlProductos);
    if (!res) return;
    productosCacheSalida = await res.json();
    if (catalogoModelos.length === 0 && catalogoMarcas.length === 0) {
        await cargarCatalogos();
    }

    const opciones = productosCacheSalida
        .map(p => `<option value="${p.id}" data-stock="${p.stock}" data-unidad="${p.unidad || 'UND'}">[${p.codigo||'—'}] ${p.nombre} (disp: ${p.stock})</option>`)
        .join('');

    const unidadesDisponibles = ['UND','MTS','KG','CAJA','ROLLO','LITRO'];
    const opcionesUnidad = unidadesDisponibles.map(u => `<option value="${u}">${u}</option>`).join('');

    const item = document.createElement('div');
    item.style.cssText = 'display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 70px 55px 30px;gap:6px;align-items:start';
    item.innerHTML = `
        <select class="select-producto" style="border:0.5px solid #c8d8ea;border-radius:8px;padding:6px 8px;font-size:12px;color:#0d2137;width:100%;min-width:0;height:32px">
            ${opciones}
        </select>
        ${crearComboHTML('modelo', 'Modelo')}
        ${crearComboHTML('marca', 'Marca')}
        <input type="text" placeholder="Serial"
               style="border:0.5px solid #c8d8ea;border-radius:8px;padding:6px 8px;font-size:12px;width:100%;min-width:0;height:32px;box-sizing:border-box">
        <select class="select-unidad" style="border:0.5px solid #c8d8ea;border-radius:8px;padding:6px 4px;font-size:12px;color:#0d2137;width:100%;min-width:0;height:32px">
            ${opcionesUnidad}
        </select>
        <input type="number" min="1" value="1"
               style="border:0.5px solid #c8d8ea;border-radius:8px;padding:6px 8px;font-size:12px;text-align:center;width:100%;min-width:0;height:32px;box-sizing:border-box">
        <button type="button"
                style="background:#fdecea;border:none;border-radius:6px;color:#c0392b;cursor:pointer;font-size:14px;width:30px;height:32px;flex-shrink:0"
                onclick="this.parentElement.remove()">✕</button>
    `;
    document.getElementById('sal-items').appendChild(item);
    item.querySelectorAll('.combo-wrap').forEach(activarCombo);

    const selectProducto = item.querySelector('.select-producto');
    const selectUnidad    = item.querySelector('.select-unidad');
    function autocompletarUnidad() {
        const opcion = selectProducto.options[selectProducto.selectedIndex];
        selectUnidad.value = opcion?.dataset.unidad || 'UND';
    }
    selectProducto.addEventListener('change', autocompletarUnidad);
    autocompletarUnidad();
}

async function guardarSalida(event) {
    event.preventDefault();

    const numero = document.getElementById('sal-numero').value;
    if (!numero) {
        alert('Escribe el Destino para generar el numero de documento');
        return;
    }

    const filas = document.getElementById('sal-items').querySelectorAll(':scope > div');
    if (filas.length === 0) {
        alert('Agrega al menos un producto');
        return;
    }

    const detalle = Array.from(filas).map(fila => {
        const selectProducto = fila.querySelector('.select-producto');
        const selectUnidad   = fila.querySelector('.select-unidad');
        const comboModelo    = fila.querySelector('[data-tipo="modelo"] .combo-input');
        const comboMarca     = fila.querySelector('[data-tipo="marca"] .combo-input');
        const inputSerial    = fila.querySelectorAll('input[type="text"]')[2];
        const inputCantidad  = fila.querySelector('input[type="number"]');
        return {
            producto_id: parseInt(selectProducto.value),
            unidad:      selectUnidad.value,
            modelo:      comboModelo.value,
            marca:       comboMarca.value,
            serial:      inputSerial ? inputSerial.value : '',
            cantidad:    parseInt(inputCantidad.value) || 1
        };
    });

    const datos = {
        numero_documento: numero,
        obra:             document.getElementById('sal-obra').value || 'Almacen',
        destino:          document.getElementById('sal-destino').value,
        observaciones:    document.getElementById('sal-observaciones').value,
        sede_id:          parseInt(document.getElementById('sal-sede').value) || sedeActual,
        detalle:          detalle
    };

    const res = await apiFetch(`${API}/salidas/`, {
        method: 'POST',
        body: JSON.stringify(datos)
    });

    if (!res) return;
    const resultado = await res.json();

    if (res.ok) {
        for (const item of detalle) {
            await guardarModeloEnCatalogo(item.modelo);
            await guardarMarcaEnCatalogo(item.marca);
        }
        await cargarCatalogos();
        cerrarModal('modal-salida');
        limpiarFormSalida();
        cargarSalidas();
        cargarProductos();
    } else {
        alert('Error: ' + resultado.error);
    }
}

function limpiarFormSalida() {
    document.getElementById('sal-numero').value        = '';
    document.getElementById('sal-fecha').value         = '';
    document.getElementById('sal-obra').value          = 'Almacen';
    document.getElementById('sal-destino').value       = '';
    document.getElementById('sal-observaciones').value = '';
    document.getElementById('sal-items').innerHTML     = '';
    document.getElementById('sal-sede').value = '';
    productosCacheSalida = [];
}

function verPDFSalida(id) {
    window.open(`${API}/pdf/salida/${id}?token=${token}`, '_blank');
}

async function eliminarSalida(id, numero) {
    if (!confirm(`Eliminar la salida "${numero}"?\n\nEsto devolvera el stock que se habia descontado.`)) return;
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

async function cargarItemsDeSalida() {
    const select      = document.getElementById('dev-salida');
    const salidaId    = select.value;
    const contenedor  = document.getElementById('dev-items');

    if (!salidaId) {
        contenedor.innerHTML = '<p style="font-size:12px;color:#6b8aab">Selecciona primero una salida arriba.</p>';
        document.getElementById('dev-origen').value = '';
        return;
    }

    const opcionElegida = select.options[select.selectedIndex];
    document.getElementById('dev-origen').value = opcionElegida.dataset.destino || '';
    generarNumeroDevolucion();

    const res   = await apiFetch(`${API}/devoluciones/salida/${salidaId}/items`);
    if (!res) return;
    const items = await res.json();

    if (items.length === 0) {
        contenedor.innerHTML = '<p style="font-size:12px;color:#6b8aab">Esta salida no tiene productos.</p>';
        return;
    }

    contenedor.innerHTML = items.map(item => `
        <div class="dev-item-fila" data-producto-id="${item.producto_id}"
             data-modelo="${item.modelo || ''}" data-marca="${item.marca || ''}"
             data-serial="${item.serial || ''}" data-unidad="${item.unidad || 'UND'}"
             style="display:grid;grid-template-columns:24px 2fr 1fr 70px;gap:8px;align-items:center;
                    padding:8px;border:0.5px solid #dce6f0;border-radius:8px">
            <input type="checkbox" class="dev-check" style="width:16px;height:16px">
            <div>
                <strong style="font-size:12.5px">${item.nombre}</strong>
                <div style="font-size:11px;color:#6b8aab">
                    ${item.modelo || '—'} ${item.marca ? '· ' + item.marca : ''} ${item.serial ? '· Serial: ' + item.serial : ''}
                </div>
            </div>
            <div style="font-size:11px;color:#6b8aab">Salio: ${item.cantidad} ${item.unidad || ''}</div>
            <input type="number" class="dev-cantidad" min="1" max="${item.cantidad}" value="${item.cantidad}"
                   style="border:0.5px solid #c8d8ea;border-radius:8px;padding:6px;font-size:12px;text-align:center">
        </div>
    `).join('');
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

async function cargarDevoluciones() {
    const res = await apiFetch(urlConSede(`${API}/devoluciones/`));
    if (!res) return;
    devolucionesCache = await res.json();

    if (usuario.rol === 'admin') {
        const sel = document.getElementById('filtro-sede-devoluciones');
        const valorActual = sel.value;
        const resSedes = await apiFetch(`${API}/auth/sedes`);
        if (resSedes) {
            const sedes = await resSedes.json();
            sel.innerHTML = '<option value="">— Todas las sedes —</option>';
            sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                `<option value="${s.id}">${s.nombre} — ${s.ciudad}</option>`
            ));
            sel.style.display = 'block';
            sel.value = valorActual;
        }
    }

    renderizarDevoluciones(devolucionesCache);
    filtrarDevoluciones();
}

function renderizarDevoluciones(devoluciones) {
    document.getElementById('subtitulo-devoluciones').textContent =
        `${devoluciones.length} devoluciones registradas`;

    const tbody = document.getElementById('tabla-devoluciones');
    tbody.innerHTML = '';

    if (devoluciones.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#6b8aab;padding:2rem">Sin devoluciones registradas</td></tr>';
        return;
    }

    devoluciones.forEach(d => {
        const fecha = new Date(d.fecha).toLocaleDateString('es-CO', {
            day: '2-digit', month: '2-digit', year: 'numeric'
        });
        tbody.insertAdjacentHTML('beforeend', `
            <tr>
                <td><strong>${d.numero_documento}</strong></td>
                <td>${d.salida_numero || '—'}</td>
                <td>${d.origen || '—'}</td>
                <td>${d.motivo || '—'}</td>
                <td>${d.total_items} producto(s)</td>
                <td><span style="font-size:11px;color:#4a6080">${d.sede_nombre || '—'}</span></td>
                <td>${fecha}</td>
                <td>
                    <div class="acciones">
                        <button class="btn-accion" onclick="verPDFDevolucion(${d.id})">📄 PDF</button>
                        <button class="btn-accion danger" onclick="eliminarDevolucion(${d.id}, '${d.numero_documento}')">🗑️ Eliminar</button>
                    </div>
                </td>
            </tr>
        `);
    });
}

function filtrarDevoluciones() {
    const texto = document.getElementById('buscar-devoluciones').value.trim().toLowerCase();
    const sedeFiltro = document.getElementById('filtro-sede-devoluciones')?.value;

    let filtradas = devolucionesCache;

    if (texto) {
        filtradas = filtradas.filter(d =>
            (d.numero_documento || '').toLowerCase().includes(texto) ||
            (d.origen || '').toLowerCase().includes(texto) ||
            (d.motivo || '').toLowerCase().includes(texto)
        );
    }

    if (sedeFiltro) {
        filtradas = filtradas.filter(d => String(d.sede_id) === sedeFiltro);
    }

    renderizarDevoluciones(filtradas);
}

async function guardarDevolucion(event) {
    event.preventDefault();

    const salidaId = document.getElementById('dev-salida').value;
    if (!salidaId) {
        alert('Selecciona la salida de la que esta regresando la mercancia');
        return;
    }

    const numero = document.getElementById('dev-numero').value;
    if (!numero) {
        alert('No se pudo generar el numero de documento. Verifica fecha y salida.');
        return;
    }

    const filas = document.querySelectorAll('.dev-item-fila');
    const detalle = [];
    filas.forEach(fila => {
        const check = fila.querySelector('.dev-check');
        if (!check.checked) return;
        const cantidad = fila.querySelector('.dev-cantidad');
        detalle.push({
            producto_id: parseInt(fila.dataset.productoId),
            cantidad:    parseInt(cantidad.value) || 1,
            modelo:      fila.dataset.modelo,
            marca:       fila.dataset.marca,
            serial:      fila.dataset.serial,
            unidad:      fila.dataset.unidad
        });
    });

    if (detalle.length === 0) {
        alert('Marca al menos un producto que este regresando');
        return;
    }

    const datos = {
        numero_documento: numero,
        salida_id:         parseInt(salidaId),
        origen:            document.getElementById('dev-origen').value,
        destino:           'Almacen',
        motivo:            document.getElementById('dev-motivo').value,
        observaciones:     document.getElementById('dev-observaciones').value,
        sede_id:          parseInt(document.getElementById('dev-sede').value) || sedeActual,
        detalle:           detalle
    };

    const res = await apiFetch(`${API}/devoluciones/`, {
        method: 'POST',
        body: JSON.stringify(datos)
    });

    if (!res) return;
    const resultado = await res.json();

    if (res.ok) {
        cerrarModal('modal-devolucion');
        limpiarFormDevolucion();
        cargarDevoluciones();
        cargarProductos();
    } else {
        alert('Error: ' + resultado.error);
    }
}

function verPDFDevolucion(id) {
    window.open(`${API}/pdf/devolucion/${id}?token=${token}`, '_blank');
}

async function eliminarDevolucion(id, numero) {
    if (!confirm(`Eliminar la devolucion "${numero}"?\n\nEsto revertira el stock que se habia sumado.`)) return;
    await apiFetch(`${API}/devoluciones/${id}`, { method: 'DELETE' });
    cargarDevoluciones();
    cargarProductos();
}

function limpiarFormDevolucion() {
    document.getElementById('dev-numero').value        = '';
    document.getElementById('dev-fecha').value         = '';
    document.getElementById('dev-salida').value        = '';
    document.getElementById('dev-origen').value        = '';
    document.getElementById('dev-motivo').value        = 'No se uso';
    document.getElementById('dev-observaciones').value = '';
    document.getElementById('dev-sede').value = '';
    document.getElementById('dev-items').innerHTML     =
        '<p style="font-size:12px;color:#6b8aab">Selecciona primero una salida arriba.</p>';
}

// ══ INICIO ══════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    inicializarSelectorSede();
    cargarProductos();
    cargarCatalogos();

    if (usuario.rol !== 'admin') {
        document.body.classList.add('rol-consulta');
    }

    const nom = usuario.nombre || 'Usuario';
    document.getElementById('nombre-usuario').textContent = nom;
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
        const rolTexto  = u.rol === 'admin' ? 'Administrador' : u.rol === 'sede' ? 'Almacenista' : 'Consulta';
        const rolColor  = u.rol === 'admin' ? '#1a6fc4' : u.rol === 'sede' ? '#1a7a4a' : '#6b8aab';
        const rolBg     = u.rol === 'admin' ? '#e8f0fb' : u.rol === 'sede' ? '#e6f4ec' : '#f0f4f8';
        const estadoBadge = u.activo
            ? '<span class="badge badge-ok">Activo</span>'
            : '<span class="badge badge-agotado">Inactivo</span>';

        tbody.insertAdjacentHTML('beforeend', `
            <tr>
                <td><strong>${u.nombre}</strong></td>
                <td style="color:#6b8aab;font-size:12px">${u.correo}</td>
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
            `<option value="${s.id}">${s.nombre} — ${s.ciudad}</option>`
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
            `<option value="${s.id}" ${s.id === u.sede_id ? 'selected' : ''}>${s.nombre} — ${s.ciudad}</option>`
        );
    });

    document.getElementById('modal-usuario-titulo').textContent = 'Editar usuario';
    document.getElementById('usr-id').value     = u.id;
    document.getElementById('usr-nombre').value = u.nombre;
    document.getElementById('usr-correo').value = u.correo;
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
    if (!confirm(`¿${accion.charAt(0).toUpperCase() + accion.slice(1)} al usuario "${nombre}"?`)) return;

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

async function cargarPuntos() {
    // Carga sedes en filtro si es admin
    if (usuario.rol === 'admin') {
        const sel = document.getElementById('filtro-sede-consolidado');
        const valorActual = sel.value;
        const resSedes = await apiFetch(`${API}/auth/sedes`);
        if (resSedes) {
            const sedes = await resSedes.json();
            sel.innerHTML = '<option value="">— Todas las sedes —</option>';
            sedes.forEach(s => sel.insertAdjacentHTML('beforeend',
                `<option value="${s.id}">${s.nombre} — ${s.ciudad}</option>`
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

    const select = document.getElementById('selector-punto');
    const valorActual = select.value;
    select.innerHTML = '<option value="">— Selecciona un punto —</option>';
    puntos.forEach(p => {
        const sede = p.sede_nombre ? ` (${p.sede_nombre})` : '';
        select.insertAdjacentHTML('beforeend',
            `<option value="${p.destino}">${p.destino}${sede} — ${p.total_salidas} salida(s)</option>`
        );
    });
    select.value = valorActual;

    document.getElementById('subtitulo-consolidado').textContent =
        `${puntos.length} puntos con movimientos`;
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

    // SALIDAS
    html += `<h3 style="font-size:13px;color:#0d2137;margin:1rem 0 0.5rem">📤 Salidas hacia "${destino}"</h3>`;

    if (data.salidas.length === 0) {
        html += '<p style="font-size:12px;color:#6b8aab;margin-bottom:1rem">Sin salidas registradas.</p>';
    } else {
        data.salidas.forEach(s => {
            const fecha = new Date(s.fecha).toLocaleDateString('es-CO', {day:'2-digit',month:'2-digit',year:'numeric'});
            html += `
                <div style="background:white;border:0.5px solid #dce6f0;border-radius:10px;padding:12px 16px;margin-bottom:10px">
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                        <strong style="font-size:13px;color:#0d2137">${s.numero_documento}</strong>
                        <span style="font-size:11px;color:#6b8aab">${fecha}${s.sede_nombre ? ' · ' + s.sede_nombre : ''}</span>
                    </div>
                    <table style="width:100%;border-collapse:collapse">
                        <thead>
                            <tr>
                                <th style="font-size:10px;color:#6b8aab;text-align:left;padding:4px 8px;background:#f7f9fc">Producto</th>
                                <th style="font-size:10px;color:#6b8aab;text-align:left;padding:4px 8px;background:#f7f9fc">Modelo</th>
                                <th style="font-size:10px;color:#6b8aab;text-align:left;padding:4px 8px;background:#f7f9fc">Serial</th>
                                <th style="font-size:10px;color:#6b8aab;text-align:right;padding:4px 8px;background:#f7f9fc">Cant.</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${s.detalle.map(d => `
                                <tr>
                                    <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8">${d.nombre}</td>
                                    <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;color:#6b8aab">${d.modelo || '—'}</td>
                                    <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;color:#6b8aab">${d.serial || '—'}</td>
                                    <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;text-align:right">${d.cantidad} ${d.unidad}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        });
    }

    // DEVOLUCIONES
    html += `<h3 style="font-size:13px;color:#0d2137;margin:1.5rem 0 0.5rem">🔄 Devoluciones desde "${destino}"</h3>`;

    if (data.devoluciones.length === 0) {
        html += '<p style="font-size:12px;color:#6b8aab">Sin devoluciones registradas.</p>';
    } else {
        data.devoluciones.forEach(d => {
            const fecha = new Date(d.fecha).toLocaleDateString('es-CO', {day:'2-digit',month:'2-digit',year:'numeric'});
            html += `
                <div style="background:white;border:0.5px solid #dce6f0;border-radius:10px;padding:12px 16px;margin-bottom:10px">
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                        <strong style="font-size:13px;color:#0d2137">${d.numero_documento}</strong>
                        <span style="font-size:11px;color:#6b8aab">${fecha}${d.sede_nombre ? ' · ' + d.sede_nombre : ''}</span>
                    </div>
                    <div style="font-size:11px;color:#6b8aab;margin-bottom:8px">
                        Motivo: ${d.motivo || '—'} · Salida origen: ${d.salida_numero || '—'}
                    </div>
                    <table style="width:100%;border-collapse:collapse">
                        <thead>
                            <tr>
                                <th style="font-size:10px;color:#6b8aab;text-align:left;padding:4px 8px;background:#f7f9fc">Producto</th>
                                <th style="font-size:10px;color:#6b8aab;text-align:left;padding:4px 8px;background:#f7f9fc">Modelo</th>
                                <th style="font-size:10px;color:#6b8aab;text-align:left;padding:4px 8px;background:#f7f9fc">Serial</th>
                                <th style="font-size:10px;color:#6b8aab;text-align:right;padding:4px 8px;background:#f7f9fc">Cant.</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${d.detalle.map(item => `
                                <tr>
                                    <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8">${item.nombre}</td>
                                    <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;color:#6b8aab">${item.modelo || '—'}</td>
                                    <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;color:#6b8aab">${item.serial || '—'}</td>
                                    <td style="font-size:12px;padding:4px 8px;border-top:0.5px solid #f0f4f8;text-align:right">${item.cantidad} ${item.unidad}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        });
    }

    const pdfUrl = (document.getElementById('filtro-sede-consolidado')?.value)
    ? `${API}/pdf/consolidado?destino=${encodeURIComponent(destino)}&sede_id=${document.getElementById('filtro-sede-consolidado').value}&token=${token}`
    : `${API}/pdf/consolidado?destino=${encodeURIComponent(destino)}&token=${token}`;

    html = `<div style="margin-bottom:1rem">
        <button onclick="descargarPDFConsolidado('${destino}')" class="btn-primario">📄 Exportar PDF</button>
    </div>` + html;

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