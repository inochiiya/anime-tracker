import asyncio
import ipaddress
import json
import os
import shutil
import socket
import time
import uuid
from hashlib import md5
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func, case, text, inspect

from database import get_db, init_db, SessionLocal
from models import Anime, Character, EpisodeNote, EpisodeImage, Changelog
from schemas import (
    AnimeCreate, AnimeUpdate, AnimeResponse, StatusUpdate,
    CharacterCreate, CharacterUpdate, CharacterResponse,
    EpisodeNoteCreate, EpisodeNoteUpdate, EpisodeNoteResponse,
    EpisodeImageResponse,
    ChangelogCreate, ChangelogUpdate, ChangelogResponse,
)
from config import ADMIN_TOKEN
import crud

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
UPLOAD_DIR = BACKEND_DIR / "uploads"
CACHE_DIR = BACKEND_DIR / "cache"
UPLOAD_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

app = FastAPI(title="追番收藏 API")

# 说明：本项目前后端同源（均由 FastAPI 提供服务），无需 CORS。
# 移除 allow_origins=["*"] 可防止其他网站跨域调用本 API。

app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

# Created lazily inside the running event loop, then reused as a connection pool.
http_client: Optional[httpx.AsyncClient] = None

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if request.method in MUTATING_METHODS:
        fetch_site = request.headers.get("sec-fetch-site", "").lower()
        if fetch_site == "cross-site":
            return JSONResponse(status_code=403, content={"detail": "拒绝跨站写入请求"})

        origin = request.headers.get("origin")
        if origin:
            parsed_origin = urlparse(origin)
            try:
                origin_port = parsed_origin.port or (443 if parsed_origin.scheme == "https" else 80)
            except ValueError:
                return JSONResponse(status_code=403, content={"detail": "请求来源不受信任"})
            request_port = request.url.port or (443 if request.url.scheme == "https" else 80)
            if (
                parsed_origin.scheme not in {"http", "https"}
                or parsed_origin.hostname != request.url.hostname
                or origin_port != request_port
            ):
                return JSONResponse(status_code=403, content={"detail": "请求来源不受信任"})

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
        "connect-src 'self'; object-src 'none'; base-uri 'self'; "
        "frame-ancestors 'self'; form-action 'self'",
    )
    if request.scope.get("path", "").startswith("/api/") and "cache-control" not in response.headers:
        response.headers["Cache-Control"] = "no-store"
    return response


# ─── Admin Auth ───────────────────────────────────────────────

def require_admin(x_admin_token: Optional[str] = Header(None)):
    """校验管理令牌，保护写操作。令牌通过 X-Admin-Token 请求头传入。"""
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="需要管理员令牌")


@app.get("/api/auth/check", dependencies=[Depends(require_admin)])
def auth_check():
    """用于前端校验管理令牌是否有效。"""
    return {"ok": True}


# ─── API Routes ───────────────────────────────────────────────


@app.get("/api/anime")
def list_anime(
    status: Optional[str] = None,
    genre: Optional[str] = None,
    year: Optional[int] = None,
    min_rating: Optional[float] = None,
    search: Optional[str] = None,
    sort_by: str = "updated_at",
    order: str = "desc",
    page: int = 1,
    page_size: int = 24,
    db: Session = Depends(get_db),
):
    filters = {
        "status": status,
        "genre": genre,
        "year": year,
        "min_rating": min_rating,
        "search": search,
    }
    query = crud.get_anime_list(db, filters)

    sort_column = getattr(Anime, sort_by, Anime.updated_at)
    query = query.order_by(
        sort_column.desc() if order == "desc" else sort_column.asc()
    )

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@app.get("/api/anime/featured/list")
def get_featured(limit: int = 8, db: Session = Depends(get_db)):
    return (
        db.query(Anime)
        .filter(Anime.is_featured == 1)
        .order_by(Anime.rating.desc())
        .limit(limit)
        .all()
    )


@app.get("/api/anime/recent/list")
def get_recent(limit: int = 12, db: Session = Depends(get_db)):
    return db.query(Anime).order_by(Anime.updated_at.desc()).limit(limit).all()


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    row = db.query(
        sql_func.count(Anime.id).label("total"),
        sql_func.sum(case((Anime.status == "watching", 1), else_=0)).label("watching"),
        sql_func.sum(case((Anime.status == "completed", 1), else_=0)).label("completed"),
        sql_func.sum(case((Anime.status == "planned", 1), else_=0)).label("planned"),
        sql_func.sum(case((Anime.status == "dropped", 1), else_=0)).label("dropped"),
        sql_func.avg(case((Anime.rating > 0, Anime.rating), else_=None)).label("avg_rating"),
    ).one()
    return {
        "total": row.total,
        "watching": row.watching,
        "completed": row.completed,
        "planned": row.planned,
        "dropped": row.dropped,
        "avg_rating": round(row.avg_rating, 1) if row.avg_rating else 0,
    }


@app.get("/api/genres")
def get_genres(db: Session = Depends(get_db)):
    rows = db.query(Anime.genre).filter(Anime.genre.isnot(None), Anime.genre != "").all()
    genre_set = set()
    for (genre_str,) in rows:
        for g in genre_str.split(","):
            g = g.strip()
            if g:
                genre_set.add(g)
    return sorted(genre_set)


@app.get("/api/years")
def get_years(db: Session = Depends(get_db)):
    rows = (
        db.query(Anime.year)
        .filter(Anime.year.isnot(None))
        .distinct()
        .order_by(Anime.year.desc())
        .all()
    )
    return [r[0] for r in rows]


@app.get("/api/anime/{anime_id}", response_model=AnimeResponse)
def get_anime(anime_id: int, db: Session = Depends(get_db)):
    anime = crud.get_anime(db, anime_id)
    if not anime:
        raise HTTPException(status_code=404, detail="番剧不存在")
    return anime


@app.post("/api/anime", response_model=AnimeResponse, dependencies=[Depends(require_admin)])
def create_anime(anime: AnimeCreate, db: Session = Depends(get_db)):
    return crud.create_anime(db, anime)


@app.put("/api/anime/{anime_id}", response_model=AnimeResponse, dependencies=[Depends(require_admin)])
def update_anime(anime_id: int, anime: AnimeUpdate, db: Session = Depends(get_db)):
    current = crud.get_anime(db, anime_id)
    if not current:
        raise HTTPException(status_code=404, detail="番剧不存在")
    changes = anime.model_dump(exclude_unset=True)
    episodes = changes.get("episodes", current.episodes)
    watched_episodes = changes.get("watched_episodes", current.watched_episodes)
    if (
        episodes is not None
        and watched_episodes is not None
        and watched_episodes > episodes
    ):
        raise HTTPException(status_code=422, detail="已看集数不能超过总集数")
    result = crud.update_anime(db, anime_id, anime)
    return result


@app.delete("/api/anime/{anime_id}", dependencies=[Depends(require_admin)])
def delete_anime(anime_id: int, db: Session = Depends(get_db)):
    result = crud.delete_anime(db, anime_id)
    if not result:
        raise HTTPException(status_code=404, detail="番剧不存在")
    return {"message": "删除成功"}


@app.put(
    "/api/anime/{anime_id}/status",
    response_model=AnimeResponse,
    dependencies=[Depends(require_admin)],
)
def set_status(anime_id: int, data: StatusUpdate, db: Session = Depends(get_db)):
    """修改追番状态，用于首页和详情页的一键切换。"""
    result = crud.set_status(db, anime_id, data.status)
    if not result:
        raise HTTPException(status_code=404, detail="番剧不存在")
    return result


@app.put(
    "/api/anime/{anime_id}/progress",
    response_model=AnimeResponse,
    dependencies=[Depends(require_admin)],
)
def increment_progress(anime_id: int, db: Session = Depends(get_db)):
    result = crud.increment_progress(db, anime_id)
    if not result:
        raise HTTPException(status_code=404, detail="番剧不存在")
    return result


@app.get("/api/export", dependencies=[Depends(require_admin)])
def export_data(db: Session = Depends(get_db)):
    raw = crud.export_all(db)
    changelogs = []
    anime_list = []
    for item in raw:
        if "_changelogs" in item:
            changelogs = item["_changelogs"]
        else:
            anime_list.append(item)
    characters = []
    episode_notes = []
    for a in anime_list:
        for c in a.pop("characters", []):
            characters.append(c)
        for n in a.pop("episode_notes", []):
            episode_notes.append(n)
    data = {"anime": anime_list, "characters": characters, "episode_notes": episode_notes, "changelogs": changelogs}
    return JSONResponse(content=data, headers={
        "Content-Disposition": "attachment; filename=anime_export.json"
    })


@app.post("/api/import", dependencies=[Depends(require_admin)])
async def import_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
        if isinstance(data, list):
            count = crud.import_data(db, data)
            return {"message": f"成功导入 {count} 条数据"}
        elif isinstance(data, dict):
            result = crud.import_full(db, data)
            return {"message": f"导入完成: {result}"}
        else:
            raise HTTPException(status_code=400, detail="无效的数据格式")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 文件")


@app.get("/api/yearly/{year}")
def yearly_summary(year: int, db: Session = Depends(get_db)):
    top3 = (
        db.query(Anime)
        .filter(Anime.status == "completed", Anime.year == year)
        .order_by(Anime.rating.desc())
        .limit(3)
        .all()
    )
    row = db.query(
        sql_func.count(Anime.id).label("count"),
        sql_func.coalesce(sql_func.sum(Anime.episodes), 0).label("total_episodes"),
    ).filter(Anime.status == "completed", Anime.year == year).one()
    return {
        "year": year,
        "count": row.count,
        "total_episodes": row.total_episodes,
        "top3": [{"title": a.title, "rating": a.rating, "cover_url": a.cover_url} for a in top3],
    }


# ─── Image Proxy ──────────────────────────────────────────────

CACHE_TTL = 7 * 24 * 3600
MAX_PROXY_SIZE = 8 * 1024 * 1024
MAX_PROXY_REDIRECTS = 3
ALLOWED_PROXY_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _get_http_client() -> httpx.AsyncClient:
    global http_client
    if http_client is None or http_client.is_closed:
        http_client = httpx.AsyncClient(timeout=10, follow_redirects=False)
    return http_client


def _detect_mime(data: bytes) -> str:
    if data[:8] == b'\x89PNG\r\n\x1a\n': return "image/png"
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP': return "image/webp"
    if data[:4] == b'GIF8': return "image/gif"
    if data[:2] == b'\xff\xd8': return "image/jpeg"
    return ""


def _parse_remote_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="仅支持公开的 HTTP(S) 图片地址")
    try:
        port = parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="图片地址端口无效") from exc
    if parsed.username or parsed.password or port not in {None, 80, 443}:
        raise HTTPException(status_code=400, detail="图片地址包含不允许的认证信息或端口")

    try:
        literal_ip = ipaddress.ip_address(parsed.hostname)
        if not literal_ip.is_global:
            raise HTTPException(status_code=400, detail="不允许访问本机或内网地址")
    except ValueError:
        literal_ip = None
    return parsed, port, literal_ip


async def _validate_remote_url(url: str) -> None:
    parsed, port, literal_ip = _parse_remote_url(url)
    if literal_ip is not None:
        return

    try:
        addresses = await asyncio.to_thread(
            socket.getaddrinfo,
            parsed.hostname,
            port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail="图片域名无法解析") from exc

    for ip in {ipaddress.ip_address(address[4][0]) for address in addresses}:
        if not ip.is_global:
            raise HTTPException(status_code=400, detail="不允许访问本机或内网地址")


async def _fetch_remote_image(url: str) -> tuple[bytes, str]:
    current_url = url
    for _ in range(MAX_PROXY_REDIRECTS + 1):
        await _validate_remote_url(current_url)
        try:
            async with _get_http_client().stream("GET", current_url, headers={"Referer": ""}) as resp:
                if resp.status_code in {301, 302, 303, 307, 308}:
                    location = resp.headers.get("location")
                    if not location:
                        raise HTTPException(status_code=502, detail="图片重定向无效")
                    current_url = urljoin(current_url, location)
                    continue
                if resp.status_code != 200:
                    raise HTTPException(status_code=502, detail="图片获取失败")

                content_length = resp.headers.get("content-length")
                if content_length:
                    try:
                        if int(content_length) > MAX_PROXY_SIZE:
                            raise HTTPException(status_code=413, detail="远程图片超过 8MB 限制")
                    except ValueError:
                        pass

                chunks = []
                total = 0
                async for chunk in resp.aiter_bytes():
                    total += len(chunk)
                    if total > MAX_PROXY_SIZE:
                        raise HTTPException(status_code=413, detail="远程图片超过 8MB 限制")
                    chunks.append(chunk)

                content = b"".join(chunks)
                detected_mime = _detect_mime(content)
                declared_mime = resp.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                mime = detected_mime or declared_mime
                if mime not in ALLOWED_PROXY_MIME or not detected_mime:
                    raise HTTPException(status_code=415, detail="远程内容不是支持的图片格式")
                return content, mime
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail="图片请求失败") from exc

    raise HTTPException(status_code=502, detail="图片重定向次数过多")


@app.get("/api/proxy/cover")
async def proxy_cover(url: str):
    cache_key = md5(url.encode()).hexdigest()
    cache_path = CACHE_DIR / f"{cache_key}.img"
    meta_path = CACHE_DIR / f"{cache_key}.meta"

    if cache_path.exists():
        # TTL check: re-fetch if cache is stale
        age = time.time() - cache_path.stat().st_mtime
        if age < CACHE_TTL:
            content = cache_path.read_bytes()
            mime = _detect_mime(content)
            if mime in ALLOWED_PROXY_MIME:
                return Response(
                    content=content,
                    media_type=mime,
                    headers={"Cache-Control": "public, max-age=604800"},
                )
            cache_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)

    content, mime = await _fetch_remote_image(url)
    cache_path.write_bytes(content)
    meta_path.write_text(mime, encoding="utf-8")
    return Response(
        content=content,
        media_type=mime,
        headers={"Cache-Control": "public, max-age=604800"},
    )


# ─── Character Routes ─────────────────────────────────────────

@app.get("/api/anime/{anime_id}/characters", response_model=list[CharacterResponse])
def list_characters(anime_id: int, db: Session = Depends(get_db)):
    return crud.get_characters(db, anime_id)


@app.post("/api/anime/{anime_id}/characters", response_model=CharacterResponse, dependencies=[Depends(require_admin)])
def create_character(anime_id: int, data: CharacterCreate, db: Session = Depends(get_db)):
    if not crud.get_anime(db, anime_id):
        raise HTTPException(status_code=404, detail="番剧不存在")
    return crud.create_character(db, anime_id, data)


@app.put("/api/characters/{char_id}", response_model=CharacterResponse, dependencies=[Depends(require_admin)])
def update_character(char_id: int, data: CharacterUpdate, db: Session = Depends(get_db)):
    result = crud.update_character(db, char_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="角色不存在")
    return result


@app.delete("/api/characters/{char_id}", dependencies=[Depends(require_admin)])
def delete_character(char_id: int, db: Session = Depends(get_db)):
    result = crud.delete_character(db, char_id)
    if not result:
        raise HTTPException(status_code=404, detail="角色不存在")
    return {"message": "删除成功"}


# ─── Episode Note Routes ─────────────────────────────────────

@app.get("/api/anime/{anime_id}/episodes", response_model=list[EpisodeNoteResponse])
def list_episode_notes(anime_id: int, db: Session = Depends(get_db)):
    return crud.get_episode_notes(db, anime_id)


@app.post("/api/anime/{anime_id}/episodes", response_model=EpisodeNoteResponse, dependencies=[Depends(require_admin)])
def create_episode_note(anime_id: int, data: EpisodeNoteCreate, db: Session = Depends(get_db)):
    if not crud.get_anime(db, anime_id):
        raise HTTPException(status_code=404, detail="番剧不存在")
    return crud.create_episode_note(db, anime_id, data)


@app.put("/api/episodes/{note_id}", response_model=EpisodeNoteResponse, dependencies=[Depends(require_admin)])
def update_episode_note(note_id: int, data: EpisodeNoteUpdate, db: Session = Depends(get_db)):
    result = crud.update_episode_note(db, note_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return result


@app.delete("/api/episodes/{note_id}", dependencies=[Depends(require_admin)])
def delete_episode_note(note_id: int, db: Session = Depends(get_db)):
    result = crud.delete_episode_note(db, note_id)
    if not result:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return {"message": "删除成功"}


ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB


def _is_valid_image(data: bytes, ext: str) -> bool:
    """校验文件魔数与扩展名一致。"""
    if ext in (".jpg", ".jpeg"):
        return data[:2] == b'\xff\xd8'
    if ext == ".png":
        return data[:8] == b'\x89PNG\r\n\x1a\n'
    if ext == ".webp":
        return data[:4] == b'RIFF' and data[8:12] == b'WEBP'
    if ext == ".gif":
        return data[:3] == b'GIF8'
    return False


def _safe_upload_path(filename: str) -> Path:
    if not filename or filename != Path(filename).name:
        raise HTTPException(status_code=400, detail="文件名无效")
    path = (UPLOAD_DIR / filename).resolve()
    if path.parent != UPLOAD_DIR.resolve():
        raise HTTPException(status_code=400, detail="文件名无效")
    return path


@app.post("/api/episodes/{note_id}/images", response_model=EpisodeImageResponse, dependencies=[Depends(require_admin)])
async def upload_episode_image(note_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    note = crud.get_episode_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail="仅支持 jpg/png/webp/gif 图片")
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="图片大小超过 5MB 限制")
    if not _is_valid_image(content, ext):
        raise HTTPException(status_code=400, detail="文件内容与扩展名不符")
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = _safe_upload_path(filename)
    filepath.write_bytes(content)
    return crud.create_episode_image(db, note_id, filename, file.filename)


@app.delete("/api/episode-images/{image_id}", dependencies=[Depends(require_admin)])
def delete_episode_image(image_id: int, db: Session = Depends(get_db)):
    result = crud.delete_episode_image(db, image_id)
    if not result:
        raise HTTPException(status_code=404, detail="图片不存在")
    filepath = _safe_upload_path(result.filename)
    if filepath.exists():
        filepath.unlink()
    return {"message": "删除成功"}


@app.get("/api/uploads/{filename}")
def serve_upload(filename: str):
    filepath = _safe_upload_path(filename)
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(filepath)


# ─── Changelog Routes ─────────────────────────────────────────

@app.get("/api/changelogs", response_model=list[ChangelogResponse])
def list_changelogs(db: Session = Depends(get_db)):
    return crud.get_changelogs(db)


@app.post("/api/changelogs", response_model=ChangelogResponse, dependencies=[Depends(require_admin)])
def create_changelog(data: ChangelogCreate, db: Session = Depends(get_db)):
    return crud.create_changelog(db, data)


@app.put("/api/changelogs/{log_id}", response_model=ChangelogResponse, dependencies=[Depends(require_admin)])
def update_changelog(log_id: int, data: ChangelogUpdate, db: Session = Depends(get_db)):
    result = crud.update_changelog(db, log_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="日志不存在")
    return result


@app.delete("/api/changelogs/{log_id}", dependencies=[Depends(require_admin)])
def delete_changelog(log_id: int, db: Session = Depends(get_db)):
    result = crud.delete_changelog(db, log_id)
    if not result:
        raise HTTPException(status_code=404, detail="日志不存在")
    return {"message": "删除成功"}


# ─── Page Routes ──────────────────────────────────────────────


@app.get("/", include_in_schema=False)
def serve_home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/list", include_in_schema=False)
def serve_list():
    return FileResponse(FRONTEND_DIR / "list.html")


@app.get("/detail", include_in_schema=False)
def serve_detail():
    return FileResponse(FRONTEND_DIR / "detail.html")


@app.get("/admin", include_in_schema=False)
def serve_admin():
    return FileResponse(FRONTEND_DIR / "admin.html")


@app.get("/changelog", include_in_schema=False)
def serve_changelog():
    return FileResponse(FRONTEND_DIR / "changelog.html")


# ─── Startup ──────────────────────────────────────────────────


def migrate_db(db: Session):
    inspector = inspect(db.bind)
    columns = [col["name"] for col in inspector.get_columns("anime")]
    new_fields = {
        "watched_episodes": "INTEGER DEFAULT 0",
        "start_date": "VARCHAR(20)",
        "finish_date": "VARCHAR(20)",
        "is_favorite": "INTEGER DEFAULT 0",
        "personal_tags": "VARCHAR(300)",
    }
    for field, col_type in new_fields.items():
        if field not in columns:
            db.execute(text(f"ALTER TABLE anime ADD COLUMN {field} {col_type}"))
    db.commit()


def migrate_changelogs(db: Session):
    """Normalize early versions and add this release once."""
    version_map = {
        "v1.0.0": "v0.1.0",
        "v1.0.1": "v0.1.1",
        "v1.0.2": "v0.1.2",
    }
    for old_version, new_version in version_map.items():
        db.query(Changelog).filter(Changelog.version == old_version).update(
            {Changelog.version: new_version}, synchronize_session=False
        )

    if not db.query(Changelog).filter(Changelog.version == "v0.1.3").first():
        db.add(Changelog(
            title="交互与进度同步修复",
            version="v0.1.3",
            content=(
                "修复首页状态切换菜单滚动后仍固定在原位的问题。\n"
                "修复管理页面允许已看集数超过总集数的问题。\n"
                "优化首页进度 +1 后正在追、最近更新和统计数据的同步刷新。\n"
                "统一早期更新日志版本号，从 v0.1.0 开始递增。"
            ),
        ))
    if not db.query(Changelog).filter(Changelog.version == "v0.2.0").first():
        db.add(Changelog(
            title="主站接入与安全增强",
            version="v0.2.0",
            content=(
                "接入 Inochi 主站，支持 /apps/anime/ 本地入口和 fan.inochi.top 域名访问。\n"
                "服务端口调整为 18101，并限制为仅监听本机回环地址。\n"
                "统一浅色与深色主题，增加返回主站入口并完善移动端适配。\n"
                "为状态切换、进度更新、导入导出及管理操作统一增加令牌校验。\n"
                "加强封面代理、上传路径、跨站写入和安全响应头防护。\n"
                "优化启动脚本、静态资源缓存与 Nginx 子路径兼容。"
            ),
        ))
    db.commit()


def migrate_from_old_db(db: Session):
    """Copy data from anime_old.db (project root) into the current database."""
    import sqlite3
    from datetime import datetime
    old_db_path = PROJECT_DIR / "anime_old.db"
    if not old_db_path.exists():
        return False
    try:
        old_conn = sqlite3.connect(old_db_path)
        old_conn.row_factory = sqlite3.Row
        rows = old_conn.execute("SELECT * FROM anime").fetchall()
        if not rows:
            old_conn.close()
            return False
        anime_columns = {c.name for c in Anime.__table__.columns}
        datetime_cols = {"created_at", "updated_at"}
        for row in rows:
            data = {}
            for k in row.keys():
                if k not in anime_columns or k == "id":
                    continue
                val = row[k]
                if k in datetime_cols and isinstance(val, str):
                    try:
                        val = datetime.fromisoformat(val)
                    except (ValueError, TypeError):
                        val = None
                data[k] = val
            anime = Anime(**data)
            db.add(anime)
        db.commit()
        max_id = max(row["id"] for row in rows)
        try:
            db.execute(text(f"INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES ('anime', {max_id})"))
            db.commit()
        except Exception:
            pass
        old_conn.close()
        print(f"[MIGRATE] Imported {len(rows)} anime records from anime_old.db")
        return True
    except Exception as e:
        print(f"[MIGRATE] Failed to import from anime_old.db: {e}")
        return False


def backup_database():
    """启动时自动备份数据库文件（带日期，保留最近 7 份）。"""
    db_path = BACKEND_DIR / "anime.db"
    if not db_path.exists():
        return
    backup_dir = BACKEND_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)
    date_str = time.strftime("%Y%m%d")
    backup_path = backup_dir / f"anime_{date_str}.db"
    if not backup_path.exists():
        shutil.copy2(db_path, backup_path)
    # 只保留最近 7 份备份
    backups = sorted(
        [path for path in backup_dir.iterdir() if path.name.startswith("anime_") and path.suffix == ".db"]
    )
    for old in backups[:-7]:
        old.unlink()


@app.on_event("startup")
def startup():
    backup_database()
    init_db()
    db = SessionLocal()
    migrate_db(db)
    migrate_changelogs(db)
    if db.query(Anime).count() == 0:
        if not migrate_from_old_db(db):
            print("[SEED] No old database found, starting with empty database")
    db.close()

@app.on_event("shutdown")
async def shutdown_http():
    if http_client is not None and not http_client.is_closed:
        await http_client.aclose()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=int(os.environ.get("ANIME_PORT", "18101")),
        reload=False,
    )
