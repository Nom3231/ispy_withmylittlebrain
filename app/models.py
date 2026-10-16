# Database tables for the game.
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()


def utc_now():
    # MySQL DATETIME has no timezone, so we store UTC with the tz stripped off
    return datetime.now(timezone.utc).replace(tzinfo=None)

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)  # never store the real password
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    games = db.relationship('GameScore', backref='player', lazy='dynamic', cascade='all, delete-orphan')
    feedbacks = db.relationship('Feedback', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    active_game = db.relationship('ActiveGame', backref='player', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        # Hash it so even if someone opens the database they cant read the password
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def total_points(self):
        # Only winning rounds add points
        result = db.session.query(func.sum(GameScore.score)).filter(GameScore.user_id == self.id, GameScore.won == True).scalar()
        return int(result) if result else 0

    def get_progression(self, levels_config):
        # Work out which ranks this player has unlocked from their total points
        pts = self.total_points
        current_lvl = 1

        for lvl_num in sorted(levels_config.keys()):
            if pts >= levels_config[lvl_num]['points_required']:
                current_lvl = lvl_num
            else:
                break

        current_cfg = levels_config[current_lvl]
        next_thresh = current_cfg['next_threshold']
        prev_req = current_cfg['points_required']

        if next_thresh is not None:
            needed = next_thresh - pts
            span = next_thresh - prev_req
            earned_in_lvl = pts - prev_req
            pct = min(100, max(0, int((earned_in_lvl / span) * 100)))
        else:
            needed = 0
            pct = 100

        unlocked = [lvl for lvl in levels_config if levels_config[lvl]['points_required'] <= pts]

        return {
            'total_points': pts,
            'current_level': current_lvl,
            'level_name': current_cfg['name'],
            'next_threshold': next_thresh,
            'points_needed': needed,
            'progress_pct': pct,
            'unlocked_levels': unlocked
        }

    def get_stats(self):
        # Numbers shown on the profile page
        total_games = self.games.count()
        total_wins = self.games.filter_by(won=True).count()
        win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
        overall_best = self.games.filter_by(won=True).order_by(GameScore.score.desc()).first()
        best_rows = (
            db.session.query(GameScore.difficulty, func.max(GameScore.score))
            .filter(GameScore.user_id == self.id, GameScore.won == True)
            .group_by(GameScore.difficulty)
            .all()
        )
        best_by_level = {str(level): 0 for level in range(1, 11)}
        for difficulty, score in best_rows:
            if difficulty in best_by_level and score:
                best_by_level[difficulty] = int(score)

        return {
            'total_games': total_games,
            'total_wins': total_wins,
            'total_points': self.total_points,
            'win_rate': round(win_rate, 1),
            'best_score': overall_best.score if overall_best else 0,
            'best_by_level': best_by_level
        }

    def __repr__(self):
        return f'<User {self.username}>'


class GameScore(db.Model):
    # One row for every finished round (win or loss). Profile uses all of them.
    __tablename__ = 'game_scores'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    difficulty = db.Column(db.String(20), nullable=False, default='1')  # level as text, like "1" or "10"
    target_number = db.Column(db.Integer, nullable=False)
    attempts_used = db.Column(db.Integer, nullable=False)
    max_attempts = db.Column(db.Integer, nullable=False, default=10)
    score = db.Column(db.Integer, nullable=False, default=0)
    won = db.Column(db.Boolean, nullable=False, default=False)
    played_at = db.Column(db.DateTime, default=utc_now, index=True)

    def __repr__(self):
        return f'<GameScore User={self.user_id} Score={self.score} Won={self.won}>'


class Feedback(db.Model):
    # Messages from the contact/feedback form
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=5)
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f'<Feedback from {self.name}>'


class ContentUpdate(db.Model):
    # Announcements the admin posts on the home page
    __tablename__ = 'content_updates'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f'<ContentUpdate {self.title}>'


class ActiveGame(db.Model):
    # The round that is happening now. The secret number stays here, not in the browser.
    __tablename__ = 'active_games'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    level = db.Column(db.Integer, nullable=False, default=1)
    level_name = db.Column(db.String(64), nullable=False)
    round_num = db.Column(db.Integer, nullable=False, default=1)
    min_value = db.Column(db.Integer, nullable=False)
    max_value = db.Column(db.Integer, nullable=False)
    base_max = db.Column(db.Integer, nullable=False)
    max_attempts = db.Column(db.Integer, nullable=False)
    base_multiplier = db.Column(db.Float, nullable=False)
    color = db.Column(db.String(20), nullable=False)
    target = db.Column(db.Integer, nullable=False)  # the secret number
    attempts_used = db.Column(db.Integer, nullable=False, default=0)
    guesses = db.Column(db.JSON, nullable=False)  # list of hints we already showed
    status = db.Column(db.String(20), nullable=False, default='in_progress')
    score = db.Column(db.Integer, nullable=False, default=0)
    effective_mult = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<ActiveGame User={self.user_id} Level={self.level} Status={self.status}>'
