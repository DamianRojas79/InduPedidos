(() => {
    const formulario = document.getElementById('filtros-pedidos');
    const filtros = [...formulario.querySelectorAll('[name="filtro"]')];
    function iniciarCombo(tipo, plural) {
        const grupo = document.getElementById(`filtro-${tipo}`);
        const seleccion = document.getElementById(`id_${tipo}`);
        const combo = document.getElementById(`combo-${tipo}`);
        const entrada = document.getElementById(`${tipo}-autocompletar`);
        const boton = document.getElementById(`abrir-${plural}`);
        const panel = document.getElementById(`opciones-${plural}`);
        const lista = document.getElementById(`lista-${plural}`);
        const sinResultados = document.getElementById(`${plural}-sin-resultados`);
        const opciones = [...seleccion.options].filter(opcion => opcion.value).map(opcion => ({
            id: opcion.value, nombre: opcion.textContent.trim()
        }));
        const normalizar = texto => texto.trim().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es');
        let visibles = [];
        let activa = -1;

        // El select conserva el ID enviado al servidor y sirve también sin JavaScript.
        entrada.value = opciones.find(opcion => opcion.id === seleccion.value)?.nombre || '';
        seleccion.hidden = true;
        combo.hidden = false;
        seleccion.disabled = entrada.disabled = boton.disabled = grupo.hidden;
        document.getElementById(`etiqueta-${tipo}`).htmlFor = entrada.id;

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
                elemento.id = `${tipo}-opcion-${opcion.id}`;
                elemento.dataset.id = opcion.id;
                elemento.setAttribute('role', 'option');
                elemento.setAttribute('aria-selected', String(opcion.id === seleccion.value));
                elemento.textContent = opcion.nombre;
                return elemento;
            }));
            activa = -1;
            entrada.removeAttribute('aria-activedescendant');
            sinResultados.hidden = visibles.length !== 0;
            panel.hidden = false;
            entrada.setAttribute('aria-expanded', 'true');
        }

        function actualizarSeleccion() {
            const nombre = entrada.value.trim();
            const exacta = opciones.find(opcion => opcion.nombre === nombre);
            const coincidencias = opciones.filter(opcion => normalizar(opcion.nombre) === normalizar(nombre));
            const seleccionada = exacta || (coincidencias.length === 1 ? coincidencias[0] : null);
            seleccion.value = seleccionada?.id || '';
            entrada.setCustomValidity(nombre && !seleccionada ? `Seleccioná un ${tipo} de la lista.` : '');
        }

        function elegir(opcion) {
            seleccion.value = opcion.id;
            entrada.value = opcion.nombre;
            entrada.setCustomValidity('');
            cerrarLista();
            formulario.requestSubmit();
        }

        entrada.addEventListener('focus', () => mostrarLista(!seleccion.value));
        entrada.addEventListener('input', () => {
            actualizarSeleccion();
            mostrarLista(true);
        });
        entrada.addEventListener('keydown', evento => {
            if (evento.key === 'ArrowDown' || evento.key === 'ArrowUp') {
                evento.preventDefault();
                if (panel.hidden) mostrarLista(!seleccion.value);
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
        return () => {
            grupo.hidden = !filtros.some(filtro => filtro.checked && filtro.value === tipo);
            seleccion.disabled = entrada.disabled = boton.disabled = grupo.hidden;
            cerrarLista();
        };
    }

    const actualizarCombos = [iniciarCombo('cliente', 'clientes'), iniciarCombo('proveedor', 'proveedores')];
    filtros.forEach(filtro => {
        filtro.addEventListener('change', () => {
            filtros.forEach(opcion => { opcion.checked = opcion === filtro; });
            actualizarCombos.forEach(actualizar => actualizar());
            formulario.requestSubmit();
        });
    });
    document.getElementById('id_periodo').addEventListener('change', () => formulario.requestSubmit());
})();
