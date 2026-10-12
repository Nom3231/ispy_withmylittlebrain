from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import current_user
from app.models import db, Feedback, ContentUpdate, GameScore, User
from app.forms import FeedbackForm

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Fetch recent updates and top high scores
    updates = ContentUpdate.query.order_by(ContentUpdate.created_at.desc()).limit(3).all()
    recent_winners = GameScore.query.filter_by(won=True).order_by(GameScore.played_at.desc()).limit(5).all()
    total_players = User.query.count()
    total_games = GameScore.query.count()
    
    return render_template('index.html',
                           title='Home',
                           updates=updates,
                           recent_winners=recent_winners,
                           total_players=total_players,
                           total_games=total_games,
                           levels_config=current_app.config['GAME_LEVELS'])

@main_bp.route('/contact')
def contact():
    org_info = current_app.config.get('ORGANIZATION_INFO', {})
    return render_template('pages/contact.html', title='Contact Us', org_info=org_info)

@main_bp.route('/feedback', methods=['GET', 'POST'])
def feedback():
    form = FeedbackForm()
    
    # Pre-populate if logged in
    if current_user.is_authenticated and not form.is_submitted():
        form.name.data = current_user.username

    if form.validate_on_submit():
        user_id = current_user.id if current_user.is_authenticated else None
        new_feedback = Feedback(
            user_id=user_id,
            name=form.name.data,
            email=form.email.data,
            rating=int(form.rating.data),
            message=form.message.data
        )
        db.session.add(new_feedback)
        db.session.commit()
        flash('Thank you for your feedback! We appreciate your thoughts.', 'success')
        return redirect(url_for('main.feedback'))
        
    return render_template('pages/feedback.html', title='Submit Feedback', form=form)
