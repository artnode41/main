from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField
from wtforms.validators import Optional, Length, Email


class GallerySettingsForm(FlaskForm):
    # Identity
    name = StringField("Internal Name", validators=[Length(max=200)])
    public_name = StringField("Public Name (displayed on website)", validators=[Optional(), Length(max=200)])
    tagline = StringField("Tagline", validators=[Optional(), Length(max=300)])
    about_text = TextAreaField("About Text", validators=[Optional()])

    # Contact
    address = TextAreaField("Address", validators=[Optional()])
    zip_code = StringField("ZIP Code", validators=[Optional(), Length(max=20)])
    city = StringField("City", validators=[Optional(), Length(max=100)])
    country = StringField("Country", validators=[Optional(), Length(max=2)])
    phone = StringField("Phone", validators=[Optional(), Length(max=50)])
    email = StringField("Admin Email", validators=[Optional(), Email(), Length(max=255)])
    contact_email = StringField("Public Contact Email", validators=[Optional(), Email(), Length(max=255)])
    website = StringField("Website URL", validators=[Optional(), Length(max=255)])
    maintenance_mode = BooleanField("Maintenance Mode")
    instagram_url = StringField("Instagram URL", validators=[Optional(), Length(max=255)])

    # Financial
    currency = SelectField("Default Currency", choices=[
        ("CHF", "CHF — Swiss Franc"),
        ("EUR", "EUR — Euro"),
        ("USD", "USD — US Dollar"),
        ("GBP", "GBP — British Pound"),
    ])
    locale = SelectField("Language", choices=[
        ("de", "Deutsch"),
        ("fr", "Français"),
        ("it", "Italiano"),
        ("en", "English"),
    ])
    vat_number = StringField("VAT / MWST Number", validators=[Optional(), Length(max=30)])
    iban = StringField("IBAN", validators=[Optional(), Length(max=34)])
    vat_scheme_default = SelectField("Default VAT Scheme", choices=[
        ("standard", "Standard (show VAT rate and amount)"),
        ("margin", "Margin scheme (Margenbesteuerung)"),
        ("none", "No VAT (Keine MWST)"),
    ])
