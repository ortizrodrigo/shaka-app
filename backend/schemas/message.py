from marshmallow import Schema, fields, validate

class MessageSchema(Schema):
    id = fields.Int(dump_only=True)
    content = fields.Str(required=True, validate=validate.Length(min=1, max=5000))
    user_id = fields.Int(dump_only=True)
    chat_id = fields.Int(required=True)
    created_at = fields.DateTime(dump_only=True)