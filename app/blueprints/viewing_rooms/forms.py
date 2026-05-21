from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, DateField
from wtforms.validators import DataRequired, Optional, Length


class ViewingRoomForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=300)])
    description = TextAreaField("Description", validators=[Optional()])
    access_code = StringField("Access Code", validators=[Optional(), Length(max=100)])
    is_active = BooleanField("Active (visible to public)")
    opens_at = DateField("Opens", validators=[Optional()])
    closes_at = DateField("Closes", validators=[Optional()])
