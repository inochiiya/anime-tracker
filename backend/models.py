from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Anime(Base):
    __tablename__ = "anime"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False, index=True)
    title_jp = Column(String(200), nullable=True)
    cover_url = Column(String(500), nullable=True)
    synopsis = Column(Text, nullable=True)
    episodes = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="planned", index=True)
    genre = Column(String(200), nullable=True)
    year = Column(Integer, nullable=True, index=True)
    season = Column(String(10), nullable=True)
    rating = Column(Float, nullable=True, default=0.0, index=True)
    studio = Column(String(100), nullable=True)
    air_date = Column(String(20), nullable=True)
    link_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    is_featured = Column(Integer, default=0, index=True)
    watched_episodes = Column(Integer, default=0)
    start_date = Column(String(20), nullable=True)
    finish_date = Column(String(20), nullable=True)
    is_favorite = Column(Integer, default=0)
    personal_tags = Column(String(300), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), index=True)

    characters = relationship("Character", back_populates="anime", cascade="all, delete-orphan", lazy="selectin")
    episode_notes = relationship("EpisodeNote", back_populates="anime", cascade="all, delete-orphan", lazy="selectin")


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    anime_id = Column(Integer, ForeignKey("anime.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    name_jp = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    role = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    anime = relationship("Anime", back_populates="characters")


class EpisodeNote(Base):
    __tablename__ = "episode_notes"
    __table_args__ = (UniqueConstraint('anime_id', 'episode', name='uq_anime_episode'),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    anime_id = Column(Integer, ForeignKey("anime.id"), nullable=False, index=True)
    episode = Column(Integer, nullable=False)
    note = Column(Text, nullable=True)
    rating = Column(Float, nullable=True)
    watched_date = Column(String(20), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    anime = relationship("Anime", back_populates="episode_notes")
    images = relationship("EpisodeImage", back_populates="note", cascade="all, delete-orphan", lazy="selectin")


class EpisodeImage(Base):
    __tablename__ = "episode_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("episode_notes.id"), nullable=False, index=True)
    filename = Column(String(200), nullable=False)
    original_name = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    note = relationship("EpisodeNote", back_populates="images")


class Changelog(Base):
    __tablename__ = "changelogs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    version = Column(String(20), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
