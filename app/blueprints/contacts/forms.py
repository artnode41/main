from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Optional, Length, Email, NumberRange

ROLE_CHOICES = [
    ("collector", "Collector / Owner"),
    ("consignor", "Consignor"),
    ("consignee", "Consignee"),
    ("donor", "Donor / Patron"),
    ("seller", "Seller / Vendor"),
    ("borrower", "Borrower"),
    ("lender", "Lender"),
    ("shipper", "Shipper / Fine Art Transport"),
    ("warehouse", "Warehouse / Storage"),
    ("conservator", "Conservator / Restorer"),
    ("framer", "Framer"),
    ("insurer", "Insurer / Broker"),
    ("appraiser", "Appraiser"),
    ("expert", "Expert / Scholar"),
    ("legal", "Legal Counsel / Executor"),
    ("curator", "Curator"),
    ("vendor", "General Vendor / Service Provider"),
    ("press", "Press / Media"),
]


class ContactForm(FlaskForm):
    contact_type = SelectField("Entity Type", choices=[
        ("individual", "Individual"),
        ("institution", "Institution / Organisation"),
    ])
    first_name = StringField("First Name", validators=[Optional(), Length(max=100)])
    last_name = StringField("Last Name", validators=[Optional(), Length(max=100)])
    organisation = StringField("Organisation", validators=[Optional(), Length(max=200)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=255)])
    phone = StringField("Phone", validators=[Optional(), Length(max=50)])
    address = TextAreaField("Address", validators=[Optional()])
    zip_code = StringField("ZIP Code", validators=[Optional(), Length(max=20)])
    city = StringField("City", validators=[Optional(), Length(max=100)])
    country = StringField("Country (2-letter)", validators=[Optional(), Length(max=2)])
    notes = TextAreaField("Notes", validators=[Optional()])

    # Artist role
    is_artist = BooleanField("This contact is a represented artist")
    biography = TextAreaField("Biography", validators=[Optional()])
    birth_year = IntegerField("Birth Year", validators=[Optional(), NumberRange(min=1, max=2100)])
    death_year = IntegerField("Death Year", validators=[Optional(), NumberRange(min=1, max=2100)])
    nationality = StringField("Nationality", validators=[Optional(), Length(max=100)])
    artist_website = StringField("Artist Website", validators=[Optional(), Length(max=255)])
    is_active_representation = BooleanField("Show on public website as represented artist")
