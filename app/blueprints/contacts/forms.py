from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Optional, Length, Email


class ContactForm(FlaskForm):
    contact_type = SelectField("Type", choices=[
        ("individual", "Individual"),
        ("institution", "Institution"),
    ])
    first_name = StringField("First Name", validators=[Optional(), Length(max=100)])
    last_name = StringField("Last Name", validators=[Optional(), Length(max=100)])
    organisation = StringField("Organisation", validators=[Optional(), Length(max=200)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=255)])
    phone = StringField("Phone", validators=[Optional(), Length(max=50)])
    address = TextAreaField("Address", validators=[Optional()])
    city = StringField("City", validators=[Optional(), Length(max=100)])
    country = StringField("Country", validators=[Optional(), Length(max=2)])
    notes = TextAreaField("Notes", validators=[Optional()])
