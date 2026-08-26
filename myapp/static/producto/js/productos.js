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
        orderCount.textContent = units;
        orderTotal.textContent = currency.format(total);
        clearOrder.disabled = order.length === 0;

        if (order.length === 0) {
            orderList.innerHTML = '<div class="order-empty"><i class="bi bi-bag"></i><p class="mt-2 mb-0">Tu pedido está vacío.</p></div>';
            return;
        }

        orderList.innerHTML = order.map((item) => `
            <div class="order-item" data-order-id="${item.id}">
                <div>
                    <div class="order-item-name">${escapeHtml(item.name)}</div>
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
        `).join('');
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
            resultCount.textContent = `${visible} ${visible === 1 ? 'producto' : 'productos'}`;
            emptyResults.classList.toggle('d-none', visible !== 0);
        });
    });

    document.querySelectorAll('.add-product').forEach((button) => {
        button.addEventListener('click', () => {
            const id = button.dataset.productId;
            const existing = order.find((item) => item.id === id);
            if (existing) {
                existing.quantity += 1;
            } else {
                order.push({
                    id,
                    name: button.dataset.productName,
                    price: Number(button.dataset.productPrice),
                    quantity: 1,
                });
            }
            saveOrder();
            renderOrder();
            if (window.bootstrap && toastElement) bootstrap.Toast.getOrCreateInstance(toastElement).show();
        });
    });

    orderList.addEventListener('click', (event) => {
        const button = event.target.closest('[data-action]');
        const row = event.target.closest('[data-order-id]');
        if (!button || !row) return;
        const item = order.find((product) => product.id === row.dataset.orderId);
        if (!item) return;
        if (button.dataset.action === 'increase') item.quantity += 1;
        if (button.dataset.action === 'decrease') item.quantity -= 1;
        if (button.dataset.action === 'remove' || item.quantity <= 0) {
            order = order.filter((product) => product.id !== item.id);
        }
        saveOrder();
        renderOrder();
    });

    clearOrder.addEventListener('click', () => {
        order = [];
        saveOrder();
        renderOrder();
    });

    renderOrder();
});
