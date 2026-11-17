# 追番收藏 - 开发文档

## 1. 项目概述

**追番收藏**是一个极简日记本风格的个人番剧收藏管理网站，用于记录和管理个人追番状态、观看进度、角色信息、每集笔记等。采用前后端分离架构，前端为纯 HTML/CSS/JS，后端为 Python FastAPI + SQLite。

**设计风格**: 浅色极简 / 莫兰迪色系 / 拍立得卡片 / 读书笔记

**在线访问**: 启动服务后访问 `http://localhost:8000`

---

## 2. 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端 | HTML5 / CSS3 / Vanilla JavaScript | ES6+ |
| 后端 | Python + FastAPI | 0.115.0 |
| ORM | SQLAlchemy | 2.0.35 |
| 数据校验 | Pydantic | 2.9.0 |
| 数据库 | SQLite | 内置 |
| 服务器 | Uvicorn | 0.30.0 |
| HTTP 客户端 | httpx | 0.27.0 |

**Python 依赖** (`backend/requirements.txt`):
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.35
pydantic==2.9.0
python-multipart==0.0.9
httpx==0.27.0
```

---

## 3. 项目结构

```
追番收藏/
├── backend/                    # 后端服务
│   ├── main.py                 # FastAPI 入口：路由、CORS、静态文件挂载、数据库迁移、图片代理
│   ├── database.py             # SQLite 引擎、会话工厂、依赖注入 get_db()
│   ├── models.py               # SQLAlchemy ORM 模型 (Anime, Character, EpisodeNote, EpisodeImage, Changelog)
│   ├── schemas.py              # Pydantic 请求/响应模型
│   ├── crud.py                 # 数据库 CRUD 操作封装 (通用 update/delete 辅助函数)
│   ├── requirements.txt        # Python 依赖清单
│   ├── cache/                  # 图片代理缓存目录 (自动创建，7天TTL)
│   └── uploads/                # 用户上传图片目录 (自动创建)
│
├── frontend/                   # 前端静态文件
│   ├── index.html              # 首页
│   ├── list.html               # 番剧列表页
│   ├── detail.html             # 番剧详情页
│   ├── admin.html              # 管理后台
│   ├── changelog.html          # 更新日志页
│   │
│   ├── css/
│   │   ├── common.css          # 设计系统：CSS 变量、全局重置、导航栏、卡片、分页、Toast、Modal、表单、按钮
│   │   ├── animations.css      # 关键帧动画：fadeInUp、fadeIn
│   │   ├── home.css            # 首页样式
│   │   ├── list.css            # 列表页样式
│   │   ├── detail.css          # 详情页样式：读书笔记布局、角色卡片、集数笔记、进度条
│   │   ├── admin.css           # 管理页样式：表格、标签页、子表单、角色/笔记/日志管理
│   │   └── changelog.css       # 更新日志页样式：时间线布局
│   │
│   ├── js/
│   │   ├── api.js              # 统一 API 层：apiGet/apiPost/apiPut/apiDelete
│   │   ├── common.js           # 公共工具：escapeHtml、状态映射、卡片生成器、状态下拉、Toast、分页
│   │   ├── home.js             # 首页逻辑：Promise.all 并行加载统计、正在追列表、最近更新
│   │   ├── list.js             # 列表页逻辑：筛选联动、URL 同步、防抖搜索
│   │   ├── detail.js           # 详情页逻辑：模块化渲染、角色展示、集数笔记、lightbox
│   │   ├── admin.js            # 管理页逻辑：标签页、角色/笔记/日志 CRUD、导入导出
│   │   └── changelog.js        # 更新日志页逻辑
│   │
│   └── assets/
│       ├── logo.svg            # 网站 Logo
│       └── default-cover.svg   # 默认封面占位图
│
├── start.bat                   # Windows 一键启动脚本 (含端口冲突处理)
├── DEVELOPMENT.md              # 本文档
└── 最新更新.md                  # 版本更新记录
```

---

## 4. 设计风格

### 4.1 整体风格定义

采用**极简日记本 / 私人书架**风格。米白色纸张底色搭配莫兰迪色系，营造温馨、安静、有留白的阅读氛围。卡片采用拍立得风格（封面 + 白色信息区），详情页采用读书笔记布局。

### 4.2 色彩系统

所有颜色通过 CSS 自定义属性定义在 `common.css` 的 `:root` 中，全站统一引用变量，无硬编码色值。

#### 背景色
| 变量 | 色值 | 用途 |
|------|------|------|
| `--bg-primary` | `#F9F9F7` | 页面主背景 (米白纸张色) |
| `--bg-secondary` | `#FFFFFF` | 纯白面板、导航栏、下拉菜单 |
| `--bg-card` | `#FFFFFF` | 卡片背景 |
| `--bg-card-hover` | `#FAFAF8` | 卡片悬停态、表格行悬停 |
| `--bg-input` | `#F5F5F3` | 输入框背景 |

#### 文字色
| 变量 | 色值 | 用途 |
|------|------|------|
| `--text-primary` | `#2C2C2C` | 主文字 (深碳灰) |
| `--text-secondary` | `#808080` | 次要文字 (中灰) |
| `--text-accent` | `#6B8E7B` | 强调文字 (豆沙绿) |

#### 强调色 (莫兰迪色系)
| 变量 | 色值 | 用途 |
|------|------|------|
| `--accent-primary` | `#6B8E7B` | 主强调色 (豆沙绿) |
| `--accent-secondary` | `#A4C6D9` | 次强调色 (灰蓝) |
| `--accent-warm` | `#D4A574` | 暖色强调 (暖棕，用于收藏、私人标签) |

#### 状态色 (低饱和度)
| 变量 | 色值 | 对应状态 |
|------|------|----------|
| `--status-watching` | `#8FBC8F` | 追番中 (薄荷绿) |
| `--status-completed` | `#EEDC82` | 已看完 (麦秆黄) |
| `--status-planned` | `#A4C6D9` | 计划看 (灰蓝) |
| `--status-dropped` | `#D3D3D3` | 已弃 (浅灰) |

#### 边框与阴影
| 变量 | 值 | 用途 |
|------|------|------|
| `--border-light` | `#E8E8E4` | 通用边框 |
| `--border-input` | `#D5D5D0` | 输入框边框 |
| `--shadow-card` | `0 2px 8px rgba(0,0,0,0.04)` | 卡片默认阴影 |
| `--shadow-card-hover` | `0 8px 24px rgba(0,0,0,0.08)` | 卡片悬停阴影 |

### 4.3 字体

```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

body { font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif; line-height: 1.7; }
h1, h2, h3, .section-title { font-family: 'Noto Serif SC', serif; }
```

- **正文**: Noto Sans SC (无衬线)，行高 1.7，阅读舒适
- **标题**: Noto Serif SC (衬线)，增加书卷气

### 4.4 圆角

| 变量 | 值 | 用途 |
|------|------|------|
| `--radius-sm` | `6px` | 按钮、输入框、标签 |
| `--radius-md` | `10px` | 卡片、面板 |
| `--radius-lg` | `16px` | 模态框 |
| `--nav-height` | `56px` | 导航栏高度 |

### 4.5 核心 UI 组件

#### 导航栏 (Navbar)
- 固定顶部 (`position: fixed`)，高度 56px
- 使用 `var(--bg-secondary)` 背景，底部 1px 浅灰分割线
- Logo 使用 SVG 图标 + 深色文字
- 当前页链接底部有豆沙绿指示线

#### 番剧卡片 (拍立得风格)
- 白色卡片背景，极淡阴影
- 封面图比例 3:4，无渐变遮罩
- 封面下方白色信息区 (`.card-info`)：标题 + 状态切换按钮 + 进度 + 评分
- 状态圆点可点击，弹出下拉菜单一键切换状态
- 追番中卡片显示进度文字 (如 "5/12 集") 和 [+1] 按钮
- hover 时上浮 4px + 阴影加深

#### 状态切换 (Status Switch)
- 卡片和详情页均可点击状态指示器
- 弹出浮层列出 4 种状态，当前状态高亮
- 切换后即时调用 API 更新，无需进入管理后台
- 使用 `position: fixed` 定位，不受卡片 `overflow: hidden` 影响

#### 分页器 (Pagination)
- 居中排列的按钮组，使用 `.pagination-dots` 类显示省略号
- 当前页使用主强调色背景

#### Toast 通知
- 固定在右上角，自动去重 (相同消息不重复显示)
- 两种类型：success (豆沙绿)、error (暖棕)
- 3 秒后自动消失

#### 模态框 (Modal)
- 全屏半透明遮罩，居中弹出，白色背景
- 管理后台模态框内含标签页 (基本信息/角色/集数笔记)

#### 表单 (Form)
- 输入框浅灰背景，focus 时豆沙绿边框
- 双列布局 (`grid-template-columns: 1fr 1fr`)，移动端单列
- 提交按钮防重复点击 (提交时自动 disabled)

### 4.6 动画系统

定义在 `animations.css` 中：

| 动画名 | 效果 | 用途 |
|--------|------|------|
| `fadeInUp` | 从下方 24px 淡入上移 | 卡片、内容区块入场 |
| `fadeIn` | 透明度 0→1 | 通用淡入 |

**交错延迟类**: `.stagger-1` 到 `.stagger-8`，每级延迟 50ms。

### 4.7 响应式断点

| 断点 | 网格列数 | 其他调整 |
|------|----------|----------|
| > 1200px | 5 列 | 默认桌面布局 |
| ≤ 1200px | 4 列 | - |
| ≤ 900px | 3 列 | 详情页改为上下布局 |
| ≤ 600px | 2 列 | 筛选栏垂直堆叠、表单单列布局 |

---

## 5. 数据库设计

### 5.1 数据模型

5 张表，定义在 `backend/models.py`：

#### Anime 表 (核心)
| 字段 | 类型 | 索引 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | 主键，自增 |
| `title` | String(200) | ✓ | 番剧名称 |
| `title_jp` | String(200) | - | 日文原名 |
| `cover_url` | String(500) | - | 封面图片 URL |
| `synopsis` | Text | - | 简介/剧情 |
| `episodes` | Integer | - | 总集数 |
| `status` | String(20) | ✓ | 追番状态 |
| `genre` | String(200) | - | 类型标签 (逗号分隔) |
| `year` | Integer | ✓ | 放送年份 |
| `season` | String(10) | - | 季度 |
| `rating` | Float | ✓ | 个人评分 (0-10) |
| `studio` | String(100) | - | 制作公司 |
| `air_date` | String(20) | - | 首播日期 |
| `link_url` | String(500) | - | 外部链接 |
| `notes` | Text | - | 个人备注 |
| `is_featured` | Integer | ✓ | 是否推荐 (0/1) |
| `watched_episodes` | Integer | - | 已看集数 |
| `start_date` | String(20) | - | 开始观看日期 |
| `finish_date` | String(20) | - | 看完日期 |
| `is_favorite` | Integer | - | 是否最爱 (0/1) |
| `personal_tags` | String(300) | - | 私人标签 (逗号分隔) |
| `created_at` | DateTime | - | 创建时间 |
| `updated_at` | DateTime | ✓ | 更新时间 (默认排序字段) |

#### Character 表 (角色)
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | PK |
| `anime_id` | Integer | FK → Anime.id (级联删除) |
| `name` | String(100) | 角色名 |
| `name_jp` | String(100) | 日文名 |
| `avatar_url` | String(500) | 头像 URL |
| `role` | String(50) | 角色身份 (主角/配角/路人) |
| `description` | Text | 角色简介 |
| `sort_order` | Integer | 排序权重 |

#### EpisodeNote 表 (集数笔记)
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | PK |
| `anime_id` | Integer | FK → Anime.id (级联删除) |
| `episode` | Integer | 集数 (与 anime_id 联合唯一) |
| `note` | Text | 笔记内容 |
| `rating` | Float | 单集评分 (0-10) |
| `watched_date` | String(20) | 观看日期 |

#### EpisodeImage 表 (笔记图片)
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | PK |
| `note_id` | Integer | FK → EpisodeNote.id (级联删除) |
| `filename` | String(200) | 存储文件名 (UUID) |
| `original_name` | String(200) | 原始文件名 |

#### Changelog 表 (更新日志)
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | PK |
| `title` | String(200) | 日志标题 |
| `content` | Text | 日志内容 |
| `version` | String(20) | 版本号 |
| `created_at` | DateTime | 创建时间 |

### 5.2 关系与约束

- Anime → Character: 一对多，级联删除
- Anime → EpisodeNote: 一对多，级联删除
- EpisodeNote → EpisodeImage: 一对多，级联删除
- EpisodeNote: `UniqueConstraint(anime_id, episode)` 防止重复笔记
- 所有关系使用 `lazy="selectin"` 预加载，避免 N+1 查询

### 5.3 数据库迁移

启动时自动检测旧数据库是否缺少新字段，通过 `PRAGMA table_info(anime)` 查询列信息，对缺失字段执行 `ALTER TABLE anime ADD COLUMN ...`。支持从 `anime_old.db` 自动导入旧数据。

---

## 6. 后端 API 设计

### 6.1 基础配置

- **CORS**: 允许所有来源
- **静态文件**: `/css`、`/js`、`/assets`
- **HTTP 客户端**: 全局复用 `httpx.AsyncClient` (连接池)
- **图片代理缓存**: `backend/cache/`，7 天 TTL 自动过期

### 6.2 RESTful 接口

#### 番剧 CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/anime` | 列表 (支持 status/genre/year/min_rating/search/sort_by/order/page/page_size) |
| GET | `/api/anime/{id}` | 详情 |
| POST | `/api/anime` | 新增 |
| PUT | `/api/anime/{id}` | 更新 (部分更新) |
| DELETE | `/api/anime/{id}` | 删除 |
| PUT | `/api/anime/{id}/progress` | 进度+1 (自动完成) |

#### 角色 CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/anime/{id}/characters` | 获取某番所有角色 |
| POST | `/api/anime/{id}/characters` | 新增角色 |
| PUT | `/api/characters/{id}` | 编辑角色 |
| DELETE | `/api/characters/{id}` | 删除角色 |

#### 集数笔记 CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/anime/{id}/episodes` | 获取某番所有集数笔记 |
| POST | `/api/anime/{id}/episodes` | 新增笔记 |
| PUT | `/api/episodes/{id}` | 编辑笔记 |
| DELETE | `/api/episodes/{id}` | 删除笔记 |
| POST | `/api/episodes/{id}/images` | 上传图片到笔记 |
| DELETE | `/api/episode-images/{id}` | 删除图片 |
| GET | `/api/uploads/{filename}` | 访问上传的图片 |

#### 更新日志 CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/changelogs` | 获取所有日志 |
| POST | `/api/changelogs` | 新增日志 |
| PUT | `/api/changelogs/{id}` | 编辑日志 |
| DELETE | `/api/changelogs/{id}` | 删除日志 |

#### 统计与工具

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 统计数据 (单次聚合查询) |
| GET | `/api/genres` | 类型列表 |
| GET | `/api/years` | 年份列表 |
| GET | `/api/yearly/{year}` | 年度总结 (DB 侧排序) |
| GET | `/api/anime/featured/list` | 推荐番剧 |
| GET | `/api/anime/recent/list` | 最近更新 |
| GET | `/api/export` | 导出全部数据 (含角色/笔记/日志) |
| POST | `/api/import` | 导入数据 (支持旧格式和新格式) |
| GET | `/api/proxy/cover` | 图片代理 (带缓存+TTL) |

### 6.3 页面路由

| 路径 | 返回文件 | 说明 |
|------|----------|------|
| `/` | `index.html` | 首页 |
| `/list` | `list.html` | 番剧列表 |
| `/detail` | `detail.html` | 番剧详情 (`?id=1`) |
| `/admin` | `admin.html` | 管理后台 |
| `/changelog` | `changelog.html` | 更新日志 |
| `/docs` | Swagger UI | API 文档 |

---

## 7. 前端页面与功能

### 7.1 首页 (`/`)

- **问候区**: "欢迎回来" + 年度统计 (并行加载 stats + yearly)
- **正在追**: 水平卡片列表，每张带 [+1] 进度按钮和状态切换
- **最近更新**: 响应式网格

### 7.2 番剧列表页 (`/list`)

- **筛选栏**: 搜索 (防抖 300ms) + 状态/类型/年份/排序下拉
- **结果网格**: 5/4/3/2 列响应式，追番中卡片带 [+1] 和状态切换
- **分页**: 20 条/页，URL 同步筛选状态

### 7.3 番剧详情页 (`/detail?id=1`)

采用**读书笔记**风格布局，模块化渲染：

- **封面区** (左侧): 封面图 + 最爱徽章
- **信息区** (右侧):
  - 标题 + 日文名
  - 状态徽章 (可点击切换) + 评分
  - 观看进度条 + [+1 集] 按钮
  - 类型标签 + 私人标签
  - 信息网格 (制作公司、放送时间、日期等)
  - **角色卡片** (头像 + 名字 + 身份)
  - 简介 (XSS 安全渲染)
  - 个人备注 (便签样式)
  - **每集笔记** (集数标签 + 评分 + 笔记 + 图片网格 + Lightbox)
  - 外部链接

### 7.4 管理后台 (`/admin`)

- **标签页**: 番剧管理 / 更新日志
- **番剧管理**: 表格 + 新增/编辑/删除 + 导入导出
- **编辑弹窗内嵌标签页**: 基本信息 / 角色管理 / 集数笔记管理
- **角色管理**: 列表 + 添加/编辑/删除
- **集数笔记管理**: 列表 + 添加/编辑/删除 + 图片上传
- **更新日志管理**: 列表 + 新增/编辑/删除

### 7.5 更新日志页 (`/changelog`)

- 时间线布局，展示版本号、日期、内容

---

## 8. 公共 JavaScript 模块

### 8.1 `api.js` - API 封装层

| 函数 | 方法 | 说明 |
|------|------|------|
| `apiGet(path, params)` | GET | 自动拼接查询参数，过滤空值 |
| `apiPost(path, data)` | POST | JSON 请求体 |
| `apiPut(path, data)` | PUT | JSON 请求体 |
| `apiDelete(path)` | DELETE | - |

### 8.2 `common.js` - 公共工具

| 函数 | 说明 |
|------|------|
| `escapeHtml(str)` | XSS 防护，将用户内容转义后安全插入 innerHTML |
| `getProxiedUrl(url)` | 将外部图片 URL 转为代理 URL |
| `createAnimeCard(anime, showProgressBtn)` | 创建拍立得风格卡片 (含状态切换) |
| `showStatusDropdown(rect, anime, card, showProgressBtn)` | 卡片状态下拉菜单 |
| `showDetailStatusDropdown(e, animeId)` | 详情页状态下拉菜单 |
| `showToast(message, type)` | Toast 通知 (自动去重) |
| `createPagination(total, page, pageSize, onChange)` | 分页器 |

---

## 9. 启动方式

### 方式一：一键启动 (Windows)

双击 `start.bat`，自动检测并释放端口、安装依赖、启动服务、打开浏览器。

### 方式二：手动启动

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### 访问地址

| 地址 | 说明 |
|------|------|
| `http://localhost:8000` | 首页 |
| `http://localhost:8000/list` | 番剧列表 |
| `http://localhost:8000/detail?id=1` | 番剧详情 |
| `http://localhost:8000/admin` | 管理后台 |
| `http://localhost:8000/changelog` | 更新日志 |
| `http://localhost:8000/docs` | API 文档 |

---

## 10. 安全措施

- **XSS 防护**: 所有用户输入内容通过 `escapeHtml()` 转义后再插入 DOM
- **图片代理**: 外部图片通过后端代理，防盗链 + 本地缓存
- **提交保护**: 表单提交时按钮自动 disabled，防止双击重复提交
- **唯一约束**: `EpisodeNote(anime_id, episode)` 联合唯一，防止重复笔记

---

## 11. 性能优化

- **数据库索引**: `status`、`year`、`rating`、`updated_at`、`is_featured` 均已建立索引
- **单次聚合查询**: `/api/stats` 使用 `CASE WHEN` 条件聚合，1 次查询替代 6 次
- **genre 筛选**: SQL 层 `LIKE` 精确匹配逗号分隔标签，避免全表加载
- **预加载**: 所有关系使用 `lazy="selectin"`，避免 N+1 查询
- **HTTP 连接池**: 全局复用 `httpx.AsyncClient`，图片代理复用 TCP 连接
- **图片缓存 TTL**: 代理缓存 7 天自动过期，防止磁盘无限增长
- **浏览器缓存**: 代理响应带 `Cache-Control: public, max-age=604800`
- **并行加载**: 首页使用 `Promise.all` 并行请求，详情页使用 `Promise.allSettled` 容错
- **通用 CRUD 辅助**: `_update_one`/`_delete_one` 消除重复代码

---

## 12. 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `backend/main.py` | 523 | FastAPI 入口、路由、迁移、图片代理 |
| `backend/database.py` | 22 | 数据库引擎和会话 |
| `backend/models.py` | 90 | 5 个 ORM 模型 + 索引 + 关系 |
| `backend/schemas.py` | 136 | Pydantic 模型 (含嵌套响应) |
| `backend/crud.py` | 271 | CRUD + 通用辅助 + 导入导出 |
| `frontend/css/common.css` | 636 | 设计系统 (全变量驱动) |
| `frontend/css/animations.css` | 28 | 动画定义 |
| `frontend/css/home.css` | 59 | 首页样式 |
| `frontend/css/list.css` | 74 | 列表页样式 |
| `frontend/css/detail.css` | 450 | 详情页样式 (角色+笔记+lightbox) |
| `frontend/css/admin.css` | 418 | 管理页样式 (标签页+子表单) |
| `frontend/css/changelog.css` | 90 | 更新日志样式 |
| `frontend/js/api.js` | 48 | API 封装 |
| `frontend/js/common.js` | 326 | 公共工具 + 卡片 + 状态切换 + Toast |
| `frontend/js/home.js` | 59 | 首页逻辑 |
| `frontend/js/list.js` | 125 | 列表页逻辑 |
| `frontend/js/detail.js` | 220 | 详情页逻辑 (模块化渲染) |
| `frontend/js/admin.js` | 616 | 管理页逻辑 (多实体 CRUD) |
| `frontend/js/changelog.js` | 33 | 更新日志逻辑 |
| `frontend/index.html` | 55 | 首页 HTML |
| `frontend/list.html` | 79 | 列表页 HTML |
| `frontend/detail.html` | 45 | 详情页 HTML |
| `frontend/admin.html` | 358 | 管理页 HTML |
| `frontend/changelog.html` | 45 | 更新日志 HTML |
| **合计** | **~4800** | - |
