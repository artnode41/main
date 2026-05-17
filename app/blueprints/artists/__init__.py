from flask import Blueprint

bp = Blueprint("artists", __name__, url_prefix="/artists")

from . import routes
