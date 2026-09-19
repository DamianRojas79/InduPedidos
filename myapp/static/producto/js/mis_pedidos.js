(() => {
    const estado = document.getElementById('estado-planilla');
    const tabla = document.querySelector('.planilla-pedidos');
    let pendientes = Promise.resolve();
    let cantidadPendiente = 0;
    tabla.querySelectorAll('input:not([type="hidden"])').forEach(celda => {
        celda.dataset.guardado = celda.value;
        celda.addEventListener('keydown', evento => {
            if (evento.key === 'Enter') {
                evento.preventDefault();
                celda.blur();
            }
            if (evento.key === 'Escape') {
                celda.value = celda.dataset.guardado;
                celda.removeAttribute('aria-invalid');
                celda.blur();
            }
        });
        celda.addEventListener('change', () => {
            const valor = celda.value;
            const fila = celda.closest('[data-pedido]');
            cantidadPendiente++;
            estado.textContent = 'Guardando…';
            pendientes = pendientes.then(async () => {
                try {
                    const respuesta = await fetch(fila.dataset.url, {
                        method: 'POST',
                        headers: {'X-CSRFToken': fila.querySelector('[name="csrfmiddlewaretoken"]').value},
                        body: new URLSearchParams({campo: celda.name, valor})
                    });
                    if (respuesta.redirected) throw new Error('La sesión venció. Volvé a iniciar sesión para guardar.');
                    const datos = await respuesta.json();
                    if (!respuesta.ok) throw new Error(datos.error || 'No se pudo guardar el cambio.');
                    celda.dataset.guardado = datos.valor;
                    if (celda.value === valor) celda.value = datos.valor;
                    celda.removeAttribute('aria-invalid');
                    if (celda.name === 'numero') {
                        const cuerpo = fila.parentElement;
                        datos.orden.forEach((id, indice) => {
                            const actual = cuerpo.querySelector(`[data-pedido="${id}"]`);
                            cuerpo.append(actual);
                            const numero = actual.querySelector('[name="numero"]');
                            numero.value = String(indice + 1);
                            numero.dataset.guardado = numero.value;
                        });
                    }
                } catch (error) {
                    celda.setAttribute('aria-invalid', 'true');
                    estado.textContent = error.message || 'No se pudo guardar. Revisá la conexión y volvé a editar la celda.';
                } finally {
                    cantidadPendiente--;
                    if (!tabla.querySelector('[aria-invalid="true"]')) {
                        estado.textContent = cantidadPendiente ? 'Guardando…' : 'Cambios guardados.';
                    }
                }
            });
        });
    });
    tabla.querySelectorAll('form').forEach(formulario => {
        formulario.addEventListener('submit', async evento => {
            evento.preventDefault();
            await pendientes;
            if (tabla.querySelector('[aria-invalid="true"]')) {
                estado.textContent = 'Hay cambios sin guardar. Corregí las celdas marcadas o presioná Escape antes de eliminar.';
                return;
            }
            formulario.submit();
        });
    });
    window.addEventListener('beforeunload', evento => {
        if (cantidadPendiente || tabla.querySelector('[aria-invalid="true"]')) {
            evento.preventDefault();
            evento.returnValue = '';
        }
    });
})();
