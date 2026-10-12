from urllib.parse import urljoin, urlparse

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from app.models import db, User
from app.forms import RegistrationForm, LoginForm

auth_bp = Blueprint('auth', __name__)


def is_safe_redirect(target):
    """Allow only same-host relative redirects. Blocks //host and backslash tricks."""
    if not target or not target.startswith('/') or target.startswith('//') or '\\' in target:
        return False
    host = urlparse(request.host_url)
    redirected = urlparse(urljoin(request.host_url, target))
    return redirected.scheme in ('http', 'https') and redirected.netloc == host.netloc

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('game.play'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('This username is already taken. Please choose another.', 'danger')
            return render_template('auth/register.html', form=form, title='Register')
        flash('Account created successfully! You can now log in and play.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', form=form, title='Register')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('game.play'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            if is_safe_redirect(next_page):
                return redirect(next_page)
            return redirect(url_for('game.play'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
            
    return render_template('auth/login.html', form=form, title='Login')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))
