from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import db
from models import ChatMemberModel, UserModel
from schemas import ChatMemberSchema, ChatMemberAddSchema
from services.chat import get_membership, transfer_or_dissolve_ownership
from constants.roles import OWNER_ROLE, PRIVILEGED_ROLES

blp = Blueprint("chat_members", __name__, description="Operations on Chat Members")


@blp.route("/chat-member/<int:chat_member_id>")
class ChatMember(MethodView):
  @jwt_required()
  @blp.response(200, ChatMemberSchema)
  def get(self, chat_member_id):
    current_user_id = int(get_jwt_identity())
    chat_member = ChatMemberModel.query.get_or_404(chat_member_id)

    if not get_membership(chat_member.chat_id, current_user_id):
      abort(403, message="You are not a member of this chat.")

    return chat_member


@blp.route("/chat/<int:chat_id>/members")
class ChatMemberList(MethodView):
  @jwt_required()
  @blp.response(200, ChatMemberSchema(many=True))
  def get(self, chat_id):
    current_user_id = int(get_jwt_identity())

    if not get_membership(chat_id, current_user_id):
      abort(403, message="You are not a member of this chat.")

    return ChatMemberModel.query.filter_by(chat_id=chat_id).all()

  @jwt_required()
  @blp.arguments(ChatMemberAddSchema)
  @blp.response(201, ChatMemberSchema)
  def post(self, add_data, chat_id):
    current_user_id = int(get_jwt_identity())

    requester = get_membership(chat_id, current_user_id)
    if not requester:
      abort(403, message="You are not a member of this chat.")
    if requester.role not in PRIVILEGED_ROLES:
      abort(403, message="Only owners and admins can add members.")

    invitee_id = add_data["user_id"]
    UserModel.query.get_or_404(invitee_id)

    if get_membership(chat_id, invitee_id):
      abort(409, message="User is already a member of this chat.")

    new_member = ChatMemberModel(user_id=invitee_id, chat_id=chat_id, role="member")

    try:
      db.session.add(new_member)
      db.session.commit()
    except IntegrityError:
      db.session.rollback()
      abort(409, message="User is already a member of this chat.")
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while adding the member.")

    return new_member


@blp.route("/chat/<int:chat_id>/members/<int:target_user_id>")
class ChatMemberDetail(MethodView):
  @jwt_required()
  def delete(self, chat_id, target_user_id):
    current_user_id = int(get_jwt_identity())

    requester = get_membership(chat_id, current_user_id)
    if not requester:
      abort(403, message="You are not a member of this chat.")

    target = get_membership(chat_id, target_user_id)
    if not target:
      abort(404, message="User is not a member of this chat.")

    current_user = UserModel.query.get(current_user_id)
    is_self = current_user_id == target_user_id
    is_app_admin = current_user and current_user.is_admin
    is_chat_owner = requester.role == OWNER_ROLE
    is_chat_admin = requester.role in PRIVILEGED_ROLES

    # PERMISSIONS
    # app admins:   can remove anyone
    # chat owners:  can remove anyone (except other owners, but there should only be one owner)
    # chat admins:  can remove members
    # members:      can remove themselves
    if not is_self and not is_app_admin:
      if target.role == OWNER_ROLE:
        abort(403, message="Only app admins can remove an owner from a chat.")
      if not is_chat_owner and not is_chat_admin:
        abort(403, message="You do not have permission to remove this member.")
      if is_chat_admin and not is_chat_owner and target.role in PRIVILEGED_ROLES:
        abort(403, message="Admins cannot remove other admins or owners.")

    try:
      db.session.delete(target)

      if target.role == OWNER_ROLE:
        transfer_or_dissolve_ownership(chat_id, target_user_id)

      db.session.commit()
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while removing the member.")

    return {"message": "Member removed."}, 200