from marshmallow import Schema, fields, validate
from schemas.user import UserPublicSchema

class LastMessageSchema(Schema):
    id = fields.Int(dump_only=True)
    content = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    sender = fields.Nested(UserPublicSchema, dump_only=True)

class ChatSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(validate=validate.Length(max=100))
    created_at = fields.DateTime(dump_only=True)
    member_users = fields.Nested(UserPublicSchema, many=True, dump_only=True)
    last_message = fields.Nested(LastMessageSchema, dump_only=True, allow_none=True)
    unread_count = fields.Int(dump_only=True)

class ChatCreateSchema(Schema):
    name = fields.Str(validate=validate.Length(max=100))
    member_ids = fields.List(fields.Int(), load_default=[])

class ChatRenameSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))