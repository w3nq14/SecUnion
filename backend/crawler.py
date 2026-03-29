import aiohttp
import asyncio
from parser import FriendLinkParser
from storage import Storage
from domain_filter import DomainFilter
from url_normalizer import URLNormalizer
import time
from collections import defaultdict
from bs4 import BeautifulSoup

class Crawler:
    def __init__(self, max_depth=2, max_nodes=10000, rate_limit=1.0, timeout=30, use_cache=True, ai_detector=None):
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.use_cache = use_cache
        self.parser = FriendLinkParser()
        self.storage = Storage()
        self.domain_filter = DomainFilter()
        self.visited = set()
        self.last_request_time = defaultdict(float)
        self.should_stop = False
        self.ai_detector = ai_detector

    async def fetch(self, url):
        try:
            domain = url.split('/')[2] if len(url.split('/')) > 2 else url
        except:
            return None, False

        elapsed = time.time() - self.last_request_time[domain]
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                    self.last_request_time[domain] = time.time()
                    if response.status == 200:
                        return await response.text(), True
                    return None, False
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        return None, False

    async def check_accessibility(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    return response.status == 200
        except:
            return False

    def extract_blog_name(self, html, url):
        try:
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.find('title')
            if title:
                return title.get_text().strip()
        except:
            pass
        try:
            return url.split('/')[2] if len(url.split('/')) > 2 else url
        except:
            return url

    async def crawl_recursive(self, seed_urls, progress_callback=None):
        if isinstance(seed_urls, str):
            seed_urls = [seed_urls]

        # 标准化种子URL
        seed_urls = [URLNormalizer.normalize(url) for url in seed_urls]

        queue = [(url, 0) for url in seed_urls]
        edges = []
        nodes = set()
        failed_urls = set()
        current_depth = -1

        while queue and len(self.visited) < self.max_nodes and not self.should_stop:
            url, depth = queue.pop(0)

            # 每次深度变化时进行AI检测
            if depth != current_depth and self.ai_detector and len(nodes) > 0:
                current_depth = depth
                if progress_callback:
                    progress_callback(depth, "AI检测企业域名...")
                corporate_domains = self.ai_detector.detect_corporate_domains(list(nodes))
                if corporate_domains:
                    self.domain_filter.add_to_blacklist(corporate_domains)

            # 标准化URL
            url = URLNormalizer.normalize(url)

            if depth > self.max_depth or url in self.visited or url in failed_urls:
                continue

            # 检查域名过滤
            if not self.domain_filter.is_allowed(url):
                continue

            if progress_callback:
                progress_callback(depth, url)

            # Check cache first only if use_cache is True
            if self.use_cache:
                cached = self.storage.get_blog(url)
                if cached:
                    self.visited.add(url)
                    nodes.add(url)

                    if not cached['is_accessible']:
                        failed_urls.add(url)
                        continue

                    for friend in cached['friends']:
                        friend = URLNormalizer.normalize(friend)
                        # 过滤自己指向自己
                        if URLNormalizer.same_domain(url, friend):
                            continue
                        if self.domain_filter.is_allowed(friend):
                            edges.append({"source": url, "target": friend})
                            if depth + 1 <= self.max_depth and friend not in self.visited and friend not in failed_urls:
                                nodes.add(friend)
                                queue.append((friend, depth + 1))
                    continue

            self.visited.add(url)
            nodes.add(url)

            html, is_accessible = await self.fetch(url)
            if not html:
                try:
                    domain = url.split('/')[2] if len(url.split('/')) > 2 else url
                except:
                    domain = url
                self.storage.save_blog(url, domain, [], False)
                failed_urls.add(url)
                continue

            blog_name = self.extract_blog_name(html, url)

            friend_page_url = self.parser.find_friend_page_url(html, url)
            if friend_page_url:
                friend_html, _ = await self.fetch(friend_page_url)
                if friend_html:
                    friends = self.parser.parse(friend_html, friend_page_url)
                else:
                    friends = []
            else:
                friends = self.parser.parse(html, url)

            # 标准化并过滤友链
            friends = [URLNormalizer.normalize(f) for f in friends]
            friends = [f for f in friends if self.domain_filter.is_allowed(f) and not URLNormalizer.same_domain(url, f)]

            self.storage.save_blog(url, blog_name, friends, is_accessible, friend_page_url)

            for friend in friends:
                edges.append({"source": url, "target": friend})
                if depth + 1 <= self.max_depth and friend not in self.visited and friend not in failed_urls:
                    nodes.add(friend)
                    queue.append((friend, depth + 1))

        return {"nodes": [{"id": node} for node in nodes], "edges": edges}

    def stop(self):
        self.should_stop = True
