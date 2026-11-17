from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func, case, text, inspect
from typing import Optional
import json
import os
import uuid
import time
import shutil
import httpx
from hashlib import md5

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

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="追番收藏 API")

# 说明：本项目前后端同源（均由 FastAPI 提供服务），无需 CORS。
# 移除 allow_origins=["*"] 可防止其他网站跨域调用本 API。

app.mount("/css", StaticFiles(directory="../frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="../frontend/js"), name="js")
app.mount("/assets", StaticFiles(directory="../frontend/assets"), name="assets")

# Reusable httpx client (connection pool)
http_client = httpx.AsyncClient(timeout=10, follow_redirects=True)


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
    result = crud.update_anime(db, anime_id, anime)
    if not result:
        raise HTTPException(status_code=404, detail="番剧不存在")
    return result


@app.delete("/api/anime/{anime_id}", dependencies=[Depends(require_admin)])
def delete_anime(anime_id: int, db: Session = Depends(get_db)):
    result = crud.delete_anime(db, anime_id)
    if not result:
        raise HTTPException(status_code=404, detail="番剧不存在")
    return {"message": "删除成功"}


@app.put("/api/anime/{anime_id}/status", response_model=AnimeResponse)
def set_status(anime_id: int, data: StatusUpdate, db: Session = Depends(get_db)):
    """公开的轻量状态切换，只允许修改 status 字段，用于首页/详情页的一键切换。"""
    result = crud.set_status(db, anime_id, data.status)
    if not result:
        raise HTTPException(status_code=404, detail="番剧不存在")
    return result


@app.put("/api/anime/{anime_id}/progress", response_model=AnimeResponse)
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

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
CACHE_TTL = 7 * 24 * 3600  # 7 days
os.makedirs(CACHE_DIR, exist_ok=True)


def _detect_mime(data: bytes) -> str:
    if data[:8] == b'\x89PNG\r\n\x1a\n': return "image/png"
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP': return "image/webp"
    if data[:3] == b'GIF8': return "image/gif"
    if data[:2] == b'\xff\xd8': return "image/jpeg"
    if data[:4] == b'<svg' or b'<svg' in data[:200]: return "image/svg+xml"
    return "image/jpeg"


@app.get("/api/proxy/cover")
async def proxy_cover(url: str):
    cache_key = md5(url.encode()).hexdigest()
    cache_path = os.path.join(CACHE_DIR, cache_key + ".img")
    meta_path = os.path.join(CACHE_DIR, cache_key + ".meta")

    if os.path.exists(cache_path):
        # TTL check: re-fetch if cache is stale
        age = time.time() - os.path.getmtime(cache_path)
        if age < CACHE_TTL:
            mime = "image/jpeg"
            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    mime = f.read().strip()
            with open(cache_path, "rb") as f:
                return Response(content=f.read(), media_type=mime,
                              headers={"Cache-Control": "public, max-age=604800"})

    try:
        resp = await http_client.get(url, headers={"Referer": ""})
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="图片获取失败")
        mime = resp.headers.get("content-type", "")
        if not mime or mime == "application/octet-stream":
            mime = _detect_mime(resp.content)
        mime = mime.split(";")[0].strip()
        with open(cache_path, "wb") as f:
            f.write(resp.content)
        with open(meta_path, "w") as f:
            f.write(mime)
        return Response(content=resp.content, media_type=mime,
                      headers={"Cache-Control": "public, max-age=604800"})
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="图片请求失败")


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
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return crud.create_episode_image(db, note_id, filename, file.filename)


@app.delete("/api/episode-images/{image_id}", dependencies=[Depends(require_admin)])
def delete_episode_image(image_id: int, db: Session = Depends(get_db)):
    result = crud.delete_episode_image(db, image_id)
    if not result:
        raise HTTPException(status_code=404, detail="图片不存在")
    filepath = os.path.join(UPLOAD_DIR, result.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    return {"message": "删除成功"}


@app.get("/api/uploads/{filename}")
def serve_upload(filename: str):
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
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
    return FileResponse("../frontend/index.html")


@app.get("/list", include_in_schema=False)
def serve_list():
    return FileResponse("../frontend/list.html")


@app.get("/detail", include_in_schema=False)
def serve_detail():
    return FileResponse("../frontend/detail.html")


@app.get("/admin", include_in_schema=False)
def serve_admin():
    return FileResponse("../frontend/admin.html")


@app.get("/changelog", include_in_schema=False)
def serve_changelog():
    return FileResponse("../frontend/changelog.html")


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


def migrate_from_old_db(db: Session):
    """Copy data from anime_old.db (project root) into the current database."""
    import sqlite3
    from datetime import datetime
    old_db_path = os.path.join(os.path.dirname(__file__), "..", "anime_old.db")
    if not os.path.exists(old_db_path):
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
    db_path = os.path.join(os.path.dirname(__file__), "anime.db")
    if not os.path.exists(db_path):
        return
    backup_dir = os.path.join(os.path.dirname(__file__), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    date_str = time.strftime("%Y%m%d")
    backup_path = os.path.join(backup_dir, f"anime_{date_str}.db")
    if not os.path.exists(backup_path):
        shutil.copy2(db_path, backup_path)
    # 只保留最近 7 份备份
    backups = sorted(
        [f for f in os.listdir(backup_dir) if f.startswith("anime_") and f.endswith(".db")]
    )
    for old in backups[:-7]:
        os.remove(os.path.join(backup_dir, old))


@app.on_event("startup")
def startup():
    backup_database()
    init_db()
    db = SessionLocal()
    migrate_db(db)
    if db.query(Anime).count() == 0:
        if not migrate_from_old_db(db):
            print("[SEED] No old database found, starting with empty database")
    db.close()

@app.on_event("shutdown")
async def shutdown_http():
    await http_client.aclose()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
