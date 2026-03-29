from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

class FriendLinkParser:
    SOCIAL_DOMAINS = {'twitter.com', 'github.com', 'facebook.com', 'linkedin.com', 'instagram.com', 'weibo.com', 'zhihu.com', 'pinterest.com', 'reddit.com', 'tumblr.com', 'digg.com', 'csdn.net', 'cnblogs.com'}
    FRIEND_KEYWORDS = ['友链', 'friends', 'blogroll', 'links', '朋友']

    def _normalize_url(self, url):
        """标准化URL为主域名"""
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except:
            return url

    def parse(self, html, base_url):
        soup = BeautifulSoup(html, 'html.parser')
        friends = set()

        # Strategy 1: Keyword-based section detection
        section = self._find_friend_section(soup)
        if section:
            friends.update(self._extract_links_from_section(section, base_url))

        # Strategy 2: Fallback - find link clusters
        if not friends:
            friends.update(self._find_link_clusters(soup, base_url))

        # 标准化所有URL
        return [self._normalize_url(f) for f in friends]

    def find_friend_page_url(self, html, base_url):
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.find_all('a', href=True):
            text = a.get_text().lower()
            href = a.get('href', '').lower()
            for keyword in self.FRIEND_KEYWORDS:
                if keyword in text or keyword in href:
                    full_url = urljoin(base_url, a['href'])
                    parsed = urlparse(full_url)
                    base_parsed = urlparse(base_url)
                    if parsed.netloc == base_parsed.netloc:
                        return full_url
        return None

    def _find_friend_section(self, soup):
        for keyword in self.FRIEND_KEYWORDS:
            # Search in headings
            for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                if keyword in tag.get_text().lower():
                    return tag.find_next(['div', 'section', 'ul', 'aside'])

            # Search in div/section with class or id
            for tag in soup.find_all(['div', 'section', 'aside']):
                attrs = ' '.join([str(v) for v in tag.attrs.values()]).lower()
                if keyword in attrs:
                    return tag
        return None

    def _extract_links_from_section(self, section, base_url):
        links = set()
        for a in section.find_all('a', href=True):
            url = self._normalize_url(urljoin(base_url, a['href']))
            if url and self._is_valid_friend_link(url, base_url):
                links.add(url)
        return links

    def _find_link_clusters(self, soup, base_url):
        links = set()
        # Strategy 1: Find links in lists
        for ul in soup.find_all(['ul', 'ol']):
            cluster_links = []
            for a in ul.find_all('a', href=True):
                url = self._normalize_url(urljoin(base_url, a['href']))
                if url and self._is_valid_friend_link(url, base_url):
                    cluster_links.append(url)
            if len(cluster_links) >= 3:
                links.update(cluster_links)

        # Strategy 2: If no links found, collect all valid external links
        if not links:
            for a in soup.find_all('a', href=True):
                url = self._normalize_url(urljoin(base_url, a['href']))
                if url and self._is_valid_friend_link(url, base_url):
                    links.add(url)

        return links

    def _is_valid_friend_link(self, url, base_url):
        try:
            parsed = urlparse(url)
            base_parsed = urlparse(base_url)

            # Must be external
            if parsed.netloc == base_parsed.netloc:
                return False

            # Exclude social media
            for domain in self.SOCIAL_DOMAINS:
                if domain in parsed.netloc:
                    return False

            # Must have valid scheme
            if parsed.scheme not in ['http', 'https']:
                return False

            return True
        except:
            return False

    def _normalize_url(self, url):
        if not url:
            return None
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
