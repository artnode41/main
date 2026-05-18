from flask import Blueprint, render_template
from flask_security import login_required

bp = Blueprint("exhibitions", __name__, url_prefix="/admin/exhibitions")

@bp.route("/")
@login_required
def index():
    return render_template("stub.html", title="Exhibitions", coming="Phase 3")
