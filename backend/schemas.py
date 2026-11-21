from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime


# ─── Anime ────────────────────────────────────────────────────

class AnimeBase(BaseModel):
    title: str = Field(..., max_length=200)
    title_jp: Optional[str] = None
    cover_url: Optional[str] = None
    synopsis: Optional[str] = None
    episodes: Optional[int] = Field(default=None, ge=0)
    status: str = Field(default="planned", pattern="^(watching|completed|planned|dropped)$")
    genre: Optional[str] = None
    year: Optional[int] = None
    season: Optional[str] = None
    rating: Optional[float] = Field(default=0.0, ge=0, le=10)
    studio: Optional[str] = None
    air_date: Optional[str] = None
    link_url: Optional[str] = None
    notes: Optional[str] = None
    is_featured: Optional[int] = 0
    watched_episodes: Optional[int] = Field(default=0, ge=0)
    start_date: Optional[str] = None
    finish_date: Optional[str] = None
    is_favorite: Optional[int] = 0
    personal_tags: Optional[str] = None

    @model_validator(mode="after")
    def validate_episode_progress(self):
        if (
            self.episodes is not None
            and self.watched_episodes is not None
            and self.watched_episodes > self.episodes
        ):
            raise ValueError("已看集数不能超过总集数")
        return self


class AnimeCreate(AnimeBase):
    pass


class AnimeUpdate(AnimeBase):
    title: Optional[str] = Field(default=None, max_length=200)


class AnimeResponse(AnimeBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str = Field(pattern="^(watching|completed|planned|dropped)$")


# ─── Character ────────────────────────────────────────────────

class CharacterBase(BaseModel):
    name: str = Field(..., max_length=100)
    name_jp: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = 0


class CharacterCreate(CharacterBase):
    pass


class CharacterUpdate(CharacterBase):
    name: Optional[str] = Field(default=None, max_length=100)


class CharacterResponse(CharacterBase):
    id: int
    anime_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Episode Note ─────────────────────────────────────────────

class EpisodeNoteBase(BaseModel):
    episode: int
    note: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0, le=10)
    watched_date: Optional[str] = None


class EpisodeNoteCreate(EpisodeNoteBase):
    pass


class EpisodeNoteUpdate(EpisodeNoteBase):
    episode: Optional[int] = None


class EpisodeImageResponse(BaseModel):
    id: int
    note_id: int
    filename: str
    original_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EpisodeNoteResponse(EpisodeNoteBase):
    id: int
    anime_id: int
    images: List[EpisodeImageResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Changelog ────────────────────────────────────────────────

class ChangelogBase(BaseModel):
    title: str = Field(..., max_length=200)
    content: Optional[str] = None
    version: Optional[str] = None


class ChangelogCreate(ChangelogBase):
    pass


class ChangelogUpdate(ChangelogBase):
    title: Optional[str] = Field(default=None, max_length=200)


class ChangelogResponse(ChangelogBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
