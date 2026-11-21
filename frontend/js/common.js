const STATUS_MAP = {
    watching: '追番中',
    completed: '已看完',
    planned: '计划看',
    dropped: '已弃',
};

const SEASON_MAP = {
    winter: '冬季',
    spring: '春季',
    summer: '夏季',
    fall: '秋季',
};

function getStatusText(status) {
    return STATUS_MAP[status] || status;
}

function getSeasonText(season) {
    return SEASON_MAP[season] || season || '';
}

function formatRating(rating) {
    if (!rating || rating === 0) return '';
    return rating.toFixed(1);
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function getProxiedUrl(url) {
    if (!url) return '/assets/default-cover.svg';
    if (url.startsWith('http')) return '/api/proxy/cover?url=' + encodeURIComponent(url);
    return url;
}

function createCoverImg(coverUrl, title) {
    const img = document.createElement('img');
    img.className = 'cover';
    img.src = getProxiedUrl(coverUrl);
    img.alt = title;
    img.loading = 'lazy';
    img.onerror = function () {
        this.src = '/assets/default-cover.svg';
    };
    return img;
}

function createAnimeCard(anime, showProgressBtn = false) {
    const card = document.createElement('div');
    card.className = 'anime-card';
    card.onclick = (e) => {
        if (e.target.closest('.progress-btn') || e.target.closest('.status-switch')) return;
        window.location.href = `/detail?id=${anime.id}`;
    };

    const coverWrap = document.createElement('div');
    coverWrap.className = 'cover-wrap';
    coverWrap.appendChild(createCoverImg(anime.cover_url, anime.title));

    if (showProgressBtn && anime.status === 'watching' && anime.episodes && anime.watched_episodes < anime.episodes) {
        const btn = document.createElement('button');
        btn.className = 'progress-btn';
        btn.textContent = '+1';
        btn.title = '进度 +1';
        btn.onclick = async (e) => {
            e.stopPropagation();
            btn.disabled = true;
            try {
                const updated = await apiPut(`/anime/${anime.id}/progress`);
                btn.closest('.anime-card').replaceWith(createAnimeCard(updated, showProgressBtn));
                showToast(`进度更新: ${updated.watched_episodes}/${updated.episodes || '?'}`);
                if (typeof onProgressUpdate === 'function') onProgressUpdate();
            } catch (err) {
                showToast('更新失败: ' + err.message, 'error');
                btn.disabled = false;
            }
        };
        coverWrap.appendChild(btn);
    }

    card.appendChild(coverWrap);

    const info = document.createElement('div');
    info.className = 'card-info';

    const title = document.createElement('div');
    title.className = 'card-title';
    title.textContent = anime.title;

    const meta = document.createElement('div');
    meta.className = 'card-meta';

    const left = document.createElement('div');
    left.className = 'card-meta-left';

    const statusSwitch = document.createElement('div');
    statusSwitch.className = 'status-switch';
    const dot = document.createElement('span');
    dot.className = `status-dot ${anime.status}`;
    statusSwitch.appendChild(dot);
    const statusLabel = document.createElement('span');
    statusLabel.className = 'status-label';
    statusLabel.textContent = getStatusText(anime.status);
    statusSwitch.appendChild(statusLabel);

    statusSwitch.onclick = (e) => {
        e.stopPropagation();
        closeAllStatusDropdowns();
        const rect = statusSwitch.getBoundingClientRect();
        showStatusDropdown(rect, anime, card, showProgressBtn);
    };
    left.appendChild(statusSwitch);

    if (anime.episodes) {
        const progress = document.createElement('span');
        progress.className = 'card-progress';
        progress.textContent = `${anime.watched_episodes || 0}/${anime.episodes}`;
        left.appendChild(progress);
    }

    meta.appendChild(left);

    if (anime.rating && anime.rating > 0) {
        const rating = document.createElement('span');
        rating.className = 'card-rating';
        rating.textContent = formatRating(anime.rating);
        meta.appendChild(rating);
    }

    info.appendChild(title);
    info.appendChild(meta);
    card.appendChild(info);

    return card;
}

// ─── Status Dropdown (shared) ───────────────────────────────

function closeAllStatusDropdowns() {
    document.querySelectorAll('.status-dropdown').forEach(el => {
        if (typeof el._cleanup === 'function') {
            el._cleanup();
        } else {
            el.remove();
        }
    });
}

function showStatusDropdown(rect, anime, card, showProgressBtn) {
    const dropdown = document.createElement('div');
    dropdown.className = 'status-dropdown';
    dropdown.style.position = 'fixed';
    dropdown.style.left = rect.left + 'px';
    dropdown.style.top = (rect.bottom + 4) + 'px';
    dropdown.style.zIndex = '9999';

    ['watching', 'completed', 'planned', 'dropped'].forEach(status => {
        const item = document.createElement('div');
        item.className = 'status-dropdown-item' + (status === anime.status ? ' active' : '');
        const itemDot = document.createElement('span');
        itemDot.className = `status-dot ${status}`;
        item.appendChild(itemDot);
        const itemText = document.createElement('span');
        itemText.textContent = getStatusText(status);
        item.appendChild(itemText);
        item.onclick = async (e) => {
            e.stopPropagation();
            if (status === anime.status) { closeAllStatusDropdowns(); return; }
            try {
                const updated = await apiPut(`/anime/${anime.id}/status`, { status: status });
                card.replaceWith(createAnimeCard(updated, showProgressBtn));
                showToast(`状态已更新为 ${getStatusText(status)}`);
                if (typeof onProgressUpdate === 'function') onProgressUpdate();
            } catch (err) {
                showToast('更新失败: ' + err.message, 'error');
            }
            closeAllStatusDropdowns();
        };
        dropdown.appendChild(item);
    });

    document.body.appendChild(dropdown);
    let closed = false;
    const closeHandler = () => {
        if (closed) return;
        closed = true;
        dropdown.remove();
        document.removeEventListener('click', closeHandler);
        window.removeEventListener('scroll', closeHandler, true);
        window.removeEventListener('wheel', closeHandler, true);
        window.removeEventListener('resize', closeHandler);
    };
    dropdown._cleanup = closeHandler;
    setTimeout(() => document.addEventListener('click', closeHandler), 0);
    window.addEventListener('scroll', closeHandler, true);
    window.addEventListener('wheel', closeHandler, true);
    window.addEventListener('resize', closeHandler);
}

function showDetailStatusDropdown(e, animeId) {
    e.stopPropagation();
    const existing = document.querySelector('.detail-status-dropdown');
    if (existing) { existing.remove(); return; }

    const badge = document.getElementById('detail-status-badge');
    const currentStatus = badge.className.replace('detail-status-badge ', '').trim();

    const dropdown = document.createElement('div');
    dropdown.className = 'detail-status-dropdown';

    ['watching', 'completed', 'planned', 'dropped'].forEach(status => {
        const item = document.createElement('div');
        item.className = 'status-dropdown-item' + (status === currentStatus ? ' active' : '');
        const itemDot = document.createElement('span');
        itemDot.className = `status-dot ${status}`;
        item.appendChild(itemDot);
        const itemText = document.createElement('span');
        itemText.textContent = getStatusText(status);
        item.appendChild(itemText);
        item.onclick = async (ev) => {
            ev.stopPropagation();
            if (status === currentStatus) { dropdown.remove(); return; }
            try {
                await apiPut(`/anime/${animeId}/status`, { status: status });
                showToast(`状态已更新为 ${getStatusText(status)}`);
                if (typeof loadDetail === 'function') loadDetail();
            } catch (err) {
                showToast('更新失败: ' + err.message, 'error');
            }
            dropdown.remove();
        };
        dropdown.appendChild(item);
    });

    badge.parentElement.appendChild(dropdown);
    setTimeout(() => document.addEventListener('click', function close() {
        dropdown.remove();
        document.removeEventListener('click', close);
    }), 0);
}

// ─── Toast ───────────────────────────────────────────────────

function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }
    // Dedup: skip if same message is already showing
    for (const existing of container.children) {
        if (existing.textContent === message) return;
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ─── Navbar ──────────────────────────────────────────────────

function initNavbar() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.navbar nav a').forEach((a) => {
        const href = a.getAttribute('href');
        if (href === currentPath) {
            a.classList.add('active');
        } else {
            a.classList.remove('active');
        }
    });
}

// ─── Pagination ──────────────────────────────────────────────

function createPagination(total, page, pageSize, onChange) {
    const container = document.createElement('div');
    container.className = 'pagination';
    const totalPages = Math.ceil(total / pageSize);
    if (totalPages <= 1) return container;

    const prevBtn = document.createElement('button');
    prevBtn.textContent = '上一页';
    prevBtn.disabled = page <= 1;
    prevBtn.onclick = () => onChange(page - 1);
    container.appendChild(prevBtn);

    const start = Math.max(1, page - 2);
    const end = Math.min(totalPages, page + 2);

    if (start > 1) {
        const btn = document.createElement('button');
        btn.textContent = '1';
        btn.onclick = () => onChange(1);
        container.appendChild(btn);
        if (start > 2) {
            const dots = document.createElement('span');
            dots.className = 'pagination-dots';
            dots.textContent = '...';
            container.appendChild(dots);
        }
    }

    for (let i = start; i <= end; i++) {
        const btn = document.createElement('button');
        btn.textContent = i;
        if (i === page) btn.classList.add('active');
        btn.onclick = () => onChange(i);
        container.appendChild(btn);
    }

    if (end < totalPages) {
        if (end < totalPages - 1) {
            const dots = document.createElement('span');
            dots.className = 'pagination-dots';
            dots.textContent = '...';
            container.appendChild(dots);
        }
        const btn = document.createElement('button');
        btn.textContent = totalPages;
        btn.onclick = () => onChange(totalPages);
        container.appendChild(btn);
    }

    const nextBtn = document.createElement('button');
    nextBtn.textContent = '下一页';
    nextBtn.disabled = page >= totalPages;
    nextBtn.onclick = () => onChange(page + 1);
    container.appendChild(nextBtn);

    return container;
}

document.addEventListener('DOMContentLoaded', initNavbar);
