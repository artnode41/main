from flask import Blueprint

bp = Blueprint("artists", __name__, url_prefix="/admin/artists")

from . import routes
