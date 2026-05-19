from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField, DecimalField, DateField
from wtforms.validators import DataRequired, Optional, Length, NumberRange


STATUS_CHOICES = [
    ("available", "Available"),
    ("reserved", "Reserved"),
    ("sold", "Sold"),
    ("on_consignment", "On Consignment"),
    ("on_loan", "On Loan"),
]

OBJECT_TYPE_CHOICES = [
    ("", "— Select —"),
    ("painting", "Painting"),
    ("sculpture", "Sculpture"),
    ("print", "Print"),
    ("drawing", "Drawing"),
    ("photograph", "Photograph"),
    ("glass", "Glass"),
    ("other", "Other"),
]

OWNERSHIP_CHOICES = [
    ("owned", "Owned outright (gallery purchased)"),
    ("consignment", "Consignment (artist/owner retains title)"),
]


class ArtworkForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=500)])
    artist_id = SelectField("Artist", coerce=int, validators=[Optional()])
    year_from = IntegerField("Year (from)", validators=[Optional(), NumberRange(min=1, max=2100)])
    year_to = IntegerField("Year (to)", validators=[Optional(), NumberRange(min=1, max=2100)])
    medium = TextAreaField("Medium", validators=[Optional(), Length(max=500)])
    dimensions = TextAreaField("Dimensions", validators=[Optional(), Length(max=500)])
    description = TextAreaField("Description", validators=[Optional()])
    object_type = SelectField("Object Type", choices=OBJECT_TYPE_CHOICES, validators=[Optional()])
    status = SelectField("Status", choices=STATUS_CHOICES, validators=[DataRequired()])
    price = DecimalField("Asking Price", validators=[Optional()], places=2)
    currency = SelectField("Currency", choices=[
        ("CHF", "CHF"), ("EUR", "EUR"), ("USD", "USD"), ("GBP", "GBP")
    ])
    ownership_type = SelectField("Ownership", choices=OWNERSHIP_CHOICES)
    acquisition_cost = DecimalField("Acquisition Cost", validators=[Optional()], places=2)
    acquisition_date = DateField("Acquisition Date", validators=[Optional()])
    inventory_number = StringField("Inventory Number", validators=[Optional(), Length(max=100)])
    rights = StringField("Rights", validators=[Optional(), Length(max=200)])
    credit_line = TextAreaField("Credit Line", validators=[Optional()])
