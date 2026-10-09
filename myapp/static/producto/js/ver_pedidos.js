(() => {
    const formulario = document.getElementById('filtros-pedidos');
    const filtros = [...formulario.querySelectorAll('[name="filtro"]')];
    const grupoCliente = document.getElementById('filtro-cliente');
    const cliente = document.getElementById('id_cliente');
    const combo = document.getElementById('combo-cliente');
    const entrada = document.getElementById('cliente-autocompletar');
    const boton = document.getElementById('abrir-clientes');
    const panel = document.getElementById('opciones-clientes');
    const lista = document.getElementById('lista-clientes');
    const sinResultados = document.getElementById('clientes-sin-resultados');
    const opciones = [...cliente.options].filter(opcion => opcion.value).map(opcion => ({
        id: opcion.value, nombre: opcion.textContent.trim()
    }));
    const normalizar = texto => texto.trim().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es');
    let visibles = [];
    let activa = -1;

    // El select conserva el ID enviado al servidor y sirve también sin JavaScript.
    entrada.value = opciones.find(opcion => opcion.id === cliente.value)?.nombre || '';
    cliente.hidden = true;
    combo.hidden = false;
    entrada.disabled = grupoCliente.hidden;
    document.getElementById('etiqueta-cliente').htmlFor = entrada.id;

    function cerrarLista() {
        panel.hidden = true;
        entrada.setAttribute('aria-expanded', 'false');
        entrada.removeAttribute('aria-activedescendant');
        activa = -1;
    }

    function mostrarLista(filtrar = false) {
        const busqueda = normalizar(entrada.value);
        visibles = opciones.filter(opcion => !filtrar || normalizar(opcion.nombre).includes(busqueda));
        lista.replaceChildren(...visibles.map(opcion => {
            const elemento = document.createElement('li');
            elemento.id = `cliente-opcion-${opcion.id}`;
            elemento.dataset.id = opcion.id;
            elemento.setAttribute('role', 'option');
            elemento.setAttribute('aria-selected', String(opcion.id === cliente.value));
            elemento.textContent = opcion.nombre;
            return elemento;
        }));
        activa = -1;
        entrada.removeAttribute('aria-activedescendant');
        sinResultados.hidden = visibles.length !== 0;
        panel.hidden = false;
        entrada.setAttribute('aria-expanded', 'true');
    }

    function actualizarCliente() {
        const nombre = entrada.value.trim();
        const exacta = opciones.find(opcion => opcion.nombre === nombre);
        const coincidencias = opciones.filter(opcion => normalizar(opcion.nombre) === normalizar(nombre));
        const seleccionada = exacta || (coincidencias.length === 1 ? coincidencias[0] : null);
        cliente.value = seleccionada?.id || '';
        entrada.setCustomValidity(nombre && !seleccionada ? 'Seleccioná un cliente de la lista.' : '');
    }

    function elegir(opcion) {
        cliente.value = opcion.id;
        entrada.value = opcion.nombre;
        entrada.setCustomValidity('');
        cerrarLista();
        formulario.requestSubmit();
    }

    entrada.addEventListener('focus', () => mostrarLista(!cliente.value));
    entrada.addEventListener('input', () => {
        actualizarCliente();
        mostrarLista(true);
    });
    entrada.addEventListener('keydown', evento => {
        if (evento.key === 'ArrowDown' || evento.key === 'ArrowUp') {
            evento.preventDefault();
            if (panel.hidden) mostrarLista(!cliente.value);
            if (!visibles.length) return;
            const paso = evento.key === 'ArrowDown' ? 1 : -1;
            activa = activa < 0 ? (paso === 1 ? 0 : visibles.length - 1) : (activa + paso + visibles.length) % visibles.length;
            [...lista.children].forEach((elemento, indice) => elemento.classList.toggle('opcion-activa', indice === activa));
            const elemento = lista.children[activa];
            entrada.setAttribute('aria-activedescendant', elemento.id);
            elemento.scrollIntoView({block: 'nearest'});
        } else if (evento.key === 'Enter' && !panel.hidden && (activa >= 0 || visibles.length === 1)) {
            evento.preventDefault();
            elegir(visibles[activa >= 0 ? activa : 0]);
        } else if (evento.key === 'Escape') {
            evento.preventDefault();
            cerrarLista();
        }
    });
    boton.addEventListener('click', () => {
        const estabaAbierta = !panel.hidden;
        entrada.focus();
        if (estabaAbierta) cerrarLista();
        else mostrarLista();
    });
    // Mantiene el foco en el texto hasta seleccionar una opción con el mouse.
    lista.addEventListener('mousedown', evento => evento.preventDefault());
    lista.addEventListener('click', evento => {
        const elemento = evento.target.closest('[role="option"]');
        if (elemento) elegir(opciones.find(opcion => opcion.id === elemento.dataset.id));
    });
    combo.addEventListener('focusout', evento => {
        if (!combo.contains(evento.relatedTarget)) cerrarLista();
    });
    document.addEventListener('click', evento => {
        if (!combo.contains(evento.target)) cerrarLista();
    });
    filtros.forEach(filtro => {
        filtro.addEventListener('change', () => {
            filtros.forEach(opcion => { opcion.checked = opcion === filtro; });
            grupoCliente.hidden = filtro.value !== 'cliente';
            entrada.disabled = grupoCliente.hidden;
            cerrarLista();
            formulario.requestSubmit();
        });
    });
    document.getElementById('id_periodo').addEventListener('change', () => formulario.requestSubmit());
})();
