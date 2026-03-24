from extensions import db
from datetime import datetime, timezone

class ChatModel(db.Model):
    __tablename__ = "chats"

    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(100), nullable=True)  # Optional for group chats
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    members = db.relationship("ChatMemberModel", back_populates="chat", lazy=True, cascade="all, delete-orphan")
    messages = db.relationship("MessageModel", back_populates="chat", lazy=True, cascade="all, delete-orphan")