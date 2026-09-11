from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_color = db.Column(db.String(7), default="#e50914")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    my_list = db.relationship("MyList", backref="user", lazy=True, cascade="all, delete-orphan")
    history = db.relationship("WatchHistory", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, default=0)

    videos = db.relationship("Video", backref="category", lazy=True, order_by="Video.id")


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    thumbnail_url = db.Column(db.String(500))
    banner_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    release_year = db.Column(db.Integer)
    duration_minutes = db.Column(db.Integer)
    rating = db.Column(db.String(10), default="U/A 13+")
    is_featured = db.Column(db.Boolean, default=False)
    genre_tags = db.Column(db.String(200))

    def duration_display(self):
        if not self.duration_minutes:
            return ""
        h, m = divmod(self.duration_minutes, 60)
        return f"{h}h {m}m" if h else f"{m}m"


class MyList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey("video.id"), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    video = db.relationship("Video")


class WatchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey("video.id"), nullable=False)
    progress_seconds = db.Column(db.Integer, default=0)
    duration_seconds = db.Column(db.Integer, default=0)
    last_watched = db.Column(db.DateTime, default=datetime.utcnow)

    video = db.relationship("Video")

    def percent(self):
        if not self.duration_seconds:
            return 0
        return min(100, int((self.progress_seconds / self.duration_seconds) * 100))
