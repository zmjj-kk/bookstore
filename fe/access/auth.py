import requests
from urllib.parse import urljoin


class Auth:
    def __init__(self, url_prefix):
        self.url_prefix = urljoin(url_prefix, "auth/")
        # 显式指定表单格式的 Content-Type（解决 415 错误的核心）
        self.form_headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

    def login(self, user_id: str, password: str, terminal: str) -> (int, str):
        data = {
            "user_id": user_id,
            "password": password,
            "terminal": terminal
        }
        url = urljoin(self.url_prefix, "login")
        # 发送表单数据并指定 headers
        r = requests.post(url, data=data, headers=self.form_headers)
        return r.status_code, r.json().get("token", "")

    def register(self, user_id: str, password: str) -> int:
        data = {
            "user_id": user_id,
            "password": password
        }
        url = urljoin(self.url_prefix, "register")
        # 显式指定表单头，确保后端正确解析
        r = requests.post(url, data=data, headers=self.form_headers)
        return r.status_code

    def password(self, user_id: str, old_password: str, new_password: str) -> int:
        data = {
            "user_id": user_id,
            "old_password": old_password,  # 下划线命名匹配后端
            "new_password": new_password
        }
        url = urljoin(self.url_prefix, "password")
        r = requests.post(url, data=data, headers=self.form_headers)
        return r.status_code

    def logout(self, user_id: str, token: str) -> int:
        data = {"user_id": user_id}
        # 合并 token 头和表单头
        headers = {**self.form_headers, "token": token}
        url = urljoin(self.url_prefix, "logout")
        r = requests.post(url, data=data, headers=headers)
        return r.status_code

    def unregister(self, user_id: str, password: str) -> int:
        data = {
            "user_id": user_id,
            "password": password
        }
        url = urljoin(self.url_prefix, "unregister")
        r = requests.post(url, data=data, headers=self.form_headers)
        return r.status_code