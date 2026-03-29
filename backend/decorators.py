from functools import wraps
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_smorest import abort
from models import UserModel

def admin_required(fn):
  @wraps(fn)
  def wrapper(*args, **kwargs):
    verify_jwt_in_request()
    current_user_id = int(get_jwt_identity())
    user = UserModel.query.get(current_user_id)
    if not user or not user.is_admin:
      abort(403, message="Admin privileges required.")
    return fn(*args, **kwargs)
  return wrapper