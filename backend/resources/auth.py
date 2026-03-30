from flask.views import MethodView
from flask import current_app
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone

from flask_jwt_extended import (
  create_access_token,
  create_refresh_token,
  decode_token,
  get_jwt,
  get_jwt_identity,
  jwt_required,
)

from passlib.hash import argon2

from extensions import db
from models import UserModel, TokenBlocklistModel
from schemas import LoginSchema, TokenPairSchema

blp = Blueprint("auth", __name__, description="Authentication")

def build_token_payload(token):
  """Standardize token responses in TokenSchema format."""

  # extract JWT's expiration timestamp
  decoded = decode_token(token)
  expires_at = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
  return {
    "token": token,
    "token_type": "Bearer",
    "expires_at": expires_at,
  }

@blp.route("/auth/login")
class Login(MethodView):
  @blp.arguments(LoginSchema)
  @blp.response(200, TokenPairSchema)
  def post(self, login_data):
    """Authenticate a user and return a new access/refresh token pair."""

    # extract username from request payload and fetch user from database
    username = login_data["username"]
    user = UserModel.query.filter_by(username=username).first()

    # validate credentials: user existence and password match (with argon2 hash)
    if user is None or not argon2.verify(login_data["password"], user.password_hash):
      abort(401, message="Invalid credentials.")

    # generate access and refresh tokens
    access_token = create_access_token(identity=str(user.id), fresh=True)
    refresh_token = create_refresh_token(identity=str(user.id))

    # return tokens in TokenPairSchema format
    return {
      "access": build_token_payload(access_token),
      "refresh": build_token_payload(refresh_token),
    }

@blp.route("/auth/refresh")
class Refresh(MethodView):
  @blp.response(200, TokenPairSchema)
  @jwt_required(refresh=True)
  def post(self):
    """Refresh authentication tokens."""

    # extract current token data
    jwt_payload = get_jwt()
    jti = jwt_payload["jti"]
    identity = get_jwt_identity()

    # create blocklist record for current token (not yet persisted)
    token = TokenBlocklistModel(
      jti=jti,
      user_id=int(identity),
      token_type=jwt_payload.get("type"),
      expires_at=datetime.fromtimestamp(jwt_payload.get("exp"), tz=timezone.utc),
    )

    # persist blocklist entry (invalidate current token)
    try:
      db.session.add(token)
      db.session.commit()
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while refreshing.")

    # generate new (non-fresh) access and refresh tokens
    access_token = create_access_token(identity=identity, fresh=False)
    refresh_token = create_refresh_token(identity=identity)

    return {
      "access": build_token_payload(access_token),
      "refresh": build_token_payload(refresh_token),
    }

@blp.route("/auth/logout")
class Logout(MethodView):
  @jwt_required(verify_type=False)
  def post(self):
    """Log out a user by invalidating their current token."""

    # extract current token data
    jwt_payload = get_jwt()
    jti = jwt_payload["jti"]
    identity = get_jwt_identity()

    # create blocklist record for current token (not yet persisted)
    token = TokenBlocklistModel(
      jti=jti,
      user_id=int(identity),
      token_type=jwt_payload.get("type"),
      expires_at=datetime.fromtimestamp(jwt_payload.get("exp"), tz=timezone.utc),
    )

    # persist blocklist entry (invalidate current token)
    try:
      db.session.add(token)
      db.session.commit()
    except SQLAlchemyError:
      db.session.rollback()
      abort(500, message="An error occurred while logging out.")

    return {"message": "Logged out."}, 200