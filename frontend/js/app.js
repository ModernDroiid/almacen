const API = 'http://localhost:5000/api';

// ══ NAVEGACIÓN ══════════════════════════════════════════════

function mostrarSeccion(nombre, btn) {
    document.querySelectorAll('.seccion').forEach(s => s.classList.remove('activa'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('sec-' + nombre).classList.add('activa');
    btn.classList.add('active');
    if (nombre === 'productos')     cargarProductos();
    if (nombre === 'entradas')      cargarEntradas();
    if (nombre === 'salidas')       cargarSalidas();
    if (nombre === 'devoluciones')  cargarDevoluciones();
    if (nombre === 'modelos')       cargarModelos();
    if (nombre === 'marcas')        cargarMarcas();
}

// ══ MODALES ═════════════════════════════════════════════════

function abrirModal(id) {
    document.getElementById(id).classList.add('visible');

    if (id === 'modal-entrada') {
        const hoy = new Date().toISOString().split('T')[0];
        document.getElementById('ent-fecha').value = hoy;
        generarNumeroEntrada();
    }
    if (id === 'modal-salida') {
        const hoy = new Date().toISOString().split('T')[0];
        document.getElementById('sal-fecha').value = hoy;
        generarNumeroSalida();
    }
    if (id === 'modal-devolucion') {
        const hoy = new Date().toISOString().split('T')[0];
        document.getElementById('dev-fecha').value = hoy;
        cargarSelectorSalidas();
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

document.querySelectorAll('.modal-fondo').forEach(fondo => {
    fondo.addEventListener('click', function(e) {
        if (e.target === this) cerrarModal(this.id);
    });
});

// ══ CATALOGOS ════════════════════════════════════════════════

let catalogoModelos = [];
let catalogoMarcas  = [];

async function cargarCatalogos() {
    const [resModelos, resMarcas] = await Promise.all([
        fetch(`${API}/catalogos/modelos`),
        fetch(`${API}/catalogos/marcas`)
    ]);
    catalogoModelos = await resModelos.json();
    catalogoMarcas  = await resMarcas.json();
}

async function guardarModeloEnCatalogo(nombre) {
    if (!nombre || !nombre.trim()) return;
    await fetch(`${API}/catalogos/modelos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre: nombre.trim() })
    });
}

async function guardarMarcaEnCatalogo(nombre) {
    if (!nombre || !nombre.trim()) return;
    await fetch(`${API}/catalogos/marcas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
    const res     = await fetch(`${API}/catalogos/modelos`);
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
    await fetch(url, {
        method: metodo,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre })
    });
    cerrarModal('modal-modelo');
    cargarModelos();
}

async function eliminarModelo(id, nombre) {
    if (!confirm(`Eliminar el modelo "${nombre}"?`)) return;
    await fetch(`${API}/catalogos/modelos/${id}`, { method: 'DELETE' });
    cargarModelos();
}

function limpiarFormModelo() {
    document.getElementById('modelo-id').value     = '';
    document.getElementById('modelo-nombre').value = '';
    document.getElementById('modal-modelo-titulo').textContent = 'Nuevo modelo';
}

// ══ MARCAS ════════════════════════════════════════════════════

async function cargarMarcas() {
    const res    = await fetch(`${API}/catalogos/marcas`);
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
    await fetch(url, {
        method: metodo,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre })
    });
    cerrarModal('modal-marca');
    cargarMarcas();
}

async function eliminarMarca(id, nombre) {
    if (!confirm(`Eliminar la marca "${nombre}"?`)) return;
    await fetch(`${API}/catalogos/marcas/${id}`, { method: 'DELETE' });
    cargarMarcas();
}

function limpiarFormMarca() {
    document.getElementById('marca-id').value     = '';
    document.getElementById('marca-nombre').value = '';
    document.getElementById('modal-marca-titulo').textContent = 'Nueva marca';
}

// ══ PRODUCTOS ═══════════════════════════════════════════════

async function cargarProductos() {
    const respuesta = await fetch(`${API}/productos/`);
    const productos = await respuesta.json();

    const total    = productos.length;
    // ✅ CORREGIDO: usar p.stock en vez de p.stock_minimo
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
        // ✅ CORREGIDO: usar p.stock en vez de p.stock_minimo para el badge
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
                <td><strong>${p.nombre}</strong><div class="sub">${p.descripcion || '—'}</div></td>
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
    const datos = {
        codigo:       document.getElementById('prod-codigo').value,
        nombre:       document.getElementById('prod-nombre').value,
        descripcion:  document.getElementById('prod-descripcion').value,
        unidad:       document.getElementById('prod-unidad').value,
        stock_minimo: parseInt(document.getElementById('prod-stock-minimo').value) || 0,
        stock:        parseInt(document.getElementById('prod-stock-minimo').value) || 0,
    };
    const url    = id ? `${API}/productos/${id}` : `${API}/productos/`;
    const metodo = id ? 'PUT' : 'POST';
    await fetch(url, {
        method: metodo,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(datos)
    });
    cerrarModal('modal-producto');
    cargarProductos();
}

async function editarProducto(id) {
    const res       = await fetch(`${API}/productos/`);
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
    await fetch(`${API}/productos/${id}`, { method: 'DELETE' });
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
}

// ══ ENTRADAS ════════════════════════════════════════════════

let productosCache = [];

async function generarNumeroEntrada() {
    const fecha = document.getElementById('ent-fecha').value;
    const obra  = document.getElementById('ent-obra').value.trim();
    if (!fecha || !obra) return;
    const base       = `ENT-${fecha}-${obra.toUpperCase().replace(/ /g, '-')}`;
    const res        = await fetch(`${API}/entradas/`);
    const entradas   = await res.json();
    const existentes = entradas.filter(e => e.numero_documento.startsWith(base));
    document.getElementById('ent-numero').value = `${base}-${existentes.length + 1}`;
}

let entradasCache = [];

async function cargarEntradas() {
    const res      = await fetch(`${API}/entradas/`);
    entradasCache  = await res.json();
    renderizarEntradas(entradasCache);
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
    if (!texto) {
        renderizarEntradas(entradasCache);
        return;
    }
    const filtradas = entradasCache.filter(e =>
        (e.numero_documento || '').toLowerCase().includes(texto) ||
        (e.obra || '').toLowerCase().includes(texto) ||
        (e.destino || '').toLowerCase().includes(texto)
    );
    renderizarEntradas(filtradas);
}

async function agregarItemEntrada() {
    if (productosCache.length === 0) {
        const res      = await fetch(`${API}/productos/`);
        productosCache = await res.json();
    }
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
        detalle:          detalle
    };

    const res = await fetch(`${API}/entradas/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(datos)
    });

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
    productosCache = [];
}

function verPDFEntrada(id) {
    window.open(`${API}/pdf/entrada/${id}`, '_blank');
}

async function eliminarEntrada(id, numero) {
    if (!confirm(`Eliminar la entrada "${numero}"?\n\nEsto revertira el stock que se sumo con esta entrada.`)) return;
    await fetch(`${API}/entradas/${id}`, { method: 'DELETE' });
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
    const res        = await fetch(`${API}/salidas/`);
    const salidas    = await res.json();
    const existentes = salidas.filter(s => s.numero_documento.startsWith(base));
    document.getElementById('sal-numero').value = `${base}-${existentes.length + 1}`;
}

let salidasCache = [];

async function cargarSalidas() {
    const res     = await fetch(`${API}/salidas/`);
    salidasCache  = await res.json();
    renderizarSalidas(salidasCache);
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
    if (!texto) {
        renderizarSalidas(salidasCache);
        return;
    }
    const filtradas = salidasCache.filter(s =>
        (s.numero_documento || '').toLowerCase().includes(texto) ||
        (s.obra || '').toLowerCase().includes(texto) ||
        (s.destino || '').toLowerCase().includes(texto)
    );
    renderizarSalidas(filtradas);
}

async function agregarItemSalida() {
    if (productosCacheSalida.length === 0) {
        const res            = await fetch(`${API}/productos/`);
        productosCacheSalida = await res.json();
    }
    if (catalogoModelos.length === 0 && catalogoMarcas.length === 0) {
        await cargarCatalogos();
    }

    // ✅ CORREGIDO: mostrar p.stock en vez de p.stock_minimo
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
        detalle:          detalle
    };

    const res = await fetch(`${API}/salidas/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(datos)
    });

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
    productosCacheSalida = [];
}

function verPDFSalida(id) {
    window.open(`${API}/pdf/salida/${id}`, '_blank');
}

async function eliminarSalida(id, numero) {
    if (!confirm(`Eliminar la salida "${numero}"?\n\nEsto devolvera el stock que se habia descontado.`)) return;
    await fetch(`${API}/salidas/${id}`, { method: 'DELETE' });
    cargarSalidas();
    cargarProductos();
}

// ══ DEVOLUCIONES ════════════════════════════════════════════

async function cargarSelectorSalidas() {
    const res     = await fetch(`${API}/devoluciones/salidas-disponibles`);
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

    const res   = await fetch(`${API}/devoluciones/salida/${salidaId}/items`);
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
    const res        = await fetch(`${API}/devoluciones/`);
    const devs       = await res.json();
    const existentes = devs.filter(d => d.numero_documento.startsWith(base));
    document.getElementById('dev-numero').value = `${base}-${existentes.length + 1}`;
}

async function cargarDevoluciones() {
    const res          = await fetch(`${API}/devoluciones/`);
    const devoluciones = await res.json();

    document.getElementById('subtitulo-devoluciones').textContent =
        `${devoluciones.length} devoluciones registradas`;

    const tbody = document.getElementById('tabla-devoluciones');
    tbody.innerHTML = '';

    if (devoluciones.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#6b8aab;padding:2rem">Sin devoluciones registradas</td></tr>';
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
        detalle:           detalle
    };

    const res = await fetch(`${API}/devoluciones/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(datos)
    });

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
    window.open(`${API}/pdf/devolucion/${id}`, '_blank');
}

async function eliminarDevolucion(id, numero) {
    if (!confirm(`Eliminar la devolucion "${numero}"?\n\nEsto revertira el stock que se habia sumado.`)) return;
    await fetch(`${API}/devoluciones/${id}`, { method: 'DELETE' });
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
    document.getElementById('dev-items').innerHTML     =
        '<p style="font-size:12px;color:#6b8aab">Selecciona primero una salida arriba.</p>';
}

// ══ INICIO ══════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    cargarProductos();
    cargarCatalogos();
});