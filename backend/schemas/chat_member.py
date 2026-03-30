from marshmallow import Schema, fields, validate
from constants.roles import ADMIN_ROLE, MEMBER_ROLE

class ChatMemberSchema(Schema):
    id = fields.Int(dump_only=True)
    user_id = fields.Int(required=True)
    chat_id = fields.Int(required=True)
    role = fields.Str(dump_only=True)
    joined_at = fields.DateTime(dump_only=True)

class ChatMemberAddSchema(Schema):
    user_id = fields.Int(required=True)

class ChatMemberRoleUpdateSchema(Schema):
    role = fields.Str(required=True, validate=validate.OneOf([ADMIN_ROLE, MEMBER_ROLE]))
 
class OwnerTransferSchema(Schema):
    user_id = fields.Int(required=True)