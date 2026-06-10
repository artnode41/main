from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, DecimalField, BooleanField
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
    source_country = StringField("Country",
                                 validators=[Optional(), Length(max=2)])
    description = TextAreaField("Description", validators=[Optional()])
    # Art. 24a MWSTG — Acquisition fields (shown when event_type = acquisition)
    purchase_invoice_number = StringField("Purchase Invoice Number", validators=[Optional(), Length(max=100)])
    supplier_address  = TextAreaField("Supplier Address", validators=[Optional()],
                                      description="Full postal address of seller")
    supplier_vat_status = SelectField("Supplier VAT Status", validators=[Optional()],
                                       choices=[
                                           ("", "— select —"),
                                           ("private", "Private individual (no VAT)"),
                                           ("non_vat", "Non-VAT registered business"),
                                           ("vat_registered", "VAT registered (standard VAT applies)"),
                                       ])
    purchase_price    = DecimalField("Purchase Price", validators=[Optional()], places=2,
                                     description="Gross purchase price = net price (no input VAT deductible)")
    right_of_disposal = BooleanField("Signed right of disposal / declaration of ownership received")
    retention_30yr    = BooleanField("30-year retention required (Art. 24a MWSTG + revCPTO)")
