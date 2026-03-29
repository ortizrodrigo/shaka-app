from models import ChatMemberModel, ChatModel
from extensions import db

from constants.roles import OWNER_ROLE

def get_membership(chat_id, user_id):
  """get the ChatMemberModel for a user in a chat (or None)."""
  return ChatMemberModel.query.filter_by(chat_id=chat_id, user_id=user_id).first()

def transfer_or_dissolve_ownership(chat_id, departing_user_id):
  """
  after an owner leaves, promote the earliest-joined remaining member.
  if no members remain, delete the chat entirely.
  called within an active db.session -> does NOT commit.
  """
  next_owner = (
    ChatMemberModel.query
    .filter(ChatMemberModel.chat_id == chat_id, ChatMemberModel.user_id != departing_user_id)
    .order_by(ChatMemberModel.joined_at.asc())
    .first()
  )

  if next_owner:
    next_owner.role = OWNER_ROLE
  else:
    chat = ChatModel.query.get(chat_id)
    if chat:
      db.session.delete(chat)