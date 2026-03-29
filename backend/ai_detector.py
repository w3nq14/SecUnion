import requests
import os

class AIDetector:
    def __init__(self, api_key=None, base_url=None):
        if api_key is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"

    def detect_corporate_domains(self, urls):
        if not self.api_key:
            print("未配置API KEY，跳过AI检测")
            return []

        url_list = "\n".join(urls)

        prompt = f"""分析以下URL列表，识别出属于企业/公司的域名（如aliyun.com, microsoft.com等），排除个人博客域名。

URL列表：
{url_list}

只返回企业域名列表，每行一个域名（只要域名部分，如aliyun.com），不要解释。如果没有企业域名，返回"无"。"""

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0.3
                },
                timeout=30
            )

            if response.status_code != 200:
                print(f"AI检测失败: {response.status_code} - {response.text}")
                return []

            result = response.json()["choices"][0]["message"]["content"].strip()
            if result == "无" or not result:
                return []

            domains = []
            for line in result.split('\n'):
                line = line.strip()
                if not line or '.' not in line:
                    continue
                # 过滤掉包含中文字符的行
                if any('\u4e00' <= c <= '\u9fff' for c in line):
                    continue
                # 过滤掉包含空格、括号、逗号、破折号等的行
                if any(c in line for c in [' ', '(', ')', '，', ',', '、', '：', ':', '-']):
                    continue
                # 只保留看起来像域名的行
                if line.count('.') >= 1 and len(line) < 50:
                    domains.append(line)
            return domains
        except Exception as e:
            print(f"AI检测失败: {e}")
            return []
