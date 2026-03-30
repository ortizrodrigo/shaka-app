from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import db
from models import ChatMemberModel, UserModel
from schemas import ChatMemberSchema, ChatMemberAddSchema, ChatMemberRoleUpdateSchema, OwnerTransferSchema
from services.chat import get_membership, transfer_or_dissolve_ownership
from constants.roles import OWNER_ROLE, ADMIN_ROLE, MEMBER_ROLE, PRIVILEGED_ROLES

blp = Blueprint("chat_members", __name__, description="Operations on Chat Members")


@blp.route("/chat-member/<int:chat_member_id>")
class ChatMember(MethodView):
  @jwt_required()
  @blp.response(200, ChatMemberSchema)
  def get(self, chat_member_id):
    """Retrieve a specific chat membership (requires membership in the chat)."""

    # extract requester's user_id from jwt and fetch chat member
    current_user_id = int(get_jwt_identity())
    chat_member = ChatMemberModel.query.get_or_404(chat_member_id)

    # ensure requester belongs to the same chat as chat member
    if not get_membership(chat_member.chat_id, current_user_id):
      abort(403, message="You are not a member of this chat.")

    return chat_member


@blp.route("/chat/<int:chat_id>/members")
class ChatMemberList(MethodView):
  @jwt_required()
  @blp.response(200, ChatMemberSchema(many=True))
  def get(self, chat_id):
    """List all members of a chat (requires membership)."""

    # extract requester's user_id from jwt
    current_user_id = int(get_jwt_identity())

    # ensure requester belongs to the chat
    if not get_membership(chat_id, current_user_id):
      abort(403, message="You are not a member of this chat.")

    return ChatMemberModel.query.filter_by(chat_id=chat_id).all()

  @jwt_required()
  @blp.arguments(ChatMemberAddSchema)
  @blp.response(201, ChatMemberSchema)
  def post(self, add_data, chat_id):
    """Add a new member to the chat (owners/admins only)."""

    # extract requester's user_id from jwt
    current_user_id = int(get_jwt_identity())

    # ensure requester belongs to the chat
    requester = get_membership(chat_id, current_user_id)
    if not requester:
      abort(403, message="You are not a member of this chat.")

    # ensure requester has admin or owner privileges
    if requester.role not in PRIVILEGED_ROLES:
      abort(403, message="Only owners and admins can add members.")

    # check that target user exists
    invitee_id = add_data["user_id"]
    UserModel.query.get_or_404(invitee_id)

    # prevent duplicate membership
    if get_membership(chat_id, invitee_id):
      abort(409, message="User is already a member of this chat.")

    # create membership record (not yet persisted)
    new_member = ChatMemberModel(user_id=invitee_id, chat_id=chat_id, role="member")

    # persist membership record
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
    """Remove a member from the chat (role-based permissions apply)."""

    # extract requester's user_id from jwt
    current_user_id = int(get_jwt_identity())

    # ensure requester belongs to the chat
    requester = get_membership(chat_id, current_user_id)
    if not requester:
      abort(403, message="You are not a member of this chat.")

    # ensure target belongs to the chat
    target = get_membership(chat_id, target_user_id)
    if not target:
      abort(404, message="User is not a member of this chat.")

    # resolve user permissions
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
      # remove membership
      db.session.delete(target)

      # handle ownership transfer or cleanup if owner is removed
      if target.role == OWNER_ROLE:
        transfer_or_dissolve_ownership(chat_id, target_user_id)

      db.session.commit()
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while removing the member.")

    return {"message": "Member removed."}, 200
  

@blp.route("/chat/<int:chat_id>/members/<int:target_user_id>/role")
class ChatMemberRole(MethodView):
  @jwt_required()
  @blp.arguments(ChatMemberRoleUpdateSchema)
  @blp.response(200, ChatMemberSchema)
  def patch(self, role_data, chat_id, target_user_id):
    """
    Promote or demote a member's role (admin <-> member).

    Rules:
    - owner cannot be promoted/demoted via this endpoint (use /transfer-owner).
    - only owner and admins can change roles.
    - admins can promote members to admin.
    - only the owner can demote an admin.
    """

    # extract requester's user_id from jwt
    current_user_id = int(get_jwt_identity())

    # ensure requester belongs to the chat
    requester = get_membership(chat_id, current_user_id)
    if not requester:
      abort(403, message="You are not a member of this chat.")

    # ensure requester has admin or owner privileges
    if requester.role not in PRIVILEGED_ROLES:
      abort(403, message="Only owners and admins can change member roles.")

    # ensure target belongs to the chat
    target = get_membership(chat_id, target_user_id)
    if not target:
      abort(404, message="User is not a member of this chat.")

    # ensure target is not the owner
    if target.role == OWNER_ROLE:
      abort(403, message="The owner's role cannot be changed here. Use the transfer ownership endpoint.")

    # ensure target is not the requester
    if current_user_id == target_user_id:
      abort(403, message="You cannot change your own role.")

    new_role = role_data["role"]

    # Admins can only demote an admin if they are the owner
    if target.role == ADMIN_ROLE and new_role == MEMBER_ROLE:
      if requester.role != OWNER_ROLE:
        abort(403, message="Only the owner can demote an admin.")

    # update target's role
    target.role = new_role

    # persist target's role
    try:
      db.session.commit()
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while updating the member's role.")

    return target
 
 
@blp.route("/chat/<int:chat_id>/transfer-owner")
class OwnerTransfer(MethodView):
  @jwt_required()
  @blp.arguments(OwnerTransferSchema)
  @blp.response(200, ChatMemberSchema)
  def post(self, transfer_data, chat_id):
    """
    Transfer chat ownership to another member (owner only).
    The previous owner becomes an admin. Only one owner at a time.
    """

    # extract requester's user_id from jwt
    current_user_id = int(get_jwt_identity())

    # ensure requester belongs to the chat
    requester = get_membership(chat_id, current_user_id)
    if not requester:
      abort(403, message="You are not a member of this chat.")

    # ensure requester is the chat owner
    if requester.role != OWNER_ROLE:
      abort(403, message="Only the current owner can transfer ownership.")

    new_owner_id = transfer_data["user_id"]

    # ensure target is not the requester
    if new_owner_id == current_user_id:
      abort(400, message="You are already the owner.")

    # ensure target belongs to the chat
    target = get_membership(chat_id, new_owner_id)
    if not target:
      abort(404, message="Target user is not a member of this chat.")

    # demote current owner to admin, promote target to owner
    requester.role = ADMIN_ROLE
    target.role = OWNER_ROLE

    # persist role updates
    try:
      db.session.commit()
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while transferring ownership.")

    return target