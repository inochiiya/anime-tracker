async function loadDetail() {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    if (!id) {
        document.getElementById('detail-content').innerHTML = `
            <div class="empty-state">
                <div class="icon">?</div>
                <p>未指定番剧 ID</p>
            </div>`;
        return;
    }

    try {
        const results = await Promise.allSettled([
            apiGet(`/anime/${id}`),
            apiGet(`/anime/${id}/characters`),
            apiGet(`/anime/${id}/episodes`),
        ]);

        const anime = results[0].status === 'fulfilled' ? results[0].value : null;
        const characters = results[1].status === 'fulfilled' ? results[1].value : [];
        const episodeNotes = results[2].status === 'fulfilled' ? results[2].value : [];

        if (!anime) {
            document.getElementById('detail-content').innerHTML = `
                <div class="empty-state"><div class="icon">!</div><p>加载失败</p></div>`;
            return;
        }

        document.title = `${anime.title} - 追番收藏`;
        renderDetail(anime, characters, episodeNotes);
    } catch (err) {
        document.getElementById('detail-content').innerHTML = `
            <div class="empty-state"><div class="icon">!</div><p>加载失败: ${escapeHtml(err.message)}</p></div>`;
    }
}

function renderDetail(anime, characters, episodeNotes) {
    const genres = anime.genre ? anime.genre.split(',').map(g => g.trim()).filter(Boolean) : [];
    const tags = anime.personal_tags ? anime.personal_tags.split(',').map(t => t.trim()).filter(Boolean) : [];
    const progress = anime.episodes ? Math.round(((anime.watched_episodes || 0) / anime.episodes) * 100) : 0;
    const seasonText = anime.season && anime.year ? `${anime.year}年${getSeasonText(anime.season)}`
        : anime.year ? `${anime.year}年` : '';

    document.getElementById('detail-content').innerHTML = `
        <div class="detail-layout">
            <div class="detail-cover">
                <img src="${getProxiedUrl(anime.cover_url)}"
                     alt="${escapeHtml(anime.title)}"
                     onerror="this.src='${appPath('/assets/default-cover.svg')}'">
                ${anime.is_favorite ? '<div class="favorite-badge">&#10084; 最爱</div>' : ''}
            </div>
            <div class="detail-info">
                ${renderHeader(anime)}
                ${renderMeta(anime)}
                ${renderProgress(anime, progress)}
                ${renderTags(genres, tags)}
                ${renderGrid(anime, seasonText)}
                ${renderCharacters(characters)}
                ${renderSynopsis(anime)}
                ${renderNotes(anime)}
                ${renderEpisodeNotes(episodeNotes)}
                ${renderLink(anime)}
            </div>
        </div>`;
}

function renderHeader(anime) {
    return `<div>
        <h1 class="detail-title">${escapeHtml(anime.title)}</h1>
        ${anime.title_jp ? `<div class="detail-title-jp">${escapeHtml(anime.title_jp)}</div>` : ''}
    </div>`;
}

function renderMeta(anime) {
    return `<div class="detail-meta">
        <div class="detail-status-switch" onclick="showDetailStatusDropdown(event, ${anime.id})">
            <span class="detail-status-badge ${anime.status}" id="detail-status-badge">${getStatusText(anime.status)}</span>
        </div>
        ${anime.rating > 0 ? `<div class="detail-rating"><span class="star">&#9733;</span> ${formatRating(anime.rating)}</div>` : ''}
    </div>`;
}

function renderProgress(anime, progress) {
    if (!anime.episodes) return '';
    return `<div class="progress-section">
        <div class="progress-header">
            <span class="progress-label">观看进度</span>
            <span class="progress-value">${anime.watched_episodes || 0} / ${anime.episodes} 集</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width: ${progress}%"></div></div>
        ${anime.status === 'watching' ? `<div class="progress-actions"><button class="btn btn-primary btn-sm" onclick="incrementProgress(${anime.id})">+1 集</button></div>` : ''}
    </div>`;
}

function renderTags(genres, tags) {
    let html = '';
    if (genres.length > 0) {
        html += `<div class="genre-tags">${genres.map(g => `<span class="genre-tag">${escapeHtml(g)}</span>`).join('')}</div>`;
    }
    if (tags.length > 0) {
        html += `<div class="personal-tags">${tags.map(t => `<span class="personal-tag">${escapeHtml(t)}</span>`).join('')}</div>`;
    }
    return html;
}

function renderGrid(anime, seasonText) {
    const items = [];
    if (anime.studio) items.push({ label: '制作公司', value: anime.studio });
    if (seasonText) items.push({ label: '放送时间', value: seasonText });
    if (anime.air_date) items.push({ label: '首播日期', value: anime.air_date });
    if (anime.start_date) items.push({ label: '开始观看', value: anime.start_date });
    if (anime.finish_date) items.push({ label: '看完日期', value: anime.finish_date });
    if (items.length === 0) return '';
    return `<div class="detail-grid">${items.map(i =>
        `<div class="detail-item"><div class="label">${i.label}</div><div class="value">${escapeHtml(i.value)}</div></div>`
    ).join('')}</div>`;
}

function renderCharacters(characters) {
    if (characters.length === 0) return '';
    return `<div class="detail-characters">
        <h3>角色</h3>
        <div class="characters-grid">
            ${characters.map(c => `<div class="character-card">
                <div class="character-avatar ${c.avatar_url ? '' : 'no-img'}">
                    ${c.avatar_url
                        ? `<img src="${getProxiedUrl(c.avatar_url)}" alt="${escapeHtml(c.name)}" onerror="this.parentElement.classList.add('no-img');this.remove()">`
                        : `<span>${escapeHtml((c.name || '?')[0])}</span>`}
                </div>
                <div class="character-info">
                    <div class="character-name">${escapeHtml(c.name)}</div>
                    ${c.name_jp ? `<div class="character-name-jp">${escapeHtml(c.name_jp)}</div>` : ''}
                    ${c.role ? `<div class="character-role">${escapeHtml(c.role)}</div>` : ''}
                </div>
            </div>`).join('')}
        </div>
    </div>`;
}

function renderSynopsis(anime) {
    if (!anime.synopsis) return '';
    const html = escapeHtml(anime.synopsis).replace(/\n/g, '<br>');
    return `<div class="detail-synopsis"><h3>简介</h3><p>${html}</p></div>`;
}

function renderNotes(anime) {
    if (!anime.notes) return '';
    const html = escapeHtml(anime.notes).replace(/\n/g, '<br>');
    return `<div class="detail-notes"><h3>我的笔记</h3><div class="notes-content">${html}</div></div>`;
}

function renderEpisodeNotes(episodeNotes) {
    if (episodeNotes.length === 0) return '';
    return `<div class="detail-episodes">
        <h3>每集笔记</h3>
        <div class="episodes-list">
            ${episodeNotes.map(n => {
                const noteDiv = document.createElement('div');
                noteDiv.className = 'episode-note-content';
                noteDiv.textContent = n.note || '';
                const noteHtml = n.note ? noteDiv.outerHTML.replace(/\n/g, '<br>') : '';
                return `<div class="episode-note-card">
                    <div class="episode-note-header">
                        <span class="ep-badge">第 ${n.episode} 集</span>
                        ${n.rating ? `<span class="ep-rating">&#9733; ${n.rating.toFixed(1)}</span>` : ''}
                        ${n.watched_date ? `<span class="ep-date">${escapeHtml(n.watched_date)}</span>` : ''}
                    </div>
                    ${noteHtml}
                    ${n.images && n.images.length > 0 ? `
                        <div class="episode-images">
                            ${n.images.map(img => `
                                <div class="episode-img" onclick="openLightbox('${API_BASE}/uploads/${encodeURIComponent(img.filename)}')">
                                    <img src="${API_BASE}/uploads/${encodeURIComponent(img.filename)}" alt="${escapeHtml(img.original_name || '')}" loading="lazy">
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>`;
            }).join('')}
        </div>
    </div>`;
}

function renderLink(anime) {
    if (!anime.link_url) return '';
    return `<div class="detail-link"><a href="${escapeHtml(anime.link_url)}" target="_blank" rel="noopener">外部链接</a></div>`;
}

// ─── Actions ─────────────────────────────────────────────────

async function incrementProgress(id) {
    try {
        const updated = await apiPut(`/anime/${id}/progress`);
        showToast(`进度更新: ${updated.watched_episodes}/${updated.episodes || '?'}`);
        loadDetail();
    } catch (err) {
        showToast('更新失败: ' + err.message, 'error');
    }
}

// ─── Lightbox ────────────────────────────────────────────────

function openLightbox(src) {
    const overlay = document.createElement('div');
    overlay.className = 'lightbox-overlay';
    overlay.onclick = () => overlay.remove();
    const img = document.createElement('img');
    img.src = src;
    img.className = 'lightbox-img';
    overlay.appendChild(img);
    document.body.appendChild(overlay);
    const onKey = (e) => { if (e.key === 'Escape') { overlay.remove(); document.removeEventListener('keydown', onKey); } };
    document.addEventListener('keydown', onKey);
}

document.addEventListener('DOMContentLoaded', loadDetail);
