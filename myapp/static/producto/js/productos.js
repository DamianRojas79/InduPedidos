document.addEventListener('DOMContentLoaded', () => {
    const storageKey = 'indupedidos-pedido';
    const productCards = [...document.querySelectorAll('.product-item')];
    const filters = [...document.querySelectorAll('.category-filter')];
    const resultCount = document.querySelector('#resultado-productos');
    const emptyResults = document.querySelector('#sin-resultados');
    const orderList = document.querySelector('#lista-pedido');
    const orderCount = document.querySelector('#cantidad-pedido');
    const orderTotal = document.querySelector('#total-pedido');
    const clearOrder = document.querySelector('#vaciar-pedido');
    const toastElement = document.querySelector('#producto-toast');
    const currency = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' });

    let order = [];
    try {
        const savedOrder = JSON.parse(localStorage.getItem(storageKey));
        order = Array.isArray(savedOrder) ? savedOrder : [];
    } catch (_error) {
        order = [];
    }

    const saveOrder = () => localStorage.setItem(storageKey, JSON.stringify(order));

    const renderOrder = () => {
        const units = order.reduce((total, item) => total + item.quantity, 0);
        const total = order.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        if (orderCount) orderCount.textContent = units;
        if (orderTotal) orderTotal.textContent = currency.format(total);
        if (clearOrder) clearOrder.disabled = order.length === 0;

        if (!orderList) return;
        if (order.length === 0) {
            orderList.innerHTML = '<div class="order-empty"><i class="bi bi-bag"></i><p class="mt-2 mb-0">Tu pedido está vacío.</p></div>';
            return;
        }

        orderList.innerHTML = order.map((item) => {
            const options = [
                item.color ? `Color: ${escapeHtml(item.color)}` : '',
                item.size ? `Talle: ${escapeHtml(item.size)}` : '',
            ].filter(Boolean).join(' · ');

            return `
            <div class="order-item" data-order-id="${escapeHtml(item.lineId || item.id)}">
                <div>
                    <div class="order-item-name">${escapeHtml(item.name)}</div>
                    ${options ? `<div class="order-item-options">${options}</div>` : ''}
                    <div class="order-item-price">${currency.format(item.price)}</div>
                </div>
                <div class="quantity-control" aria-label="Cantidad de ${escapeHtml(item.name)}">
                    <button type="button" data-action="decrease" aria-label="Quitar uno">−</button>
                    <span>${item.quantity}</span>
                    <button type="button" data-action="increase" aria-label="Agregar uno">+</button>
                </div>
                <button class="remove-item" type="button" data-action="remove" aria-label="Eliminar ${escapeHtml(item.name)}">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;
        }).join('');
    };

    function escapeHtml(value) {
        const element = document.createElement('div');
        element.textContent = value;
        return element.innerHTML;
    }

    filters.forEach((filter) => {
        filter.addEventListener('click', () => {
            const selected = filter.dataset.category;
            let visible = 0;
            filters.forEach((item) => item.classList.toggle('active', item === filter));
            productCards.forEach((card) => {
                const show = selected === 'todos' || card.dataset.category === selected;
                card.classList.toggle('d-none', !show);
                if (show) visible += 1;
            });
            if (resultCount) resultCount.textContent = `${visible} ${visible === 1 ? 'producto' : 'productos'}`;
            if (emptyResults) emptyResults.classList.toggle('d-none', visible !== 0);
        });
    });

    document.querySelectorAll('.option-button').forEach((button) => {
        button.addEventListener('click', () => {
            const group = button.closest('[data-option-group]');
            group.querySelectorAll('.option-button').forEach((option) => {
                const selected = option === button;
                option.classList.toggle('active', selected);
                option.setAttribute('aria-pressed', selected.toString());
            });
            group.classList.remove('has-error');
            const error = button.closest('.product-options').querySelector('.option-error');
            error.textContent = '';
        });
    });

    document.querySelectorAll('.add-product').forEach((button) => {
        button.addEventListener('click', () => {
            const id = button.dataset.productId;
            const card = button.closest('.product-card');
            const optionGroups = [...card.querySelectorAll('[data-option-group]')];
            const missingGroups = optionGroups.filter((group) => !group.querySelector('.option-button.active'));

            optionGroups.forEach((group) => group.classList.toggle('has-error', missingGroups.includes(group)));
            const error = card.querySelector('.option-error');
            if (missingGroups.length > 0) {
                const labels = missingGroups.map((group) => group.dataset.optionGroup === 'size' ? 'talle' : 'color');
                error.textContent = `Elegí ${labels.join(' y ')} para continuar.`;
                missingGroups[0].querySelector('.option-button').focus();
                return;
            }

            const selectedColor = card.querySelector('[data-option-group="color"] .option-button.active')?.dataset.optionValue || '';
            const selectedSize = card.querySelector('[data-option-group="size"] .option-button.active')?.dataset.optionValue || '';
            const lineId = [id, selectedColor, selectedSize].join('|');
            const existing = order.find((item) => (item.lineId || item.id) === lineId);
            if (existing) {
                existing.quantity += 1;
            } else {
                order.push({
                    id,
                    lineId,
                    name: button.dataset.productName,
                    price: Number(button.dataset.productPrice),
                    color: selectedColor,
                    size: selectedSize,
                    quantity: 1,
                });
            }
            saveOrder();
            renderOrder();
            if (window.bootstrap && toastElement) bootstrap.Toast.getOrCreateInstance(toastElement).show();
        });
    });

    orderList?.addEventListener('click', (event) => {
        const button = event.target.closest('[data-action]');
        const row = event.target.closest('[data-order-id]');
        if (!button || !row) return;
        const item = order.find((product) => (product.lineId || product.id) === row.dataset.orderId);
        if (!item) return;
        if (button.dataset.action === 'increase') item.quantity += 1;
        if (button.dataset.action === 'decrease') item.quantity -= 1;
        if (button.dataset.action === 'remove' || item.quantity <= 0) {
            order = order.filter((product) => (product.lineId || product.id) !== (item.lineId || item.id));
        }
        saveOrder();
        renderOrder();
    });

    clearOrder?.addEventListener('click', () => {
        order = [];
        saveOrder();
        renderOrder();
    });

    renderOrder();
});
