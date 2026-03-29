from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import MessageModel, ChatMemberModel
from schemas import MessageSchema

blp = Blueprint("messages", __name__, description="Operations on Messages")

@blp.route("/message/<int:message_id>")
class Message(MethodView):
  @jwt_required()
  @blp.response(200, MessageSchema)
  def get(self, message_id):
    message = MessageModel.query.get_or_404(message_id)

    current_user_id = int(get_jwt_identity())
    membership = ChatMemberModel.query.filter_by(
      chat_id=message.chat_id,
      user_id=current_user_id
    ).first()
    if not membership:
      abort(403, message="You are not a member of this chat.")

    return message


@blp.route("/message")
class MessageList(MethodView):
  @jwt_required()
  @blp.arguments(MessageSchema)
  @blp.response(201, MessageSchema)
  def post(self, message_data):
    current_user_id = int(get_jwt_identity())
    chat_id = message_data["chat_id"]

    membership = ChatMemberModel.query.filter_by(
      chat_id=chat_id,
      user_id=current_user_id
    ).first()
    if not membership:
      abort(403, message="You are not a member of this chat.")

    message = MessageModel(
      content=message_data["content"],
      chat_id=chat_id,
      user_id=current_user_id,
    )

    try:
      db.session.add(message)
      db.session.commit()
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while sending the message.")

    return message