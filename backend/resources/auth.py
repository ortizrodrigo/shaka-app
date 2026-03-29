from flask.views import MethodView
from flask import current_app
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone

from flask_jwt_extended import (
  create_access_token,
  create_refresh_token,
  get_jwt,
  get_jwt_identity,
  jwt_required,
  decode_token
)

from passlib.hash import argon2

from extensions import db
from models import UserModel, TokenBlocklistModel
from schemas import LoginSchema, TokenPairSchema

blp = Blueprint("auth", __name__, description="Authentication")

def build_token_payload(token, expires_delta):
  return {
    "token": token,
    "token_type": "Bearer",
    "expires_at": datetime.now(timezone.utc) + expires_delta,
  }

@blp.route("/auth/login")
class Login(MethodView):
  @blp.response(200, TokenPairSchema)
  @blp.arguments(LoginSchema)
  def post(self, login_data):
    username = login_data["username"]
    user = UserModel.query.filter_by(username=username).first()

    if user is None or not argon2.verify(login_data["password"], user.password_hash):
      abort(401, message="Invalid credentials.")

    access_token = create_access_token(identity=str(user.id), fresh=True)
    refresh_token = create_refresh_token(identity=str(user.id))

    return {
      "access": build_token_payload(access_token, current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]),
      "refresh": build_token_payload(refresh_token, current_app.config["JWT_REFRESH_TOKEN_EXPIRES"])
    }

@blp.route("/auth/refresh")
class Refresh(MethodView):
  @blp.response(200, TokenPairSchema)
  @jwt_required(refresh=True)
  def post(self):
    jwt_payload = get_jwt()
    jti = jwt_payload["jti"]
    identity = get_jwt_identity()
    token = TokenBlocklistModel(
      jti=jti,
      user_id=int(identity),
      token_type=jwt_payload.get("type"),
      expires_at=datetime.fromtimestamp(jwt_payload.get("exp"), tz=timezone.utc),
    )

    try:
      db.session.add(token)
      db.session.commit()
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while refreshing.")

    access_token = create_access_token(identity=identity, fresh=False)
    refresh_token = create_refresh_token(identity=identity)

    return {
      "access": build_token_payload(access_token, current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]),
      "refresh": build_token_payload(refresh_token, current_app.config["JWT_REFRESH_TOKEN_EXPIRES"])
    }

@blp.route("/auth/logout")
class Logout(MethodView):
  @jwt_required(verify_type=False)
  def post(self):
    jwt_payload = get_jwt()
    jti = jwt_payload["jti"]
    identity = get_jwt_identity()
    token = TokenBlocklistModel(
      jti=jti,
      user_id=int(identity),
      token_type=jwt_payload.get("type"),
      expires_at=datetime.fromtimestamp(jwt_payload.get("exp"), tz=timezone.utc),
    )

    try:
      db.session.add(token)
      db.session.commit()
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while logging out.")

    return {"message": "Logged out."}, 200