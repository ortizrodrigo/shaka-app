from extensions import db
from datetime import datetime, timezone

class ChatMemberModel(db.Model):
    __tablename__ = "chat_members"

    __table_args__ = (
        db.UniqueConstraint("user_id", "chat_id", name="uq_chat_members_user_id_chat_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    chat_id = db.Column(db.Integer, db.ForeignKey("chats.id"), nullable=False)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("UserModel", back_populates="chats")
    chat = db.relationship("ChatModel", back_populates="members")