from flask.views import MethodView
from flask_smorest import Blueprint

from extensions import db
from models import MessageModel
from schemas import MessageSchema

blp = Blueprint("messages", __name__, description="Operations on Messages")

@blp.route("/message/<int:message_id>")
class Message(MethodView):
  @blp.response(200, MessageSchema)
  def get(self, message_id):
    message = MessageModel.query.get_or_404(message_id)
    return message

@blp.route("/message")
class MessageList(MethodView):
  @blp.response(200, MessageSchema(many=True))
  def get(self):
    return MessageModel.query.all()