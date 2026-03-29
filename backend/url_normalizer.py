from urllib.parse import urlparse

class URLNormalizer:
    @staticmethod
    def normalize(url):
        """将URL标准化为主域名形式"""
        try:
            parsed = urlparse(url)
            # 只保留协议和域名
            normalized = f"{parsed.scheme}://{parsed.netloc}"
            return normalized
        except:
            return url

    @staticmethod
    def same_domain(url1, url2):
        """检查两个URL是否属于同一域名"""
        try:
            domain1 = urlparse(url1).netloc.lower()
            domain2 = urlparse(url2).netloc.lower()
            return domain1 == domain2
        except:
            return False
