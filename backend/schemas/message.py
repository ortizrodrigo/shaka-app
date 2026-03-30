from marshmallow import Schema, fields, validate

class MessageSchema(Schema):
    id = fields.Int(dump_only=True)
    content = fields.Str(required=True, validate=validate.Length(min=1, max=5000))
    user_id = fields.Int(dump_only=True)
    chat_id = fields.Int(required=True)
    created_at = fields.DateTime(dump_only=True)

class MessagePageSchema(Schema):
    items = fields.List(fields.Nested(MessageSchema), dump_only=True)
    total = fields.Int(dump_only=True)
    page = fields.Int(dump_only=True)
    per_page = fields.Int(dump_only=True)
    pages = fields.Int(dump_only=True)
    has_next = fields.Bool(dump_only=True)
    has_prev = fields.Bool(dump_only=True)
 
class MessagePaginationQuerySchema(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=50, validate=validate.Range(min=1, max=100))
