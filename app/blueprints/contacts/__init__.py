from flask import Blueprint

bp = Blueprint("contacts", __name__, url_prefix="/admin/contacts")

from . import routes
