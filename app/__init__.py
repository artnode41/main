import os
from flask import Flask
from flask_babel import Babel
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
    app.config["SECURITY_RECOVERABLE"] = True
    app.config["SECURITY_RESET_PASSWORD_WITHIN"] = "1 days"
    app.config["WTF_CSRF_SECRET_KEY"] = os.environ.get("SECRET_KEY", "csrf-secret")
    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "mail.infomaniak.com")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", "")
    app.config["PAYREXX_INSTANCE"] = os.environ.get("PAYREXX_INSTANCE", "")
    app.config["PAYREXX_API_SECRET"] = os.environ.get("PAYREXX_API_SECRET", "")

    db.init_app(app)
    migrate.init_app(app, db)
    security.init_app(app, user_datastore)

    # ── Flask-Babel ──────────────────────────────────────────
    app.config["BABEL_DEFAULT_LOCALE"] = "de"
    app.config["BABEL_SUPPORTED_LOCALES"] = ["de", "fr", "it", "en"]
    app.config["BABEL_TRANSLATION_DIRECTORIES"] = "translations"

    babel = Babel()

    def get_locale():
        from flask import session, request
        lang = session.get("lang")
        if lang and lang in app.config["BABEL_SUPPORTED_LOCALES"]:
            return lang
        return request.accept_languages.best_match(
            app.config["BABEL_SUPPORTED_LOCALES"], default="de"
        )

    babel.init_app(app, locale_selector=get_locale)

    # ── Swiss formatting filters ─────────────────────────────
    def ch_date(value, fmt="short"):
        if not value:
            return ""
        if fmt == "long":
            return value.strftime("%d. %B %Y")
        return value.strftime("%d.%m.%Y")

    def ch_currency(value, currency="CHF"):
        if value is None:
            return ""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return str(value)
        # Format with apostrophe thousands separator
        parts = f"{v:,.2f}".split(".")
        integer = parts[0].replace(",", "'")
        return f"{currency} {integer}.{parts[1]}"

    app.jinja_env.filters["ch_date"] = ch_date

    # ── MinIO helper ─────────────────────────────────────────
    def upload_to_minio(data, object_name, content_type="image/jpeg"):
        import os, io
        from minio import Minio
        client = Minio(
            os.environ.get("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.environ.get("MINIO_ROOT_USER", "minioadmin"),
            secret_key=os.environ.get("MINIO_ROOT_PASSWORD"),
            secure=False
        )
        bucket = os.environ.get("MINIO_BUCKET", "artnode-media")
        client.put_object(bucket, object_name, io.BytesIO(data), len(data), content_type=content_type)
        return f"/media/{bucket}/{object_name}"

    app.upload_to_minio = upload_to_minio

    # ── Translation helper ───────────────────────────────────
    def get_trans(obj, field, lang=None, fallback=None):
        """Get translated field value with fallback."""
        from flask import session
        if lang is None:
            lang = session.get("lang", "de")
        trans = getattr(obj, "translations", None) or {}
        # Try requested language
        val = trans.get(lang, {}).get(field)
        if val:
            return val, None
        # Try fallback language
        if fallback and fallback != lang:
            val = trans.get(fallback, {}).get(field)
            if val:
                return val, fallback
        # Try any available language
        for l, t in trans.items():
            if t.get(field):
                return t[field], l
        # Fall back to original field
        orig = getattr(obj, field, None)
        return orig, None

    app.jinja_env.globals["get_trans"] = get_trans
    app.jinja_env.filters["ch_currency"] = ch_currency

    @app.route("/health")
    def health():
        return {"status": "ok", "service": "artnode"}


    @app.route("/webhook/payrexx", methods=["POST"])
    def payrexx_webhook():
        from .blueprints.sales.routes import webhook_payrexx
        return webhook_payrexx()

    @app.route("/admin/login")
    def admin_login_redirect():
        return redirect("/login")

    from .blueprints.artworks import bp as artworks_bp
    from .blueprints.artists import bp as artists_bp
    from .blueprints.contacts import bp as contacts_bp
    from .blueprints.exhibitions import bp as exhibitions_bp
    from .blueprints.sales import bp as sales_bp
    from .blueprints.fairs import bp as fairs_bp
    from .blueprints.settings import bp as settings_bp
    from .blueprints.public import bp as public_bp
    from .blueprints.viewing_rooms import bp as viewing_rooms_bp
    from .blueprints.public_viewing import bp as public_viewing_bp
    from .blueprints.blog import bp as blog_bp
    app.register_blueprint(artworks_bp)
    app.register_blueprint(artists_bp)
    from .blueprints.export import bp as export_bp
    app.register_blueprint(export_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(exhibitions_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(fairs_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(viewing_rooms_bp)
    app.register_blueprint(public_viewing_bp)
    app.register_blueprint(blog_bp)

    from flask_mail import Mail
    mail = Mail(app)
    app.extensions["mail"] = mail
    from datetime import date
    @app.context_processor
    def inject_today():
        return dict(today_date=date.today())

    from flask_wtf.csrf import generate_csrf
    @app.context_processor
    def inject_csrf():
        return dict(csrf_token=generate_csrf)

    import markupsafe
    @app.template_filter("nl2br")
    def nl2br(value):
        if not value: return ""
        return markupsafe.Markup(markupsafe.escape(value).replace("\n", markupsafe.Markup("<br>")))

    return app
