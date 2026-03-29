from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import ChatMemberModel
from schemas import ChatMemberSchema

blp = Blueprint("chat_members", __name__, description="Operations on Chat Members")

@blp.route("/chat-member/<int:chat_member_id>")
class ChatMember(MethodView):
  @jwt_required()
  @blp.response(200, ChatMemberSchema)
  def get(self, chat_member_id):
    current_user_id = int(get_jwt_identity())
    chat_member = ChatMemberModel.query.get_or_404(chat_member_id)

    membership = ChatMemberModel.query.filter_by(
      chat_id=chat_member.chat_id,
      user_id=current_user_id
    ).first()
    if not membership:
      abort(403, message="You are not a member of this chat.")

    return chat_member


@blp.route("/chat/<int:chat_id>/members")
class ChatMemberList(MethodView):
  @jwt_required()
  @blp.response(200, ChatMemberSchema(many=True))
  def get(self, chat_id):
    current_user_id = int(get_jwt_identity())

    membership = ChatMemberModel.query.filter_by(
      chat_id=chat_id,
      user_id=current_user_id
    ).first()
    if not membership:
      abort(403, message="You are not a member of this chat.")

    return ChatMemberModel.query.filter_by(chat_id=chat_id).all()