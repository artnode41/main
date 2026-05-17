from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class ArtistForm(FlaskForm):
    first_name = StringField("First Name", validators=[Optional(), Length(max=100)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=100)])
    birth_year = IntegerField("Birth Year", validators=[Optional(), NumberRange(min=1, max=2100)])
    death_year = IntegerField("Death Year", validators=[Optional(), NumberRange(min=1, max=2100)])
    nationality = StringField("Nationality", validators=[Optional(), Length(max=100)])
    biography = TextAreaField("Biography", validators=[Optional()])
    website = StringField("Website", validators=[Optional(), Length(max=255)])
