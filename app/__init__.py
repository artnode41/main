import os
from flask import Flask, redirect, url_for
from .extensions import db, migrate, security
from .models import user_datastore


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SECURITY_PASSWORD_SALT"] = os.environ.get("SECRET_KEY", "salt")
    app.config["SECURITY_LOGIN_URL"] = "/login"
    app.config["SECURITY_LOGOUT_URL"] = "/logout"
    app.config["SECURITY_POST_LOGIN_VIEW"] = "/admin/artworks"
    app.config["SECURITY_POST_LOGOUT_VIEW"] = "/login"
    app.config["SECURITY_SEND_REGISTER_EMAIL"] = False
    app.config["SECURITY_REGISTERABLE"] = False
    app.config["WTF_CSRF_SECRET_KEY"] = os.environ.get("SECRET_KEY", "csrf-secret")

    db.init_app(app)
    migrate.init_app(app, db)
    security.init_app(app, user_datastore)

    @app.route("/health")
    def health():
        return {"status": "ok", "service": "artnode"}

    @app.route("/")
    def index():
        return redirect(url_for("artworks.index"))

    @app.route("/admin/login")
    def admin_login_redirect():
        return redirect("/login")

    # Legacy redirects for old URLs without /admin prefix
    @app.route("/artworks")
    @app.route("/artworks/<path:rest>")
    def redirect_artworks(rest=""):
        return redirect("/admin/artworks/" + rest if rest else "/admin/artworks")

    @app.route("/artists")
    @app.route("/artists/<path:rest>")
    def redirect_artists(rest=""):
        return redirect("/admin/artists/" + rest if rest else "/admin/artists/")

    @app.route("/contacts")
    @app.route("/contacts/<path:rest>")
    def redirect_contacts(rest=""):
        return redirect("/admin/contacts/" + rest if rest else "/admin/contacts/")

    @app.route("/sales")
    @app.route("/sales/<path:rest>")
    def redirect_sales(rest=""):
        return redirect("/admin/sales/" + rest if rest else "/admin/sales/")

    from .blueprints.artworks import bp as artworks_bp
    from .blueprints.artists import bp as artists_bp
    from .blueprints.contacts import bp as contacts_bp
    from .blueprints.exhibitions import bp as exhibitions_bp
    from .blueprints.sales import bp as sales_bp
    from .blueprints.fairs import bp as fairs_bp

    app.register_blueprint(artworks_bp)
    app.register_blueprint(artists_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(exhibitions_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(fairs_bp)

    return app
