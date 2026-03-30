from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import ChatModel, ChatMemberModel, MessageModel, UserModel
from schemas import (
  ChatSchema, ChatCreateSchema, ChatRenameSchema,
  MessageSchema, MessagePageSchema, MessagePaginationQuerySchema,
)
from services.chat import get_membership, enrich_chat, enrich_chats
from constants.roles import OWNER_ROLE, PRIVILEGED_ROLES

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
    membership = get_membership(chat_id, current_user_id)
    if not membership:
      abort(403, message="You are not a member of this chat.")

    chat = chat_with_members(chat_id)
    return enrich_chat(chat, membership)
  
  @jwt_required()
  @blp.arguments(ChatRenameSchema)
  @blp.response(200, ChatSchema)
  def patch(self, rename_data, chat_id):
    """Rename a chat (owner and admins only)."""

    # extract requester's user_id from jwt
    current_user_id = int(get_jwt_identity())

    # ensure requester belongs to the chat
    membership = get_membership(chat_id, current_user_id)
    if not membership:
      abort(403, message="You are not a member of this chat.")

    # ensure requester has admin or owner privileges
    if membership.role not in PRIVILEGED_ROLES:
      abort(403, message="Only owners and admins can rename this chat.")

    # update chat name
    chat = ChatModel.query.get_or_404(chat_id)
    chat.name = rename_data["name"]

    # persist chat name
    try:
      db.session.commit()
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while renaming the chat.")

    chat = chat_with_members(chat_id)
    return enrich_chat(chat, membership)

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
  @blp.arguments(MessagePaginationQuerySchema, location="query")
  @blp.response(200, MessagePageSchema)
  def get(self, pagination_args, chat_id):
    """List messages in a chat with pagination (requires membership)."""

    # extract requester's user_id from jwt
    current_user_id = int(get_jwt_identity())

    # ensure requester belongs to the chat
    if not get_membership(chat_id, current_user_id):
      abort(403, message="You are not a member of this chat.")

    # ensure chat exists
    ChatModel.query.get_or_404(chat_id)

    # retrieve pagination arguments from payload
    page = pagination_args["page"]
    per_page = pagination_args["per_page"]

    # retrieve messages with pagination
    paginated = (
      MessageModel.query
      .filter_by(chat_id=chat_id)
      .order_by(MessageModel.created_at.asc())
      .paginate(page=page, per_page=per_page, error_out=False)
    )

    return {
      "items": paginated.items,
      "total": paginated.total,
      "page": paginated.page,
      "per_page": paginated.per_page,
      "pages": paginated.pages,
      "has_next": paginated.has_next,
      "has_prev": paginated.has_prev,
    }


@blp.route("/chat")
class ChatList(MethodView):
  @jwt_required()
  @blp.response(200, ChatSchema(many=True))
  def get(self):
    """List all chats the current user is a member of."""
    current_user_id = int(get_jwt_identity())

    chats = (
      ChatModel.query
      .join(ChatMemberModel)
      .filter(ChatMemberModel.user_id == current_user_id)
      .options(joinedload(ChatModel.members).joinedload(ChatMemberModel.user))
      .all()
    )

    return enrich_chats(chats, current_user_id)

  @jwt_required()
  @blp.arguments(ChatCreateSchema)
  @blp.response(201, ChatSchema)
  def post(self, chat_data):
    """Create a new chat, assign requester as owner, and optionally add initial members."""

    # extract requester's user_id from jwt
    current_user_id = int(get_jwt_identity())

    # create chat record and assign ownership to requester
    chat = ChatModel(name=chat_data.get("name"))
    owner_membership = ChatMemberModel(user_id=current_user_id, role=OWNER_ROLE)
    chat.members.append(owner_membership)

    # add any additional members specified in member_ids
    extra_ids = [uid for uid in set(chat_data.get("member_ids", [])) if uid != current_user_id]
    for uid in extra_ids:
      # ensure each user exists
      if not UserModel.query.get(uid):
        abort(404, message=f"User {uid} not found.")
      chat.members.append(ChatMemberModel(user_id=uid, role="member"))

    # persist chat record
    try:
      db.session.add(chat)
      db.session.commit()
    except IntegrityError:
      db.session.rollback()
      abort(409, message="One or more users are already members or do not exist.")
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while creating the chat.")

    chat = chat_with_members(chat.id)
    return enrich_chat(chat, owner_membership)
