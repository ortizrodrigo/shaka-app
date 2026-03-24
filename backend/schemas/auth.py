from marshmallow import Schema, fields, validate, pre_load, ValidationError, validates

class LoginSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=80))
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=8, max=128))

    @pre_load
    def normalize_input(self, data, **kwargs):
        if data.get("username"):
            data["username"] = data["username"].strip().lower()
        return data

    @staticmethod
    def validate_not_blank(value):
        if not value or value.strip() == "":
            raise ValidationError("Field cannot be blank.")

class TokenSchema(Schema):
    token = fields.Str(required=True, dump_only=True)
    token_type = fields.Str(required=True, dump_only=True, metadata={"example": "Bearer"})
    expires_at = fields.DateTime(required=True, dump_only=True)

class TokenPairSchema(Schema):
    access = fields.Nested(TokenSchema, required=True, dump_only=True)
    refresh = fields.Nested(TokenSchema, required=True, dump_only=True)