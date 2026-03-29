from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from crawler import Crawler
from graph_builder import GraphBuilder
from storage import Storage
from domain_filter import DomainFilter
from ai_detector import AIDetector
import asyncio
import uuid
import os
from typing import List

# Force reload
import importlib
import sys
if 'graph_builder' in sys.modules:
    importlib.reload(sys.modules['graph_builder'])
if 'crawler' in sys.modules:
    importlib.reload(sys.modules['crawler'])

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs = {}
storage = Storage()
domain_filter = DomainFilter()
ai_detector = AIDetector(
    api_key=os.environ.get("AI_API_KEY", "sk-AISF7OVLKZ0rfFnzEE5SwHyapmqqXqOpVTmaltxd4I0O2dml"),
    base_url=os.environ.get("AI_BASE_URL", "https://api.linkapi.ai/v1")
)
active_crawlers = {}

class CrawlRequest(BaseModel):
    seed_urls: List[str]
    max_depth: int = 1
    use_cache: bool = False

async def run_crawl(job_id: str, seed_urls: List[str], max_depth: int, use_cache: bool):
    jobs[job_id] = {"status": "running", "progress": "开始爬取...", "current_depth": 0}

    def update_progress(depth, url):
        jobs[job_id]["current_depth"] = depth
        jobs[job_id]["progress"] = f"正在爬取深度 {depth}: {url[:50]}..."

    try:
        crawler = Crawler(max_depth=max_depth, use_cache=use_cache, ai_detector=ai_detector)
        active_crawlers[job_id] = crawler

        crawl_data = await crawler.crawl_recursive(seed_urls, update_progress)

        builder = GraphBuilder()
        graph = builder.build(crawl_data)

        for node in graph['nodes']:
            blog = storage.get_blog(node['id'])
            if blog:
                node['name'] = blog['name']
                node['is_accessible'] = blog['is_accessible']
            else:
                node['name'] = node['label']
                node['is_accessible'] = True

        jobs[job_id] = {
            "status": "completed",
            "graph": graph,
            "blacklisted": list(domain_filter.get_blacklist())
        }
    except Exception as e:
        jobs[job_id] = {"status": "failed", "error": str(e)}
    finally:
        if job_id in active_crawlers:
            del active_crawlers[job_id]

@app.post("/crawl")
async def crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(run_crawl, job_id, request.seed_urls, request.max_depth, request.use_cache)
    return {"job_id": job_id}

@app.post("/stop/{job_id}")
async def stop_crawl(job_id: str):
    if job_id in active_crawlers:
        active_crawlers[job_id].stop()
        return {"status": "stopping"}
    return {"status": "not_found"}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        return {"status": "not_found"}
    return jobs[job_id]

@app.get("/graph/{job_id}")
async def get_graph(job_id: str):
    if job_id not in jobs or jobs[job_id]["status"] != "completed":
        return {"error": "Graph not ready"}
    return jobs[job_id]["graph"]

@app.get("/cache")
async def get_cache(seed_urls: str = "", max_depth: int = 1):
    """从缓存中查询相关博客"""
    if not seed_urls:
        blogs = storage.get_all_blogs()
        edges = storage.get_edges()
        return {"blogs": blogs, "edges": edges}

    seed_list = [url.strip() for url in seed_urls.split(',') if url.strip()]
    from url_normalizer import URLNormalizer
    seed_list = [URLNormalizer.normalize(url) for url in seed_list]

    all_blogs = storage.get_all_blogs()

    # 逐层扩展：直接查 edges 表，找出链+入链
    current_layer = set(seed_list)
    all_nodes = set(seed_list)

    max_iter = 100 if max_depth >= 999 else max_depth

    for depth in range(max_iter):
        # 查询当前层所有节点相关的边
        related_edges = storage.get_edges_for_nodes(current_layer)

        next_layer = set()
        for edge in related_edges:
            src = URLNormalizer.normalize(edge['source'])
            tgt = URLNormalizer.normalize(edge['target'])
            if src not in all_nodes:
                next_layer.add(src)
            if tgt not in all_nodes:
                next_layer.add(tgt)

        if not next_layer:
            break

        all_nodes.update(next_layer)
        current_layer = next_layer

    # 收集节点信息：在 blogs 表中有记录的用真实数据，否则用占位数据
    result_blogs = {}
    for url in all_nodes:
        if url in all_blogs:
            result_blogs[url] = all_blogs[url]
        else:
            result_blogs[url] = {"name": url, "url": url, "friends": [], "is_accessible": True}

    # 从 edges 表中取所有两端都在 all_nodes 中的边
    all_related_edges = storage.get_edges_for_nodes(all_nodes)
    edge_set = set()
    result_edges = []
    for edge in all_related_edges:
        src = URLNormalizer.normalize(edge['source'])
        tgt = URLNormalizer.normalize(edge['target'])
        if src in all_nodes and tgt in all_nodes:
            key = (src, tgt)
            if key not in edge_set:
                edge_set.add(key)
                result_edges.append({"source": src, "target": tgt})

    # 移除孤立节点
    nodes_with_edges = set()
    for edge in result_edges:
        nodes_with_edges.add(edge['source'])
        nodes_with_edges.add(edge['target'])
    result_blogs = {url: blog for url, blog in result_blogs.items() if url in nodes_with_edges}

    return {"blogs": result_blogs, "edges": result_edges}

@app.get("/test_count")
async def test_count():
    blogs = storage.get_all_blogs()
    print(f"DEBUG: storage has {len(blogs)} blogs")
    print(f"DEBUG: storage.db_path = {storage.db_path}")
    return {"count": len(blogs)}

@app.get("/all_blogs")
async def get_all_blogs():
    blogs = storage.get_all_blogs()
    blog_list = []
    for url, b in blogs.items():
        blog_list.append({"name": b["name"], "url": b["url"], "is_accessible": b.get("is_accessible", True)})
    return JSONResponse(content={"blogs": blog_list, "total": len(blog_list)})

@app.get("/domain_filter")
async def get_domain_filter():
    return {
        "whitelist": domain_filter.get_whitelist(),
        "blacklist": domain_filter.get_blacklist()
    }

@app.get("/test_filter")
async def test_filter():
    return {"status": "ok"}

@app.post("/reload_storage")
async def reload_storage():
    global storage
    storage = Storage()
    return {"status": "reloaded", "count": len(storage.get_all_blogs())}

@app.post("/update_friends")
async def update_friends():
    from parser import FriendLinkParser
    from fastapi.responses import StreamingResponse
    import aiohttp
    import json as json_lib

    parser = FriendLinkParser()
    friend_pages = storage.get_all_friend_pages()
    all_existing = set(storage.get_all_blogs().keys())
    total = len(friend_pages)

    async def event_stream():
        # 发送总数
        yield f"data: {json_lib.dumps({'type': 'start', 'total': total})}\n\n"

        changes_count = 0
        for i, item in enumerate(friend_pages):
            blog_url = item["url"]
            friend_page_url = item["friend_page_url"]
            new_friends = []

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(friend_page_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            html = await response.text()
                            friends = parser.parse(html, friend_page_url)
                            friends = [URLNormalizer.normalize(f) for f in friends]

                            for friend in friends:
                                if friend not in all_existing and domain_filter.is_allowed(friend):
                                    new_friends.append(friend)
                                    all_existing.add(friend)
            except:
                pass

            has_changes = len(new_friends) > 0
            if has_changes:
                changes_count += 1

            # 推送每条结果
            yield f"data: {json_lib.dumps({'type': 'progress', 'current': i + 1, 'total': total, 'blog_url': blog_url, 'has_changes': has_changes, 'new_friends': new_friends})}\n\n"

        # 发送完成信号
        yield f"data: {json_lib.dumps({'type': 'done', 'total': total, 'changes_count': changes_count})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/blacklist")
async def add_to_blacklist(request: dict):
    url = request.get("url")
    if not url:
        return {"error": "URL is required"}

    from urllib.parse import urlparse
    domain = urlparse(url).netloc

    domain_filter.add_to_blacklist([domain])

    # 从存储中删除该博客及相关边
    storage.delete_blog(url)

    return {"status": "success", "domain": domain}
