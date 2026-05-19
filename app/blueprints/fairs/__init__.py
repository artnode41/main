from flask import Blueprint

bp = Blueprint("fairs", __name__, url_prefix="/admin/fairs")

from . import routes
