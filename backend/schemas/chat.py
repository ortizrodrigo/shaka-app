from marshmallow import Schema, fields, validate
from schemas.user import UserPublicSchema

class ChatSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(validate=validate.Length(max=100))
    created_at = fields.DateTime(dump_only=True)
    member_users = fields.Nested(UserPublicSchema, many=True, dump_only=True)

class ChatCreateSchema(Schema):
    name = fields.Str(validate=validate.Length(max=100))