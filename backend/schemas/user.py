from marshmallow import Schema, fields, validate, validates, pre_load, ValidationError

class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True, validate=validate.Length(min=3, max=80))
    email = fields.Email(required=True, validate=validate.Length(max=254))
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=8, max=128))
    created_at = fields.DateTime(dump_only=True)
    
    @pre_load
    def normalize_input(self, data, **kwargs):
        if data.get("username"):
            data["username"] = data["username"].strip().lower()
        if data.get("email"):
            data["email"] = data["email"].strip().lower()
        return data

    @validates("username", "email")
    def validate_not_blank(self, value, **kwargs):
        if not value or value.strip() == "":
            raise ValidationError("This field cannot be blank.")
        
class UserSummarySchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True, validate=validate.Length(min=3, max=80))