document.addEventListener('DOMContentLoaded', () => {
    const productCards = [...document.querySelectorAll('.product-item')];
    const filters = [...document.querySelectorAll('.category-filter')];
    const resultCount = document.querySelector('#resultado-productos');
    const emptyResults = document.querySelector('#sin-resultados');
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

});
