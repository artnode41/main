from flask import Blueprint

bp = Blueprint("artworks", __name__, url_prefix="")

from . import routes
