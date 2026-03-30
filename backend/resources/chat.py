from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import ChatModel, ChatMemberModel, MessageModel
from schemas import ChatSchema, ChatCreateSchema, MessageSchema
from services.chat import get_membership
from constants.roles import OWNER_ROLE

blp = Blueprint("chats", __name__, description="Operations on Chats")


def chat_with_members(chat_id):
  """Fetch a chat with its members and associated user data eagerly loaded."""
  return (
    ChatModel.query
    .options(joinedload(ChatModel.members).joinedload(ChatMemberModel.user))
    .get_or_404(chat_id)
  )


@blp.route("/chat/<int:chat_id>")
class Chat(MethodView):
  @jwt_required()
  @blp.response(200, ChatSchema)
  def get(self, chat_id):
    """Retrieve a specific chat with members (requires membership)."""

    # extract requester's user_id from jwt
    current_user_id = int(get_jwt_identity())

    # ensure requester belongs to the chat
    if not get_membership(chat_id, current_user_id):
      abort(403, message="You are not a member of this chat.")

    return chat_with_members(chat_id)

  @jwt_required()
  def delete(self, chat_id):
    """Delete a chat (owner only)."""

    # extract requester's user_id from jwt
    current_user_id = int(get_jwt_identity())

    # ensure requester belongs to the chat
    membership = get_membership(chat_id, current_user_id)
    if not membership:
      abort(403, message="You are not a member of this chat.")

    # ensure requester is the chat owner
    if membership.role != OWNER_ROLE:
      abort(403, message="Only the owner can delete this chat.")

    chat = ChatModel.query.get_or_404(chat_id)

    # remove chat
    try:
      db.session.delete(chat)
      db.session.commit()
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while deleting the chat.")

    return {"message": "Chat deleted."}, 200


@blp.route("/chat/<int:chat_id>/messages")
class ChatMessageList(MethodView):
  @jwt_required()
  @blp.response(200, MessageSchema(many=True))
  def get(self, chat_id):
    """List all messages in a chat (requires membership)."""

    # extract requester's user_id from jwt
    current_user_id = int(get_jwt_identity())

    # ensure requester belongs to the chat
    if not get_membership(chat_id, current_user_id):
      abort(403, message="You are not a member of this chat.")

    # ensure chat exists
    ChatModel.query.get_or_404(chat_id)

    return (
      MessageModel.query
      .filter_by(chat_id=chat_id)
      .order_by(MessageModel.created_at.asc())
      .all()
    )


@blp.route("/chat")
class ChatList(MethodView):
  @jwt_required()
  @blp.response(200, ChatSchema(many=True))
  def get(self):
    """List all chats the current user is a member of."""

    # extract requester's user_id from jwt
    current_user_id = int(get_jwt_identity())

    return (
      ChatModel.query
      .join(ChatMemberModel)
      .filter(ChatMemberModel.user_id == current_user_id)
      .options(joinedload(ChatModel.members).joinedload(ChatMemberModel.user))
      .all()
    )

  @jwt_required()
  @blp.arguments(ChatCreateSchema)
  @blp.response(201, ChatSchema)
  def post(self, chat_data):
    """Create a new chat and assign the requester as the owner."""

     # extract requester's user_id from jwt
    current_user_id = int(get_jwt_identity())

    # create chat record and assign ownership to requester
    chat = ChatModel(name=chat_data.get("name"))
    owner_membership = ChatMemberModel(user_id=current_user_id, role=OWNER_ROLE)
    chat.members.append(owner_membership)

    # persist chat record
    try:
      db.session.add(chat)
      db.session.commit()
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while creating the chat.")

    return chat_with_members(chat.id)