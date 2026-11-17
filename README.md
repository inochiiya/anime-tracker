# 追番收藏（Anime Tracker）

极简日记本风格的个人番剧收藏管理网站，用于记录追番状态、观看进度、角色信息与每集笔记。前后端分离：前端为原生 HTML/CSS/JS，后端为 FastAPI + SQLite。

## 功能

- 追番状态管理（追番中 / 已看完 / 计划看 / 已弃）
- 观看进度追踪，卡片与详情页一键 [+1]
- 角色词条与每集笔记，笔记支持配图与图片灯箱
- 推荐番剧、最近更新、年度总结，以及类型 / 年份 / 搜索 / 排序 / 分页
- 数据导入与导出（含角色、笔记、更新日志）
- 外部封面图代理与本地缓存
- 管理后台（番剧 / 角色 / 笔记 / 更新日志的增删改查）
- 管理令牌鉴权，保护写操作与导入导出

## 技术栈

- 前端：HTML5 / CSS3 / 原生 JavaScript（ES6+）
- 后端：Python + FastAPI + SQLAlchemy + Pydantic
- 数据库：SQLite
- 服务器：Uvicorn
- HTTP 客户端：httpx

## 快速开始

### 方式一：一键启动（Windows）

双击 `start.bat`，脚本会自动安装依赖、释放端口、启动服务并打开浏览器。

### 方式二：手动启动

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

使用 `--host 0.0.0.0` 时，同一局域网内的设备也可通过本机 IP 访问。

### 访问地址

| 地址 | 说明 |
|------|------|
| http://localhost:8000 | 首页 |
| http://localhost:8000/list | 番剧列表 |
| http://localhost:8000/detail?id=1 | 番剧详情 |
| http://localhost:8000/admin | 管理后台 |
| http://localhost:8000/changelog | 更新日志 |
| http://localhost:8000/docs | API 文档（Swagger UI） |

## 目录结构

```
backend/        FastAPI 后端（路由、模型、CRUD、数据库迁移、图片代理）
frontend/       前端静态页面（HTML / CSS / JS / 资源）
start.bat       Windows 一键启动脚本
DEVELOPMENT.md  开发文档
最新更新.md     版本更新记录
```

## 安全与数据

- 首次启动会自动生成管理令牌并保存到 `backend/admin_token.txt`，同时在控制台打印。
- 所有写操作与导入导出接口需要携带 `X-Admin-Token` 请求头；在 `/admin` 页面输入令牌后会自动附带。
- 进度 [+1] 与状态切换无需令牌，便于日常使用。
- 数据库、备份、图片缓存与上传内容均不纳入版本管理（见 `.gitignore`）。

## 许可证

[MIT](LICENSE)
