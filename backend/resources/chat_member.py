from flask.views import MethodView
from flask_smorest import Blueprint

from extensions import db
from models import ChatMemberModel
from schemas import ChatMemberSchema

blp = Blueprint("chat_members", __name__, description="Operations on Chat Members")

@blp.route("/chat-member/<int:chat_member_id>")
class ChatMember(MethodView):
  @blp.response(200, ChatMemberSchema)
  def get(self, chat_member_id):
    chat_member = ChatMemberModel.query.get_or_404(chat_member_id)
    return chat_member

@blp.route("/chat-member")
class ChatMemberList(MethodView):
  @blp.response(200, ChatMemberSchema(many=True))
  def get(self):
    return ChatMemberModel.query.all()