import json
import os
from urllib.parse import urlparse

class DomainFilter:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.filter_path = os.path.join(base_dir, 'data', 'domain_filter.json')
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.filter_path):
            with open(self.filter_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "whitelist": ["csdn.net", "cnblogs.com", "github.io", "gitee.io"],
            "blacklist": []
        }

    def _save(self):
        os.makedirs(os.path.dirname(self.filter_path), exist_ok=True)
        with open(self.filter_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_to_blacklist(self, domains):
        for domain in domains:
            if domain not in self.data["blacklist"]:
                self.data["blacklist"].append(domain)
        self._save()

    def is_allowed(self, url):
        domain = urlparse(url).netloc.lower()

        # 检查白名单
        for white in self.data["whitelist"]:
            if white in domain:
                return True

        # 检查黑名单
        for black in self.data["blacklist"]:
            if black in domain:
                return False

        return True

    def get_blacklist(self):
        return self.data["blacklist"]

    def get_whitelist(self):
        return self.data["whitelist"]
