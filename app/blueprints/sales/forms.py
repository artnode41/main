from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, IntegerField
from wtforms.validators import DataRequired, Optional, NumberRange


PAYMENT_METHOD_CHOICES = [
    ("bank_transfer", "Bank Transfer"),
    ("cash", "Cash"),
    ("card", "Card"),
    ("payrexx", "Payrexx"),
    ("other", "Other"),
]

TAX_METHOD_CHOICES = [
    ("standard", "Standard VAT 8.1% (Primärmarkt)"),
    ("margin",   "Margenbesteuerung Art. 24a MWSTG (Sekundärmarkt)"),
]


class SaleForm(FlaskForm):
    buyer_id = SelectField("Buyer", coerce=int, validators=[Optional()])
    price = DecimalField("Sale Price", validators=[DataRequired()], places=2)
    currency = SelectField("Currency", choices=[
        ("CHF", "CHF"), ("EUR", "EUR"), ("USD", "USD"), ("GBP", "GBP")
    ])
    tax_method = SelectField("Tax Method", choices=TAX_METHOD_CHOICES, default="standard")
    vat_rate = DecimalField("VAT Rate (%)", validators=[Optional()],
                             places=2, default=0)
    payment_method = SelectField("Payment Method",
                                  choices=PAYMENT_METHOD_CHOICES)
    notes = TextAreaField("Notes", validators=[Optional()])
