function onProgressUpdate() {
    loadStats();
    loadWatching();
    loadRecent();
}

async function loadStats() {
    const el = document.getElementById('greeting-stats');
    try {
        const currentYear = new Date().getFullYear();
        const [stats, yearly] = await Promise.all([
            apiGet('/stats'),
            apiGet(`/yearly/${currentYear}`)
        ]);
        el.innerHTML =
            `你今年已经看完 <span class="highlight">${yearly.count}</span> 部番剧，` +
            `共 <span class="highlight">${yearly.total_episodes}</span> 集。` +
            `收藏中共 <span class="highlight">${stats.total}</span> 部，` +
            `正在追 <span class="highlight">${stats.watching}</span> 部。`;
    } catch (err) {
        el.textContent = '统计数据加载失败';
    }
}

async function loadWatching() {
    const container = document.getElementById('watching-scroll');
    container.innerHTML = '';
    try {
        const data = await apiGet('/anime', { status: 'watching', sort_by: 'updated_at', order: 'desc', page_size: 20 });
        if (data.items.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>暂无正在追的番剧</p></div>';
            return;
        }
        data.items.forEach((anime) => {
            container.appendChild(createAnimeCard(anime, true));
        });
    } catch (err) {
        container.innerHTML = '<div class="empty-state"><p>加载失败</p></div>';
    }
}

async function loadRecent() {
    const grid = document.getElementById('recent-grid');
    grid.innerHTML = '';
    try {
        const items = await apiGet('/anime/recent/list', { limit: 10 });
        if (items.length === 0) {
            grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><p>暂无番剧数据</p></div>';
            return;
        }
        items.forEach((anime) => {
            grid.appendChild(createAnimeCard(anime));
        });
    } catch (err) {
        grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><p>加载失败</p></div>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadWatching();
    loadRecent();
});
