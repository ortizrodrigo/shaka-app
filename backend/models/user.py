from extensions import db
from datetime import datetime, timezone

class UserModel(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    messages = db.relationship("MessageModel", back_populates="sender", lazy=True, cascade="all, delete-orphan")
    chats = db.relationship("ChatMemberModel", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
      return f"<User {self.username}>"