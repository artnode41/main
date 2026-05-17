from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField
from wtforms.validators import DataRequired, Optional, Length


EVENT_TYPE_CHOICES = [
    ("acquisition", "Acquisition"),
    ("sale", "Sale"),
    ("loan", "Loan"),
    ("exhibition", "Exhibition"),
    ("restitution", "Restitution"),
    ("import", "Import"),
    ("export", "Export"),
    ("ownership", "Change of Ownership"),
    ("other", "Other"),
]


class ProvenanceForm(FlaskForm):
    event_type = SelectField("Event Type", choices=EVENT_TYPE_CHOICES,
                             validators=[DataRequired()])
    event_date = DateField("Event Date", validators=[Optional()])
    event_date_end = DateField("End Date", validators=[Optional()])
    source_name = StringField("Source / Previous Owner",
                              validators=[Optional(), Length(max=200)])
    source_country = StringField("Country (2-letter code)",
                                 validators=[Optional(), Length(max=2)])
    description = TextAreaField("Description", validators=[Optional()])
