from models import ChatMemberModel, ChatModel, MessageModel
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

def get_last_message(chat_id):
  """Return the most recent MessageModel for a chat, or None."""
  return MessageModel.query.filter_by(chat_id=chat_id).order_by(MessageModel.created_at.desc()).first()
 
def get_unread_count(chat_id, membership):
  """
  Return the number of messages in the chat sent after the member's last_read_at.
  If last_read_at is None, counts all messages in the chat.
  """
  query = MessageModel.query.filter_by(chat_id=chat_id)
  if membership.last_read_at is not None:
    query = query.filter(MessageModel.created_at > membership.last_read_at)
  return query.count()
 
def enrich_chat(chat, membership):
  """
  Attach last_message and unread_count as transient attributes onto a ChatModel
  instance so that ChatSchema can serialize them.
  """
  chat.last_message = get_last_message(chat.id)
  chat.unread_count = get_unread_count(chat.id, membership)
  return chat
 
def enrich_chats(chats, user_id):
  """
  Enrich a list of ChatModel instances with last_message and unread_count
  for the given user.
  """
  memberships = {
    m.chat_id: m
    for m in ChatMemberModel.query.filter(
      ChatMemberModel.chat_id.in_([c.id for c in chats]),
      ChatMemberModel.user_id == user_id
    ).all()
  }
  for chat in chats:
    membership = memberships.get(chat.id)
    chat.last_message = get_last_message(chat.id)
    chat.unread_count = get_unread_count(chat.id, membership) if membership else 0
  return chats
 