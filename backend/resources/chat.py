from flask.views import MethodView
from flask_smorest import Blueprint

from extensions import db
from models import ChatModel
from schemas import ChatSchema

blp = Blueprint("chats", __name__, description="Operations on Chats")

@blp.route("/chat/<int:chat_id>")
class Chat(MethodView):
  @blp.response(200, ChatSchema)
  def get(self, chat_id):
    chat = ChatModel.query.get_or_404(chat_id)
    return chat

@blp.route("/chat")
class ChatList(MethodView):
  @blp.response(200, ChatSchema(many=True))
  def get(self):
    return ChatModel.query.all()