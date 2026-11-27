let adminCurrentPage = 1;
const ADMIN_PAGE_SIZE = 20;
let deleteTargetId = null;
let deleteTargetType = 'anime'; // anime | character | episode | image | changelog
let currentEditAnimeId = null;
let currentEpisodeImages = [];

// ─── Admin Token ─────────────────────────────────────────────

async function submitToken() {
    const input = document.getElementById('token-input');
    const token = input.value.trim();
    if (!token) { showToast('请输入令牌', 'error'); return; }
    setAdminToken(token);
    try {
        await apiGet('/auth/check');
        document.getElementById('token-modal').classList.remove('active');
        showToast('令牌验证成功');
        initAdmin();
    } catch (err) {
        setAdminToken('');
        showToast('令牌错误', 'error');
    }
}

function initAdmin() {
    loadAdminList();

    let searchTimeout;
    document.getElementById('admin-search').addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => { adminCurrentPage = 1; loadAdminList(); }, 300);
    });

    document.getElementById('admin-status-filter').addEventListener('change', () => {
        adminCurrentPage = 1;
        loadAdminList();
    });

    document.getElementById('form-episodes').addEventListener('input', syncWatchedEpisodesLimit);

    document.getElementById('form-modal').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeFormModal();
    });

    document.getElementById('delete-modal').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeDeleteModal();
    });

    document.getElementById('changelog-modal').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeChangelogModal();
    });
}

function syncWatchedEpisodesLimit() {
    const episodesInput = document.getElementById('form-episodes');
    const watchedInput = document.getElementById('form-watched');
    const total = parseInt(episodesInput.value, 10);
    if (Number.isInteger(total) && total >= 0) {
        watchedInput.max = String(total);
    } else {
        watchedInput.removeAttribute('max');
    }
}

// ─── Admin Tab Switching ─────────────────────────────────────

function switchAdminTab(tab) {
    document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.admin-tab-content').forEach(c => c.classList.remove('active'));
    const btn = document.querySelector(`.admin-tab[data-tab="${tab}"]`);
    if (btn) btn.classList.add('active');
    const content = document.getElementById('tab-' + tab);
    if (content) content.classList.add('active');
    if (tab === 'changelog') loadChangelogs();
}

// ─── Anime List ──────────────────────────────────────────────

async function loadAdminList() {
    const tbody = document.getElementById('admin-tbody');
    const paginationEl = document.getElementById('admin-pagination');

    tbody.innerHTML = '<tr><td colspan="7"><div class="loading-spinner"></div></td></tr>';

    try {
        const search = document.getElementById('admin-search').value;
        const status = document.getElementById('admin-status-filter').value;
        const data = await apiGet('/anime', {
            search: search || undefined,
            status: status || undefined,
            sort_by: 'updated_at',
            order: 'desc',
            page: adminCurrentPage,
            page_size: ADMIN_PAGE_SIZE,
        });

        if (data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><p>暂无数据</p></div></td></tr>';
            paginationEl.innerHTML = '';
            return;
        }

        tbody.innerHTML = data.items.map((a) => `
            <tr>
                <td>
                    <img class="cover-thumb" src="${getProxiedUrl(a.cover_url)}"
                         alt="${a.title}" onerror="this.src='${appPath('/assets/default-cover.svg')}'">
                </td>
                <td>
                    <strong>${a.title}</strong>
                    ${a.is_favorite ? ' <span style="color:var(--accent-warm)">&#10084;</span>' : ''}
                    ${a.title_jp ? `<br><small style="color:var(--text-secondary)">${a.title_jp}</small>` : ''}
                </td>
                <td><span class="status-badge ${a.status}">${getStatusText(a.status)}</span></td>
                <td>${a.episodes ? `${a.watched_episodes || 0}/${a.episodes}` : '-'}</td>
                <td class="rating-cell">${a.rating > 0 ? '&#9733; ' + a.rating.toFixed(1) : '-'}</td>
                <td>${a.year || '-'}</td>
                <td>
                    <div class="actions">
                        <button class="btn btn-secondary btn-sm" onclick="openEditModal(${a.id})">编辑</button>
                        <button class="btn btn-danger btn-sm" onclick="openDeleteModal(${a.id}, '${a.title.replace(/'/g, "\\'")}')">删除</button>
                    </div>
                </td>
            </tr>
        `).join('');

        paginationEl.innerHTML = '';
        const pagination = createPagination(data.total, data.page, data.page_size, (page) => {
            adminCurrentPage = page;
            loadAdminList();
        });
        paginationEl.appendChild(pagination);
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><p>加载失败: ${err.message}</p></div></td></tr>`;
    }
}

// ─── Anime Create/Edit Modal ─────────────────────────────────

function openCreateModal() {
    currentEditAnimeId = null;
    document.getElementById('modal-title').textContent = '新增番剧';
    document.getElementById('form-id').value = '';
    document.getElementById('anime-form').reset();
    document.getElementById('form-rating').value = '0';
    document.getElementById('form-watched').value = '0';
    syncWatchedEpisodesLimit();
    document.getElementById('cover-preview').innerHTML = '';
    document.getElementById('modal-tabs').style.display = 'none';
    switchModalTab('info');
    document.getElementById('form-modal').classList.add('active');
}

async function openEditModal(id) {
    try {
        const anime = await apiGet(`/anime/${id}`);
        currentEditAnimeId = id;
        document.getElementById('modal-title').textContent = '编辑番剧';
        document.getElementById('form-id').value = anime.id;
        document.getElementById('form-title').value = anime.title || '';
        document.getElementById('form-title-jp').value = anime.title_jp || '';
        document.getElementById('form-cover').value = anime.cover_url || '';
        document.getElementById('form-status').value = anime.status || 'planned';
        document.getElementById('form-rating').value = anime.rating || 0;
        document.getElementById('form-episodes').value = anime.episodes || '';
        document.getElementById('form-watched').value = anime.watched_episodes || 0;
        syncWatchedEpisodesLimit();
        document.getElementById('form-year').value = anime.year || '';
        document.getElementById('form-season').value = anime.season || '';
        document.getElementById('form-start-date').value = anime.start_date || '';
        document.getElementById('form-finish-date').value = anime.finish_date || '';
        document.getElementById('form-air-date').value = anime.air_date || '';
        document.getElementById('form-genre').value = anime.genre || '';
        document.getElementById('form-studio').value = anime.studio || '';
        document.getElementById('form-personal-tags').value = anime.personal_tags || '';
        document.getElementById('form-link').value = anime.link_url || '';
        document.getElementById('form-synopsis').value = anime.synopsis || '';
        document.getElementById('form-notes').value = anime.notes || '';
        document.getElementById('form-featured').checked = anime.is_featured === 1;
        document.getElementById('form-favorite').checked = anime.is_favorite === 1;
        previewCover(anime.cover_url || '');
        document.getElementById('modal-tabs').style.display = 'flex';
        switchModalTab('info');
        document.getElementById('form-modal').classList.add('active');
    } catch (err) {
        showToast('加载番剧信息失败: ' + err.message, 'error');
    }
}

function closeFormModal() {
    document.getElementById('form-modal').classList.remove('active');
    currentEditAnimeId = null;
}

function switchModalTab(tab) {
    const modal = document.getElementById('form-modal');
    if (!modal) return;
    modal.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
    modal.querySelectorAll('.modal-tab-content').forEach(c => c.classList.remove('active'));
    const btn = modal.querySelector(`.modal-tab[data-tab="${tab}"]`);
    if (btn) btn.classList.add('active');
    const content = document.getElementById('modal-tab-' + tab);
    if (content) content.classList.add('active');
    if (tab === 'characters' && currentEditAnimeId) loadCharacters(currentEditAnimeId);
    if (tab === 'episodes' && currentEditAnimeId) loadEpisodeNotes(currentEditAnimeId);
}

function previewCover(url) {
    const preview = document.getElementById('cover-preview');
    if (url) {
        preview.innerHTML = `<img src="${getProxiedUrl(url)}" onerror="this.style.display='none'" alt="封面预览">`;
    } else {
        preview.innerHTML = '';
    }
}

async function handleSubmit(e) {
    e.preventDefault();
    const titleVal = document.getElementById('form-title').value.trim();
    if (!titleVal) {
        showToast('请输入番剧名称', 'error');
        switchModalTab('info');
        document.getElementById('form-title').focus();
        return;
    }
    const id = document.getElementById('form-id').value;
    const episodesValue = document.getElementById('form-episodes').value;
    const watchedValue = document.getElementById('form-watched').value;
    const episodes = episodesValue === '' ? null : parseInt(episodesValue, 10);
    const watchedEpisodes = watchedValue === '' ? 0 : parseInt(watchedValue, 10);
    if (episodes !== null && watchedEpisodes > episodes) {
        showToast('已看集数不能超过总集数', 'error');
        switchModalTab('info');
        document.getElementById('form-watched').focus();
        return;
    }
    const data = {
        title: titleVal,
        title_jp: document.getElementById('form-title-jp').value || null,
        cover_url: document.getElementById('form-cover').value || null,
        status: document.getElementById('form-status').value,
        rating: parseFloat(document.getElementById('form-rating').value) || 0,
        episodes: episodes,
        watched_episodes: watchedEpisodes,
        year: parseInt(document.getElementById('form-year').value) || null,
        season: document.getElementById('form-season').value || null,
        start_date: document.getElementById('form-start-date').value || null,
        finish_date: document.getElementById('form-finish-date').value || null,
        air_date: document.getElementById('form-air-date').value || null,
        genre: document.getElementById('form-genre').value || null,
        studio: document.getElementById('form-studio').value || null,
        personal_tags: document.getElementById('form-personal-tags').value || null,
        link_url: document.getElementById('form-link').value || null,
        synopsis: document.getElementById('form-synopsis').value || null,
        notes: document.getElementById('form-notes').value || null,
        is_featured: document.getElementById('form-featured').checked ? 1 : 0,
        is_favorite: document.getElementById('form-favorite').checked ? 1 : 0,
    };

    const btn = document.getElementById('form-submit-btn');
    btn.disabled = true;
    try {
        if (id) {
            await apiPut(`/anime/${id}`, data);
            showToast('番剧更新成功');
        } else {
            await apiPost('/anime', data);
            showToast('番剧添加成功');
        }
        closeFormModal();
        loadAdminList();
    } catch (err) {
        showToast('操作失败: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
    }
}

// ─── Delete Modal ────────────────────────────────────────────

function openDeleteModal(id, title) {
    deleteTargetId = id;
    deleteTargetType = 'anime';
    document.getElementById('delete-message').textContent = `确定要删除「${title}」吗？此操作不可撤销。`;
    document.getElementById('delete-modal').classList.add('active');
}

function closeDeleteModal() {
    deleteTargetId = null;
    document.getElementById('delete-modal').classList.remove('active');
}

async function confirmDelete() {
    if (!deleteTargetId) return;
    try {
        if (deleteTargetType === 'anime') {
            await apiDelete(`/anime/${deleteTargetId}`);
            showToast('删除成功');
            loadAdminList();
        } else if (deleteTargetType === 'character') {
            await apiDelete(`/characters/${deleteTargetId}`);
            showToast('角色已删除');
            loadCharacters(currentEditAnimeId);
        } else if (deleteTargetType === 'episode') {
            await apiDelete(`/episodes/${deleteTargetId}`);
            showToast('笔记已删除');
            loadEpisodeNotes(currentEditAnimeId);
        } else if (deleteTargetType === 'image') {
            await apiDelete(`/episode-images/${deleteTargetId}`);
            showToast('图片已删除');
            loadEpisodeNotes(currentEditAnimeId);
        } else if (deleteTargetType === 'changelog') {
            await apiDelete(`/changelogs/${deleteTargetId}`);
            showToast('日志已删除');
            loadChangelogs();
        }
        closeDeleteModal();
    } catch (err) {
        showToast('删除失败: ' + err.message, 'error');
    }
}

// ─── Characters ──────────────────────────────────────────────

let _charactersCache = [];
let _episodesCache = [];

async function loadCharacters(animeId) {
    const list = document.getElementById('characters-list');
    try {
        const chars = await apiGet(`/anime/${animeId}/characters`);
        _charactersCache = chars;
        if (chars.length === 0) {
            list.innerHTML = '<p class="sub-empty">暂无角色，点击上方按钮添加</p>';
            return;
        }
        list.innerHTML = chars.map((c, i) => `
            <div class="sub-item">
                <div class="sub-item-info">
                    <div class="sub-item-avatar ${c.avatar_url ? '' : 'no-img'}">
                        ${c.avatar_url
                            ? `<img src="${getProxiedUrl(c.avatar_url)}" onerror="this.parentElement.classList.add('no-img');this.remove()">`
                            : `<span>${(c.name || '?')[0]}</span>`}
                    </div>
                    <div>
                        <strong>${c.name}</strong>
                        ${c.name_jp ? `<small> ${c.name_jp}</small>` : ''}
                        ${c.role ? `<span class="sub-tag">${c.role}</span>` : ''}
                    </div>
                </div>
                <div class="sub-item-actions">
                    <button type="button" class="btn btn-secondary btn-sm" onclick="editCharacterByIndex(${i})">编辑</button>
                    <button type="button" class="btn btn-danger btn-sm" onclick="deleteCharacter(${c.id})">删除</button>
                </div>
            </div>
        `).join('');
    } catch (err) {
        list.innerHTML = `<p class="sub-empty">加载失败: ${err.message}</p>`;
    }
}

function openCharacterForm(data) {
    document.getElementById('character-form-area').style.display = 'block';
    document.getElementById('char-form-id').value = data ? data.id : '';
    document.getElementById('char-form-name').value = data ? data.name : '';
    document.getElementById('char-form-name-jp').value = data ? (data.name_jp || '') : '';
    document.getElementById('char-form-avatar').value = data ? (data.avatar_url || '') : '';
    document.getElementById('char-form-role').value = data ? (data.role || '') : '';
    document.getElementById('char-form-desc').value = data ? (data.description || '') : '';
}

function closeCharacterForm() {
    document.getElementById('character-form-area').style.display = 'none';
}

function editCharacterByIndex(index) {
    openCharacterForm(_charactersCache[index]);
}

function deleteCharacter(id) {
    deleteTargetId = id;
    deleteTargetType = 'character';
    document.getElementById('delete-message').textContent = '确定要删除这个角色吗？';
    document.getElementById('delete-modal').classList.add('active');
}

async function saveCharacter() {
    const name = document.getElementById('char-form-name').value.trim();
    if (!name) { showToast('请输入角色名', 'error'); return; }
    const id = document.getElementById('char-form-id').value;
    const data = {
        name: name,
        name_jp: document.getElementById('char-form-name-jp').value || null,
        avatar_url: document.getElementById('char-form-avatar').value || null,
        role: document.getElementById('char-form-role').value || null,
        description: document.getElementById('char-form-desc').value || null,
    };
    try {
        if (id) {
            await apiPut(`/characters/${id}`, data);
        } else {
            await apiPost(`/anime/${currentEditAnimeId}/characters`, data);
        }
        showToast('角色已保存');
        closeCharacterForm();
        loadCharacters(currentEditAnimeId);
    } catch (err) {
        showToast('保存失败: ' + err.message, 'error');
    }
}

// ─── Episode Notes ───────────────────────────────────────────

async function loadEpisodeNotes(animeId) {
    const list = document.getElementById('episodes-list');
    try {
        const notes = await apiGet(`/anime/${animeId}/episodes`);
        _episodesCache = notes;
        if (notes.length === 0) {
            list.innerHTML = '<p class="sub-empty">暂无笔记，点击上方按钮添加</p>';
            return;
        }
        list.innerHTML = notes.map((n, i) => `
            <div class="sub-item">
                <div class="sub-item-info">
                    <span class="ep-badge">第 ${n.episode} 集</span>
                    ${n.rating ? `<span class="sub-tag">&#9733; ${n.rating.toFixed(1)}</span>` : ''}
                    ${n.note ? `<span class="ep-note-preview">${n.note.substring(0, 60)}${n.note.length > 60 ? '...' : ''}</span>` : ''}
                    ${n.images && n.images.length > 0 ? `<span class="sub-tag">${n.images.length} 张图</span>` : ''}
                </div>
                <div class="sub-item-actions">
                    <button type="button" class="btn btn-secondary btn-sm" onclick="editEpisodeByIndex(${i})">编辑</button>
                    <button type="button" class="btn btn-danger btn-sm" onclick="deleteEpisodeNote(${n.id})">删除</button>
                </div>
            </div>
        `).join('');
    } catch (err) {
        list.innerHTML = `<p class="sub-empty">加载失败: ${err.message}</p>`;
    }
}

function openEpisodeForm(data) {
    document.getElementById('episode-form-area').style.display = 'block';
    document.getElementById('ep-form-id').value = data ? data.id : '';
    document.getElementById('ep-form-episode').value = data ? data.episode : '';
    document.getElementById('ep-form-rating').value = data ? (data.rating || '') : '';
    document.getElementById('ep-form-date').value = data ? (data.watched_date || '') : '';
    document.getElementById('ep-form-note').value = data ? (data.note || '') : '';
    currentEpisodeImages = data ? (data.images || []) : [];
    renderEpisodeImages();
    document.getElementById('ep-form-images').value = '';
}

function closeEpisodeForm() {
    document.getElementById('episode-form-area').style.display = 'none';
    currentEpisodeImages = [];
}

function editEpisodeByIndex(index) {
    openEpisodeForm(_episodesCache[index]);
}

function deleteEpisodeNote(id) {
    deleteTargetId = id;
    deleteTargetType = 'episode';
    document.getElementById('delete-message').textContent = '确定要删除这条笔记吗？关联的图片也会被删除。';
    document.getElementById('delete-modal').classList.add('active');
}

function renderEpisodeImages() {
    const preview = document.getElementById('ep-images-preview');
    if (currentEpisodeImages.length === 0) {
        preview.innerHTML = '';
        return;
    }
    preview.innerHTML = currentEpisodeImages.map(img => `
        <div class="ep-img-thumb">
            <img src="${API_BASE}/uploads/${encodeURIComponent(img.filename)}" alt="${img.original_name || ''}">
            <button type="button" class="ep-img-del" onclick="deleteEpisodeImage(${img.id})">&times;</button>
        </div>
    `).join('');
}

async function uploadEpisodeImages(input) {
    const noteId = document.getElementById('ep-form-id').value;
    if (!noteId) {
        showToast('请先保存笔记再上传图片', 'error');
        input.value = '';
        return;
    }
    for (const file of input.files) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            const res = await fetch(`${API_BASE}/episodes/${noteId}/images`, {
                method: 'POST',
                body: formData,
                headers: getAdminToken() ? { 'X-Admin-Token': getAdminToken() } : {},
            });
            if (!res.ok) throw new Error('上传失败');
            const img = await res.json();
            currentEpisodeImages.push(img);
        } catch (err) {
            showToast('图片上传失败: ' + err.message, 'error');
        }
    }
    renderEpisodeImages();
    input.value = '';
}

async function deleteEpisodeImage(id) {
    try {
        await apiDelete(`/episode-images/${id}`);
        currentEpisodeImages = currentEpisodeImages.filter(i => i.id !== id);
        renderEpisodeImages();
        showToast('图片已删除');
    } catch (err) {
        showToast('删除失败: ' + err.message, 'error');
    }
}

async function saveEpisodeNote() {
    const epVal = parseInt(document.getElementById('ep-form-episode').value);
    if (!epVal || epVal < 1) { showToast('请输入有效集数', 'error'); return; }
    const id = document.getElementById('ep-form-id').value;
    const data = {
        episode: epVal,
        rating: parseFloat(document.getElementById('ep-form-rating').value) || null,
        watched_date: document.getElementById('ep-form-date').value || null,
        note: document.getElementById('ep-form-note').value || null,
    };
    try {
        if (id) {
            await apiPut(`/episodes/${id}`, data);
        } else {
            await apiPost(`/anime/${currentEditAnimeId}/episodes`, data);
        }
        showToast('笔记已保存');
        closeEpisodeForm();
        loadEpisodeNotes(currentEditAnimeId);
    } catch (err) {
        showToast('保存失败: ' + err.message, 'error');
    }
}

// ─── Changelog ───────────────────────────────────────────────

let _changelogsCache = [];

async function loadChangelogs() {
    const container = document.getElementById('changelog-list');
    try {
        const logs = await apiGet('/changelogs');
        _changelogsCache = logs;
        if (logs.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>暂无更新日志</p></div>';
            return;
        }
        container.innerHTML = logs.map((l, i) => `
            <div class="changelog-item">
                <div class="changelog-header">
                    <div>
                        <strong>${l.title}</strong>
                        ${l.version ? `<span class="sub-tag">${l.version}</span>` : ''}
                        <small style="color:var(--text-secondary); margin-left:8px;">${new Date(l.created_at).toLocaleDateString('zh-CN')}</small>
                    </div>
                    <div class="sub-item-actions">
                        <button type="button" class="btn btn-secondary btn-sm" onclick="editChangelogByIndex(${i})">编辑</button>
                        <button type="button" class="btn btn-danger btn-sm" onclick="deleteChangelog(${l.id})">删除</button>
                    </div>
                </div>
                ${l.content ? `<div class="changelog-content">${l.content.replace(/\n/g, '<br>')}</div>` : ''}
            </div>
        `).join('');
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><p>加载失败: ${err.message}</p></div>`;
    }
}

function openChangelogModal(data) {
    document.getElementById('changelog-modal-title').textContent = data ? '编辑更新日志' : '新增更新日志';
    document.getElementById('log-form-id').value = data ? data.id : '';
    document.getElementById('log-form-title').value = data ? data.title : '';
    document.getElementById('log-form-version').value = data ? (data.version || '') : '';
    document.getElementById('log-form-content').value = data ? (data.content || '') : '';
    document.getElementById('changelog-modal').classList.add('active');
}

function closeChangelogModal() {
    document.getElementById('changelog-modal').classList.remove('active');
}

function editChangelogByIndex(index) {
    openChangelogModal(_changelogsCache[index]);
}

function deleteChangelog(id) {
    deleteTargetId = id;
    deleteTargetType = 'changelog';
    document.getElementById('delete-message').textContent = '确定要删除这条更新日志吗？';
    document.getElementById('delete-modal').classList.add('active');
}

async function handleChangelogSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('log-form-id').value;
    const data = {
        title: document.getElementById('log-form-title').value,
        version: document.getElementById('log-form-version').value || null,
        content: document.getElementById('log-form-content').value || null,
    };
    try {
        if (id) {
            await apiPut(`/changelogs/${id}`, data);
        } else {
            await apiPost('/changelogs', data);
        }
        showToast('日志已保存');
        closeChangelogModal();
        loadChangelogs();
    } catch (err) {
        showToast('保存失败: ' + err.message, 'error');
    }
}

// ─── Export/Import ───────────────────────────────────────────

async function exportData() {
    try {
        const res = await fetch(`${API_BASE}/export`, {
            headers: getAdminToken() ? { 'X-Admin-Token': getAdminToken() } : {},
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || '导出失败');
        }
        const data = await res.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `anime_export_${new Date().toISOString().slice(0,10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('数据导出成功');
    } catch (err) {
        showToast('导出失败: ' + err.message, 'error');
    }
}

async function importData(event) {
    const file = event.target.files[0];
    if (!file) return;
    try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(`${API_BASE}/import`, {
            method: 'POST',
            body: formData,
            headers: getAdminToken() ? { 'X-Admin-Token': getAdminToken() } : {},
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || '导入失败');
        showToast(result.message);
        loadAdminList();
    } catch (err) {
        showToast('导入失败: ' + err.message, 'error');
    }
    event.target.value = '';
}

// ─── Init ────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    // 已有令牌则先验证，否则显示令牌输入框
    if (getAdminToken()) {
        try {
            await apiGet('/auth/check');
            document.getElementById('token-modal').classList.remove('active');
            initAdmin();
            return;
        } catch (err) {
            setAdminToken('');
        }
    }
    document.getElementById('token-modal').classList.add('active');
    document.getElementById('token-input').focus();
});
