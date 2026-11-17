from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date
from models import Anime, Character, EpisodeNote, EpisodeImage, Changelog
from schemas import (
    AnimeCreate, AnimeUpdate,
    CharacterCreate, CharacterUpdate,
    EpisodeNoteCreate, EpisodeNoteUpdate,
    ChangelogCreate, ChangelogUpdate,
)


# ─── Generic helpers ─────────────────────────────────────────

def _update_one(db: Session, model, obj_id: int, data):
    obj = db.query(model).filter(model.id == obj_id).first()
    if not obj:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def _delete_one(db: Session, model, obj_id: int):
    obj = db.query(model).filter(model.id == obj_id).first()
    if obj:
        db.delete(obj)
        db.commit()
    return obj


def _serialize_row(row):
    d = {}
    for c in row.__table__.columns:
        val = getattr(row, c.name)
        if hasattr(val, 'isoformat'):
            val = val.isoformat()
        d[c.name] = val
    return d


# ─── Anime CRUD ──────────────────────────────────────────────

def get_anime_list(db: Session, filters: dict):
    query = db.query(Anime)
    if filters.get("status"):
        query = query.filter(Anime.status == filters["status"])
    if filters.get("genre"):
        query = query.filter(text("(',' || genre || ',') LIKE :g")).params(g=f"%,{filters['genre']},%")
    if filters.get("year"):
        query = query.filter(Anime.year == filters["year"])
    if filters.get("min_rating"):
        query = query.filter(Anime.rating >= filters["min_rating"])
    if filters.get("search"):
        query = query.filter(
            (Anime.title.contains(filters["search"]))
            | (Anime.title_jp.contains(filters["search"]))
        )
    return query


def get_anime(db: Session, anime_id: int):
    return db.query(Anime).filter(Anime.id == anime_id).first()


def create_anime(db: Session, anime: AnimeCreate):
    db_anime = Anime(**anime.model_dump())
    db.add(db_anime)
    db.commit()
    db.refresh(db_anime)
    return db_anime


def update_anime(db: Session, anime_id: int, anime: AnimeUpdate):
    return _update_one(db, Anime, anime_id, anime)


def delete_anime(db: Session, anime_id: int):
    return _delete_one(db, Anime, anime_id)


def set_status(db: Session, anime_id: int, status: str):
    db_anime = db.query(Anime).filter(Anime.id == anime_id).first()
    if not db_anime:
        return None
    db_anime.status = status
    db.commit()
    db.refresh(db_anime)
    return db_anime


def increment_progress(db: Session, anime_id: int):
    db_anime = db.query(Anime).filter(Anime.id == anime_id).first()
    if not db_anime:
        return None
    if db_anime.episodes and db_anime.watched_episodes >= db_anime.episodes:
        return db_anime
    db_anime.watched_episodes = (db_anime.watched_episodes or 0) + 1
    if db_anime.episodes and db_anime.watched_episodes >= db_anime.episodes and db_anime.status == "watching":
        db_anime.status = "completed"
        db_anime.finish_date = date.today().isoformat()
    db.commit()
    db.refresh(db_anime)
    return db_anime


# ─── Export / Import ─────────────────────────────────────────

def export_all(db: Session):
    # eager loading via lazy="selectin" on relationships, no N+1
    items = db.query(Anime).all()
    result = []
    for a in items:
        d = _serialize_row(a)
        d["characters"] = [_serialize_row(c) for c in a.characters]
        d["episode_notes"] = []
        for note in a.episode_notes:
            nd = _serialize_row(note)
            nd["images"] = [_serialize_row(img) for img in note.images]
            d["episode_notes"].append(nd)
        result.append(d)
    result.append({"_changelogs": [_serialize_row(c) for c in db.query(Changelog).all()]})
    return result


def import_data(db: Session, data_list: list):
    count = 0
    max_id = 0
    for data in data_list:
        anime_id = data.get("id")
        existing = db.query(Anime).filter(Anime.id == anime_id).first() if anime_id else None
        if existing:
            for key, value in data.items():
                if key != "id" and hasattr(existing, key):
                    setattr(existing, key, value)
        else:
            db_anime = Anime(**{k: v for k, v in data.items() if hasattr(Anime, k)})
            db.add(db_anime)
        if anime_id and anime_id > max_id:
            max_id = anime_id
        count += 1
    db.commit()
    if max_id > 0:
        try:
            db.execute(text(f"INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES ('anime', {max_id})"))
            db.commit()
        except Exception:
            pass
    return count


def import_full(db: Session, data: dict):
    parts = []

    anime_list = data.get("anime", [])
    if anime_list:
        count = import_data(db, anime_list)
        parts.append(f"番剧 {count} 条")

    char_count = 0
    for char_data in data.get("characters", []):
        char_data.pop("id", None)
        db_char = Character(**{k: v for k, v in char_data.items() if hasattr(Character, k)})
        db.add(db_char)
        char_count += 1
    if char_count:
        parts.append(f"角色 {char_count} 条")

    note_count = 0
    for note_data in data.get("episode_notes", []):
        images_data = note_data.pop("images", [])
        note_data.pop("id", None)
        db_note = EpisodeNote(**{k: v for k, v in note_data.items() if hasattr(EpisodeNote, k)})
        db.add(db_note)
        db.flush()
        for img_data in images_data:
            img_data.pop("id", None)
            img_data["note_id"] = db_note.id
            db_img = EpisodeImage(**{k: v for k, v in img_data.items() if hasattr(EpisodeImage, k)})
            db.add(db_img)
        note_count += 1
    if note_count:
        parts.append(f"集数笔记 {note_count} 条")

    log_count = 0
    for log_data in data.get("changelogs", []):
        log_data.pop("id", None)
        db_log = Changelog(**{k: v for k, v in log_data.items() if hasattr(Changelog, k)})
        db.add(db_log)
        log_count += 1
    if log_count:
        parts.append(f"更新日志 {log_count} 条")

    db.commit()
    return "、".join(parts) if parts else "无数据"


# ─── Character CRUD ───────────────────────────────────────────

def get_characters(db: Session, anime_id: int):
    return db.query(Character).filter(Character.anime_id == anime_id).order_by(Character.sort_order, Character.id).all()


def create_character(db: Session, anime_id: int, data: CharacterCreate):
    db_char = Character(anime_id=anime_id, **data.model_dump())
    db.add(db_char)
    db.commit()
    db.refresh(db_char)
    return db_char


def update_character(db: Session, char_id: int, data: CharacterUpdate):
    return _update_one(db, Character, char_id, data)


def delete_character(db: Session, char_id: int):
    return _delete_one(db, Character, char_id)


# ─── Episode Note CRUD ───────────────────────────────────────

def get_episode_notes(db: Session, anime_id: int):
    return db.query(EpisodeNote).filter(EpisodeNote.anime_id == anime_id).order_by(EpisodeNote.episode).all()


def get_episode_note(db: Session, note_id: int):
    return db.query(EpisodeNote).filter(EpisodeNote.id == note_id).first()


def create_episode_note(db: Session, anime_id: int, data: EpisodeNoteCreate):
    db_note = EpisodeNote(anime_id=anime_id, **data.model_dump())
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


def update_episode_note(db: Session, note_id: int, data: EpisodeNoteUpdate):
    return _update_one(db, EpisodeNote, note_id, data)


def delete_episode_note(db: Session, note_id: int):
    return _delete_one(db, EpisodeNote, note_id)


# ─── Episode Image CRUD ──────────────────────────────────────

def create_episode_image(db: Session, note_id: int, filename: str, original_name: str):
    db_img = EpisodeImage(note_id=note_id, filename=filename, original_name=original_name)
    db.add(db_img)
    db.commit()
    db.refresh(db_img)
    return db_img


def delete_episode_image(db: Session, image_id: int):
    return _delete_one(db, EpisodeImage, image_id)


# ─── Changelog CRUD ──────────────────────────────────────────

def get_changelogs(db: Session):
    return db.query(Changelog).order_by(Changelog.created_at.desc()).all()


def create_changelog(db: Session, data: ChangelogCreate):
    db_log = Changelog(**data.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def update_changelog(db: Session, log_id: int, data: ChangelogUpdate):
    return _update_one(db, Changelog, log_id, data)


def delete_changelog(db: Session, log_id: int):
    return _delete_one(db, Changelog, log_id)
