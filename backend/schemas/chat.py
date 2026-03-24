from marshmallow import Schema, fields, validate

class ChatSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(validate=validate.Length(max=100))
    created_at = fields.DateTime(dump_only=True)
    members = fields.List(fields.Int(), dump_only=True)  # just user IDs for simplicity