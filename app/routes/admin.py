# Admin pages. These are not linked in the public menu.
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import current_user
from app.models import db, User, GameScore, Feedback, ContentUpdate, ActiveGame
from app.forms import ContentUpdateForm, AdminLoginForm
from app.routes.auth import is_safe_redirect
from app.tokens import issue_access_token, set_access_cookie

admin_bp = Blueprint('admin', __name__)


def _get_or_404(model, ident):
    row = db.session.get(model, ident)
    if row is None:
        abort(404)
    return row


def _admin_count():
    return User.query.filter_by(is_admin=True).count()


def admin_required(f):
    # If you are not an admin, just show Not Found so people dont even know this page exists
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(404)
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    # Old public signup for admins. Always 404 now.
    abort(404)


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Hidden login. You have to type /admin/login yourself.
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin.dashboard'))

    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.is_admin and user.check_password(form.password.data):
            next_page = request.args.get('next')
            if is_safe_redirect(next_page):
                response = redirect(next_page)
            else:
                response = redirect(url_for('admin.dashboard'))
            return set_access_cookie(response, issue_access_token(user))
        flash('Sign-in failed.', 'danger')

    return render_template('admin/login.html', title='Sign In', form=form)

@admin_bp.route('/')
@admin_required
def dashboard():
    # Simple counts for the command centre
    total_users = User.query.count()
    total_games = GameScore.query.count()
    total_wins = GameScore.query.filter_by(won=True).count()
    total_feedback = Feedback.query.count()

    users = User.query.order_by(User.created_at.desc()).limit(10).all()
    feedbacks = Feedback.query.order_by(Feedback.submitted_at.desc()).limit(5).all()
    updates = ContentUpdate.query.order_by(ContentUpdate.created_at.desc()).all()

    return render_template('admin/dashboard.html',
                           title='Admin Dashboard',
                           total_users=total_users,
                           total_games=total_games,
                           total_wins=total_wins,
                           total_feedback=total_feedback,
                           users=users,
                           feedbacks=feedbacks,
                           updates=updates)

@admin_bp.route('/users')
@admin_required
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', title='Manage Users', users=users)

@admin_bp.route('/user/toggle-admin/<int:user_id>', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = _get_or_404(User, user_id)
    # Dont lock yourself out. Always keep at least one admin.
    if user.is_admin and _admin_count() <= 1:
        flash('The only administrator cannot be demoted.', 'warning')
    elif user.id == current_user.id:
        flash('You cannot change your own admin status.', 'warning')
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
        status = 'granted' if user.is_admin else 'revoked'
        flash(f'Admin privileges {status} for user "{user.username}".', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = _get_or_404(User, user_id)
    if user.is_admin and _admin_count() <= 1:
        flash('The only administrator cannot be deleted.', 'danger')
    elif user.id == current_user.id:
        flash('You cannot delete your own account while logged in.', 'danger')
    else:
        username = user.username
        # Delete their scores and feedback first. Keep announcements they wrote.
        db.session.execute(db.delete(GameScore).where(GameScore.user_id == user.id))
        db.session.execute(db.delete(Feedback).where(Feedback.user_id == user.id))
        db.session.execute(db.delete(ActiveGame).where(ActiveGame.user_id == user.id))
        db.session.execute(
            db.update(ContentUpdate)
            .where(ContentUpdate.author_id == user.id)
            .values(author_id=None)
        )
        db.session.delete(user)
        db.session.commit()
        flash(
            f'User "{username}" was removed, along with their scores and feedback. '
            'Announcements they wrote were kept.',
            'success'
        )
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/feedback')
@admin_required
def manage_feedback():
    feedbacks = Feedback.query.order_by(Feedback.submitted_at.desc()).all()
    return render_template('admin/feedback.html', title='User Feedback', feedbacks=feedbacks)

@admin_bp.route('/feedback/delete/<int:feedback_id>', methods=['POST'])
@admin_required
def delete_feedback(feedback_id):
    item = _get_or_404(Feedback, feedback_id)
    db.session.delete(item)
    db.session.commit()
    flash('Feedback entry removed.', 'info')
    return redirect(url_for('admin.manage_feedback'))

@admin_bp.route('/updates', methods=['GET', 'POST'])
@admin_required
def manage_updates():
    form = ContentUpdateForm()
    if form.validate_on_submit():
        update = ContentUpdate(
            title=form.title.data,
            content=form.content.data,
            author_id=current_user.id
        )
        db.session.add(update)
        db.session.commit()
        flash('Content announcement published successfully!', 'success')
        return redirect(url_for('admin.manage_updates'))

    updates = ContentUpdate.query.order_by(ContentUpdate.created_at.desc()).all()
    return render_template('admin/updates.html', title='Manage Announcements', form=form, updates=updates)

@admin_bp.route('/updates/delete/<int:update_id>', methods=['POST'])
@admin_required
def delete_update(update_id):
    update = _get_or_404(ContentUpdate, update_id)
    db.session.delete(update)
    db.session.commit()
    flash('Announcement deleted.', 'info')
    return redirect(url_for('admin.manage_updates'))
