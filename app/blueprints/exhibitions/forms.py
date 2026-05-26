from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, BooleanField, BooleanField
from wtforms.validators import DataRequired, Optional, Length


class ExhibitionForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=300)])
    description = TextAreaField("Description", validators=[Optional()])
    venue = StringField("Venue / Location", validators=[Optional(), Length(max=200)])
    start_date = DateField("Start Date", validators=[Optional()])
    end_date = DateField("End Date", validators=[Optional()])
    is_active_show = BooleanField("Active Show (display in carousel and highlight on public site)")
    is_active_show = BooleanField("Active Show (display in carousel and highlight on public site)")
