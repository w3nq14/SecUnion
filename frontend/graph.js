const API_BASE = 'http://localhost:8011';

let cy;
let currentJobId = null;

document.getElementById('startBtn').addEventListener('click', async () => {
    const seedUrlsText = document.getElementById('seedUrls').value;
    const maxDepth = parseInt(document.getElementById('maxDepth').value);

    const seedUrls = seedUrlsText.split('\n').map(u => u.trim()).filter(u => u);

    if (seedUrls.length === 0) {
        alert('请输入至少一个博客URL');
        return;
    }

    document.getElementById('status').textContent = '正在爬取...';
    document.getElementById('startBtn').style.display = 'none';
    document.getElementById('stopBtn').style.display = 'inline-block';
    document.getElementById('blogList').style.display = 'none';
    if (cy) cy.destroy();

    try {
        const response = await fetch(`${API_BASE}/crawl`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({seed_urls: seedUrls, max_depth: maxDepth, use_cache: false})
        });

        const {job_id} = await response.json();
        currentJobId = job_id;
        pollStatus(job_id);
    } catch (error) {
        document.getElementById('status').textContent = '错误: ' + error.message;
        document.getElementById('startBtn').style.display = 'inline-block';
        document.getElementById('stopBtn').style.display = 'none';
    }
});

document.getElementById('stopBtn').addEventListener('click', async () => {
    if (currentJobId) {
        await fetch(`${API_BASE}/stop/${currentJobId}`, {method: 'POST'});
        document.getElementById('status').textContent = '正在停止...';
    }
});

document.getElementById('cacheBtn').addEventListener('click', async () => {
    const seedUrlsText = document.getElementById('seedUrls').value;
    const maxDepth = parseInt(document.getElementById('maxDepth').value);
    const seedUrls = seedUrlsText.split('\n').map(u => u.trim()).filter(u => u);

    if (seedUrls.length === 0) {
        alert('请输入至少一个博客URL');
        return;
    }

    document.getElementById('status').textContent = '正在从缓存加载...';
    document.getElementById('blogList').style.display = 'none';
    if (cy) cy.destroy();

    try {
        const response = await fetch(`${API_BASE}/cache?seed_urls=${encodeURIComponent(seedUrls.join(','))}&max_depth=${maxDepth}`);
        const data = await response.json();

        if (!data.blogs || Object.keys(data.blogs).length === 0) {
            document.getElementById('status').textContent = '缓存中没有找到相关数据';
            return;
        }

        // 构建图数据
        const nodes = Object.keys(data.blogs).map(url => ({
            id: url,
            label: data.blogs[url].name,
            name: data.blogs[url].name,
            is_accessible: data.blogs[url].is_accessible
        }));

        // 去重edges（相同source+target只保留一条）
        const edgeSet = new Set();
        const edges = data.edges.filter(e => {
            const key = e.source + '__' + e.target;
            if (edgeSet.has(key)) return false;
            edgeSet.add(key);
            return true;
        });

        window.currentGraphData = {nodes: nodes, edges: edges};
        renderGraph(window.currentGraphData, seedUrls);
        document.getElementById('status').textContent = `从缓存加载了 ${nodes.length} 个博客`;
    } catch (error) {
        document.getElementById('status').textContent = '错误: ' + error.message;
    }
});

document.getElementById('allBlogsBtn').addEventListener('click', async () => {
    try {
        const response = await fetch(`${API_BASE}/all_blogs?t=${Date.now()}`);
        const data = await response.json();

        if (cy) cy.destroy();
        document.getElementById('blogList').style.display = 'block';
        document.getElementById('tableView').style.display = 'none';

        if (!data.blogs || data.blogs.length === 0) {
            document.getElementById('blogList').innerHTML = '<h3>全部友链列表</h3><div class="blog-item">暂无数据</div>';
            document.getElementById('status').textContent = '暂无博客数据';
            return;
        }

        document.getElementById('blogList').innerHTML = `
            <h3>全部友链列表</h3>
            <table class="all-blogs-table">
                <thead>
                    <tr>
                        <th>标题</th>
                        <th>URL</th>
                        <th>在线</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.blogs.map(b => `
                        <tr>
                            <td>${b.name}</td>
                            <td><a href="${b.url}" target="_blank">${b.url}</a></td>
                            <td>${b.is_accessible !== false ? '是' : '否'}</td>
                            <td><button class="blacklist-btn" data-url="${b.url}">加入黑名单</button></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        document.getElementById('status').textContent = `共 ${data.blogs.length} 个博客`;

        document.querySelectorAll('.blacklist-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const url = e.target.getAttribute('data-url');
                if (!confirm(`确定将 ${url} 加入黑名单吗？`)) return;

                try {
                    const response = await fetch(`${API_BASE}/blacklist`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({url: url})
                    });
                    const result = await response.json();
                    if (result.status === 'success') {
                        alert(`已将 ${result.domain} 加入黑名单`);
                        e.target.closest('tr').remove();
                    }
                } catch (error) {
                    alert('操作失败: ' + error.message);
                }
            });
        });
    } catch (error) {
        document.getElementById('status').textContent = '错误: ' + error.message;
    }
});

async function pollStatus(jobId) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/status/${jobId}`);
            const data = await response.json();

            if (data.status === 'running') {
                document.getElementById('status').textContent = data.progress || '正在爬取...';
            } else if (data.status === 'completed') {
                clearInterval(interval);
                document.getElementById('status').textContent = `爬取完成！共 ${data.graph.nodes.length} 个博客`;
                showTableView(data.graph);
                document.getElementById('startBtn').style.display = 'inline-block';
                document.getElementById('stopBtn').style.display = 'none';
                currentJobId = null;
            } else if (data.status === 'failed') {
                clearInterval(interval);
                document.getElementById('status').textContent = '爬取失败: ' + data.error;
                document.getElementById('startBtn').style.display = 'inline-block';
                document.getElementById('stopBtn').style.display = 'none';
                currentJobId = null;
            }
        } catch (error) {
            clearInterval(interval);
            document.getElementById('status').textContent = '错误: ' + error.message;
            document.getElementById('startBtn').style.display = 'inline-block';
            document.getElementById('stopBtn').style.display = 'none';
            currentJobId = null;
        }
    }, 1000);
}

async function loadGraph(jobId, seedUrls) {
    const response = await fetch(`${API_BASE}/graph/${jobId}`);
    const graph = await response.json();
    renderGraph(graph, seedUrls);
}

function renderGraph(graph, seedUrls) {
    if (!seedUrls) seedUrls = [];

    const elements = {
        nodes: graph.nodes.map(n => ({
            data: {
                id: n.id,
                label: n.name || n.label,
                degree: n.degree || 0,
                isSeed: seedUrls.includes(n.id),
                isAccessible: n.is_accessible !== false
            }
        })),
        edges: graph.edges.map(e => ({
            data: {
                source: e.source,
                target: e.target
            }
        }))
    };

    cy = cytoscape({
        container: document.getElementById('cy'),
        elements: elements,
        style: [
            {
                selector: 'node',
                style: {
                    'background-color': ele => {
                        if (ele.data('isSeed')) return '#e74c3c';
                        return ele.data('isAccessible') ? '#27ae60' : '#95a5a6';
                    },
                    'label': 'data(label)',
                    'width': ele => 20 + ele.data('degree') * 5,
                    'height': ele => 20 + ele.data('degree') * 5,
                    'font-size': '10px',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'color': '#fff',
                    'text-outline-width': 2,
                    'text-outline-color': '#000',
                    'border-width': 3,
                    'border-color': ele => ele.data('isAccessible') ? '#27ae60' : '#e74c3c'
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': '#95a5a6',
                    'target-arrow-color': '#95a5a6',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'arrow-scale': 1.5
                }
            },
            {
                selector: '.highlighted',
                style: {
                    'opacity': 1
                }
            },
            {
                selector: 'node.dimmed',
                style: {
                    'opacity': 0.3
                }
            },
            {
                selector: 'edge.dimmed',
                style: {
                    'opacity': 0.3
                }
            }
        ],
        layout: {
            name: 'cose',
            animate: elements.nodes.length < 100,  // 节点多时禁用动画
            animationDuration: 500,
            nodeRepulsion: 8000,
            idealEdgeLength: 100,
            edgeElasticity: 100,
            numIter: elements.nodes.length > 200 ? 500 : 1000,  // 节点多时减少迭代次数
            randomize: false,
            fit: true,
            padding: 30
        }
    });

    // 显示"切换到列表"按钮，隐藏图视图容器中的表格
    document.getElementById('tableView').style.display = 'none';
    document.getElementById('switchToTableBtn').style.display = 'block';

    cy.on('tap', 'node', function(evt) {
        const node = evt.target;
        cy.elements().removeClass('highlighted').removeClass('dimmed');
        node.addClass('highlighted');
        node.neighborhood().addClass('highlighted');
        cy.elements().not('.highlighted').addClass('dimmed');
    });

    cy.on('tap', function(evt) {
        if (evt.target === cy) {
            cy.elements().removeClass('highlighted').removeClass('dimmed');
        }
    });
}

function showTableView(graph) {
    if (cy) cy.destroy();
    document.getElementById('blogList').style.display = 'none';
    document.getElementById('tableView').style.display = 'block';
    document.getElementById('switchToTableBtn').style.display = 'none';

    const tbody = document.querySelector('#blogTable tbody');
    tbody.innerHTML = graph.nodes.map(n => `
        <tr>
            <td>${n.name || n.label}</td>
            <td><a href="${n.id}" target="_blank">${n.id}</a></td>
            <td>${n.is_accessible !== false ? '在线' : '离线'}</td>
        </tr>
    `).join('');

    document.getElementById('switchToGraphBtn').onclick = () => {
        document.getElementById('tableView').style.display = 'none';
        document.getElementById('switchToTableBtn').style.display = 'block';
        renderGraph(graph);
    };

    window.currentGraphData = graph;
}

document.getElementById('switchToTableBtn').addEventListener('click', () => {
    if (window.currentGraphData) {
        showTableView(window.currentGraphData);
    }
});

document.getElementById('updateFriendsBtn').addEventListener('click', async () => {
    const btn = document.getElementById('updateFriendsBtn');
    btn.disabled = true;

    document.getElementById('blogList').style.display = 'block';
    document.getElementById('tableView').style.display = 'none';
    document.getElementById('blogList').innerHTML = `
        <h3>友链更新检查</h3>
        <div id="updateProgress" style="margin-bottom:12px;">
            <div style="background:#2c2c2c;border-radius:6px;height:18px;overflow:hidden;">
                <div id="progressBar" style="height:100%;width:0%;background:#27ae60;transition:width 0.3s;"></div>
            </div>
            <div id="progressText" style="margin-top:6px;color:#aaa;font-size:0.9em;">准备中...</div>
        </div>
        <table class="all-blogs-table">
            <thead><tr><th>博客网址</th><th>变化情况</th></tr></thead>
            <tbody id="updateResultBody"></tbody>
        </table>
    `;
    document.getElementById('status').textContent = '正在更新友链...';

    try {
        const response = await fetch(`${API_BASE}/update_friends`, { method: 'POST' });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // 保留未完成的行

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const msg = JSON.parse(line.slice(6));

                if (msg.type === 'start') {
                    document.getElementById('progressText').textContent = `共 ${msg.total} 个博客待检查`;

                } else if (msg.type === 'progress') {
                    const pct = Math.round(msg.current / msg.total * 100);
                    document.getElementById('progressBar').style.width = pct + '%';
                    document.getElementById('progressText').textContent =
                        `${msg.current} / ${msg.total}  (${pct}%)`;
                    document.getElementById('status').textContent =
                        `正在检查: ${msg.blog_url}`;

                    const tbody = document.getElementById('updateResultBody');
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><a href="${msg.blog_url}" target="_blank">${msg.blog_url}</a></td>
                        <td>${msg.has_changes
                            ? `<span style="color:#2ecc71">有新增 (${msg.new_friends.length}个)</span><br>${msg.new_friends.map(f => `<a href="${f}" target="_blank" style="font-size:0.9em">${f}</a>`).join('<br>')}`
                            : '<span style="color:#95a5a6">无变化</span>'
                        }</td>
                    `;
                    tbody.appendChild(tr);

                } else if (msg.type === 'done') {
                    document.getElementById('progressBar').style.width = '100%';
                    document.getElementById('progressText').textContent = `检查完成！共 ${msg.total} 个博客`;
                    document.getElementById('status').textContent =
                        `检查完成！${msg.changes_count} 个博客有新友链`;
                    btn.disabled = false;
                }
            }
        }
    } catch (error) {
        document.getElementById('status').textContent = '更新失败: ' + error.message;
        btn.disabled = false;
    }
});

