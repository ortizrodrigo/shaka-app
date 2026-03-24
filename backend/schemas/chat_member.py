from marshmallow import Schema, fields

class ChatMemberSchema(Schema):
    id = fields.Int(dump_only=True)
    user_id = fields.Int(required=True)
    chat_id = fields.Int(required=True)
    joined_at = fields.DateTime(dump_only=True)