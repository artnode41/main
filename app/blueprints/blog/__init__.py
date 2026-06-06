from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_security import login_required, current_user
from ...models import BlogPost
from ...extensions import db
from datetime import datetime, timezone
import re

bp = Blueprint("blog", __name__, url_prefix="/admin/blog")

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:300]


@bp.route("/")
@login_required
def index():
    posts = BlogPost.query.filter_by(
        tenant_id=current_user.tenant_id
    ).order_by(BlogPost.translation_group_id, BlogPost.language).all()
    # Group by translation_group_id
    groups = {}
    ungrouped = []
    for post in posts:
        if post.translation_group_id:
            groups.setdefault(post.translation_group_id, []).append(post)
        else:
            ungrouped.append(post)
    return render_template("blog/index.html", groups=groups, ungrouped=ungrouped)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    group_id = request.args.get("group_id", type=int)
    default_lang = request.args.get("lang", "de")
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        language = request.form.get("language", "de")
        is_published = bool(request.form.get("is_published"))
        group_id = request.form.get("translation_group_id", type=int)
        if not title or not body:
            flash("Title and body are required.", "error")
            return render_template("blog/form.html", post=None, default_lang=language, group_id=group_id)
        slug = slugify(f"{language}-{title}")
        existing = BlogPost.query.filter_by(
            tenant_id=current_user.tenant_id, slug=slug
        ).first()
        if existing:
            slug = f"{slug}-{int(datetime.now().timestamp())}"
        post = BlogPost(
            tenant_id=current_user.tenant_id,
            title=title,
            slug=slug,
            body=body,
            language=language,
            translation_group_id=group_id,
            is_published=is_published,
            published_at=datetime.now(timezone.utc) if is_published else None,
        )
        db.session.add(post)
        db.session.flush()
        # If no group_id, this post becomes its own group
        if not group_id:
            post.translation_group_id = post.id
        db.session.commit()
        flash("Post created.", "success")
        return redirect(url_for("blog.index"))
    return render_template("blog/form.html", post=None, default_lang=default_lang, group_id=group_id)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    post = BlogPost.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    if request.method == "POST":
        post.title = request.form.get("title", "").strip()
        post.body = request.form.get("body", "").strip()
        post.language = request.form.get("language", post.language)
        was_published = post.is_published
        post.is_published = bool(request.form.get("is_published"))
        if post.is_published and not was_published:
            post.published_at = datetime.now(timezone.utc)
        elif not post.is_published:
            post.published_at = None
        db.session.commit()
        flash("Post updated.", "success")
        return redirect(url_for("blog.index"))
    return render_template("blog/form.html", post=post, default_lang=post.language, group_id=post.translation_group_id)


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    post = BlogPost.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted.", "success")
    return redirect(url_for("blog.index"))
