let currentPage = 1;
const PAGE_SIZE = 20;

function onProgressUpdate() {
    loadAnime();
}

async function loadFilters() {
    const [genres, years] = await Promise.all([
        apiGet('/genres'),
        apiGet('/years'),
    ]);

    const genreSelect = document.getElementById('genre-filter');
    genres.forEach((g) => {
        const opt = document.createElement('option');
        opt.value = g;
        opt.textContent = g;
        genreSelect.appendChild(opt);
    });

    const yearSelect = document.getElementById('year-filter');
    years.forEach((y) => {
        const opt = document.createElement('option');
        opt.value = y;
        opt.textContent = y + '年';
        yearSelect.appendChild(opt);
    });
}

function getFilters() {
    return {
        status: document.getElementById('status-filter').value || undefined,
        genre: document.getElementById('genre-filter').value || undefined,
        year: document.getElementById('year-filter').value || undefined,
        search: document.getElementById('search-input').value || undefined,
        sort_by: document.getElementById('sort-filter').value || 'updated_at',
        order: document.getElementById('sort-filter').value === 'title' ? 'asc' : 'desc',
        page: currentPage,
        page_size: PAGE_SIZE,
    };
}

function updateURL() {
    const params = new URLSearchParams();
    const filters = getFilters();
    Object.entries(filters).forEach(([k, v]) => {
        if (v !== undefined && v !== '' && v !== null) {
            params.set(k, v);
        }
    });
    history.replaceState(null, '', `/list?${params.toString()}`);
}

async function loadAnime() {
    const grid = document.getElementById('anime-grid');
    const paginationEl = document.getElementById('pagination');
    const resultInfo = document.getElementById('result-info');

    grid.innerHTML = '<div class="loading-spinner" style="grid-column:1/-1"></div>';
    paginationEl.innerHTML = '';

    try {
        const filters = getFilters();
        updateURL();
        const data = await apiGet('/anime', filters);

        grid.innerHTML = '';
        resultInfo.textContent = `共 ${data.total} 部番剧`;

        if (data.items.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1">
                    <div class="icon">🔍</div>
                    <p>没有找到匹配的番剧</p>
                </div>`;
            return;
        }

        data.items.forEach((anime) => {
            grid.appendChild(createAnimeCard(anime, true));
        });

        const pagination = createPagination(data.total, data.page, data.page_size, (page) => {
            currentPage = page;
            loadAnime();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
        paginationEl.appendChild(pagination);
    } catch (err) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1">
                <div class="icon">❌</div>
                <p>加载失败: ${err.message}</p>
            </div>`;
    }
}

function readURLParams() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('status')) document.getElementById('status-filter').value = params.get('status');
    if (params.get('genre')) document.getElementById('genre-filter').value = params.get('genre');
    if (params.get('year')) document.getElementById('year-filter').value = params.get('year');
    if (params.get('search')) document.getElementById('search-input').value = params.get('search');
    if (params.get('sort_by')) document.getElementById('sort-filter').value = params.get('sort_by');
    if (params.get('page')) currentPage = parseInt(params.get('page')) || 1;
}

document.addEventListener('DOMContentLoaded', async () => {
    await loadFilters();
    readURLParams();

    document.getElementById('status-filter').addEventListener('change', () => { currentPage = 1; loadAnime(); });
    document.getElementById('genre-filter').addEventListener('change', () => { currentPage = 1; loadAnime(); });
    document.getElementById('year-filter').addEventListener('change', () => { currentPage = 1; loadAnime(); });
    document.getElementById('sort-filter').addEventListener('change', () => { currentPage = 1; loadAnime(); });

    let searchTimeout;
    document.getElementById('search-input').addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => { currentPage = 1; loadAnime(); }, 300);
    });

    loadAnime();
});
