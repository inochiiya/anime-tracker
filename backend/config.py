import os
import secrets

TOKEN_FILE = os.path.join(os.path.dirname(__file__), "admin_token.txt")


def _load_or_create_token() -> str:
    # 1. 环境变量优先（最高优先级）
    token = os.environ.get("ADMIN_TOKEN", "").strip()
    if token:
        return token
    # 2. 从本地文件读取
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            token = f.read().strip()
            if token:
                return token
    # 3. 生成随机令牌并保存到文件
    token = secrets.token_urlsafe(16)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(token)
    return token


ADMIN_TOKEN = _load_or_create_token()
