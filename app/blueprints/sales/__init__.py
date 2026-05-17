from flask import Blueprint, render_template
from flask_security import login_required

bp = Blueprint("sales", __name__, url_prefix="/sales")

@bp.route("/")
@login_required
def index():
    return render_template("stub.html", title="Sales", coming="Phase 3")
