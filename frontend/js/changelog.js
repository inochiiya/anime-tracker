async function loadChangelog() {
    const container = document.getElementById('changelog-content');
    try {
        const logs = await apiGet('/changelogs');
        if (logs.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>暂无更新日志</p></div>';
            return;
        }
        container.innerHTML = `
            <div class="changelog-timeline">
                ${logs.map(l => `
                    <div class="changelog-entry">
                        <div class="changelog-dot"></div>
                        <div class="changelog-card">
                            <div class="changelog-header">
                                <h2 class="changelog-title">${l.title}</h2>
                                <div class="changelog-meta">
                                    ${l.version ? `<span class="changelog-version">${l.version}</span>` : ''}
                                    <span class="changelog-date">${new Date(l.created_at).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
                                </div>
                            </div>
                            ${l.content ? `<div class="changelog-body">${l.content.replace(/\n/g, '<br>')}</div>` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><p>加载失败: ${err.message}</p></div>`;
    }
}

document.addEventListener('DOMContentLoaded', loadChangelog);
