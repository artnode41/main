from flask import Blueprint, render_template
from flask_security import login_required

bp = Blueprint("fairs", __name__, url_prefix="/admin/fairs")

@bp.route("/")
@login_required
def index():
    return render_template("stub.html", title="Fairs", coming="Phase 3")
