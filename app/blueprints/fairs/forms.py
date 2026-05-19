from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectMultipleField
from wtforms.validators import DataRequired, Optional, Length


class ArtFairForm(FlaskForm):
    name = StringField("Fair Name", validators=[DataRequired(), Length(max=200)])
    location = StringField("Location / Booth", validators=[Optional(), Length(max=200)])
    start_date = DateField("Start Date", validators=[Optional()])
    end_date = DateField("End Date", validators=[Optional()])
