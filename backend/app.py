import os

from dotenv import load_dotenv
from flask import Flask
from flask_smorest import Api
from datetime import timedelta

from resources.chat_member import blp as ChatMemberBlueprint
from resources.chat import blp as ChatBlueprint
from resources.message import blp as MessageBlueprint
from resources.user import blp as UserBlueprint
from resources.auth import blp as AuthBlueprint

from models import UserModel

def create_app():
  load_dotenv()

  base_dir = os.path.dirname(os.path.abspath(__file__))

  app = Flask(__name__)

  app.config.setdefault("API_TITLE", "Shaka API")
  app.config.setdefault("API_VERSION", "v1")
  app.config.setdefault("OPENAPI_VERSION", "3.0.3")
  app.config.setdefault("OPENAPI_URL_PREFIX", "/")
  app.config.setdefault("OPENAPI_SWAGGER_UI_PATH", "/swagger-ui")
  app.config.setdefault("OPENAPI_SWAGGER_UI_URL", "https://cdn.jsdelivr.net/npm/swagger-ui-dist/")

  app.config.setdefault("SQLALCHEMY_DATABASE_URI", os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(base_dir, 'app.db')}"))
  app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

  app.config.setdefault("JWT_SECRET_KEY", os.getenv("JWT_SECRET_KEY", "change-me-and-use-at-least-32-bytes"))
  app.config.setdefault("JWT_ACCESS_TOKEN_EXPIRES", timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "15"))))
  app.config.setdefault("JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "30"))))

  from extensions import db, jwt
  from models import TokenBlocklistModel

  db.init_app(app)
  jwt.init_app(app)

  @jwt.token_in_blocklist_loader
  def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload.get("jti")
    identity = jwt_payload.get("sub")
    if not jti or not identity:
      return True

    token_revoked = TokenBlocklistModel.query.filter_by(jti=jti).first() is not None
    if token_revoked:
      return True

    user_exists = UserModel.query.filter_by(id=int(identity)).first()
    if not user_exists:
      return True

    return False

  with app.app_context():
    db.create_all()

  api = Api(app)

  api.register_blueprint(ChatMemberBlueprint)
  api.register_blueprint(ChatBlueprint)
  api.register_blueprint(MessageBlueprint)
  api.register_blueprint(UserBlueprint)
  api.register_blueprint(AuthBlueprint)

  @app.get("/health")
  def health_check():
    return {"status": "ok"}

  @app.get("/")
  def index():
    return {"name": "shaka-backend", "docs": "/swagger-ui"}

  return app


app = create_app()


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
