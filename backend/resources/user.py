from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from passlib.hash import argon2
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from extensions import db
from models import UserModel, TokenBlocklistModel
from schemas import UserSchema, UserPublicSchema, UserUpdateSchema, UserSearchQuerySchema

from datetime import datetime, timezone

blp = Blueprint("users", __name__, description="Operations on Users")


@blp.route("/user/<int:user_id>")
class User(MethodView):
  @jwt_required()
  @blp.response(200, UserPublicSchema)
  def get(self, user_id):
    user = UserModel.query.get_or_404(user_id)
    return user


@blp.route("/user")
class UserList(MethodView):
  @jwt_required()
  @blp.arguments(UserSearchQuerySchema, location="query")
  @blp.response(200, UserPublicSchema(many=True))
  def get(self, query_args):
    search_term = query_args["search"].strip().lower()

    return (
      UserModel.query
      .filter(UserModel.username.ilike(f"%{search_term}%"))
      .limit(20)
      .all()
    )

  @blp.arguments(UserSchema)
  @blp.response(201, UserSchema)
  def post(self, user_data):
    hashed_password = argon2.hash(user_data["password"])
    user = UserModel(
      username=user_data["username"],
      email=user_data["email"],
      password_hash=hashed_password
    )

    try:
      db.session.add(user)
      db.session.commit()
    except IntegrityError:
      db.session.rollback()
      abort(409, message="A user with that email or username already exists.")
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while inserting the user.")

    return user


@blp.route("/me")
class Me(MethodView):
  @jwt_required()
  @blp.response(200, UserSchema)
  def get(self):
    current_user_id = int(get_jwt_identity())
    user = UserModel.query.get_or_404(current_user_id)
    return user

  @jwt_required()
  @blp.arguments(UserUpdateSchema)
  @blp.response(200, UserSchema)
  def patch(self, update_data, **kwargs):
    current_user_id = int(get_jwt_identity())
    user = UserModel.query.get_or_404(current_user_id)

    new_password = update_data.get("new_password")
    current_password = update_data.get("current_password")

    if new_password:
      if not current_password:
        abort(400, message="current_password is required to set a new password.")
      if not argon2.verify(current_password, user.password_hash):
        abort(401, message="Current password is incorrect.")
      user.password_hash = argon2.hash(new_password)

    if "username" in update_data:
      user.username = update_data["username"]

    if "email" in update_data:
      user.email = update_data["email"]

    try:
      db.session.commit()
    except IntegrityError:
      db.session.rollback()
      abort(409, message="That username or email is already taken.")
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while updating your profile.")

    return user

  @jwt_required()
  def delete(self):
    current_user_id = int(get_jwt_identity())
    user = UserModel.query.get_or_404(current_user_id)

    try:
      jwt_payload = get_jwt()
      current_token = TokenBlocklistModel(
        jti=jwt_payload["jti"],
        user_id=user.id,
        token_type=jwt_payload.get("type"),
        expires_at=datetime.fromtimestamp(jwt_payload.get("exp"), tz=timezone.utc),
      )
      db.session.add(current_token)
      db.session.flush()

      TokenBlocklistModel.query.filter_by(user_id=user.id).delete()

      db.session.delete(user)
      db.session.commit()
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while deleting the user.")

    return {"message": "User deleted."}, 200