from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import ChatModel, ChatMemberModel
from schemas import ChatSchema, ChatCreateSchema

blp = Blueprint("chats", __name__, description="Operations on Chats")

def chat_with_members(chat_id):
  return (
      ChatModel.query
      .options(joinedload(ChatModel.members).joinedload(ChatMemberModel.user))
      .get_or_404(chat_id)
  )

@blp.route("/chat/<int:chat_id>")
class Chat(MethodView):
  @blp.response(200, ChatSchema)
  def get(self, chat_id):
      return chat_with_members(chat_id)

@blp.route("/chat")
class ChatList(MethodView):
  @blp.response(200, ChatSchema(many=True))
  def get(self):
      return (
          ChatModel.query
          .options(joinedload(ChatModel.members).joinedload(ChatMemberModel.user))
          .all()
      )

  @jwt_required()
  @blp.arguments(ChatCreateSchema)
  @blp.response(201, ChatSchema)
  def post(self, chat_data):
      current_user_id = int(get_jwt_identity())

      chat = ChatModel(name=chat_data.get("name"))

      owner_membership = ChatMemberModel(user_id=current_user_id, role="owner")
      chat.members.append(owner_membership)

      try:
        db.session.add(chat)
        db.session.commit()
      except SQLAlchemyError:
        db.session.rollback()
        abort(500, message="An error occurred while creating the chat.")

      return chat_with_members(chat.id)