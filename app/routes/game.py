import random
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from app.models import db, GameScore, ActiveGame
from app.forms import GuessForm

game_bp = Blueprint('game', __name__)


def _levels():
    return current_app.config['GAME_LEVELS']


def get_active_game(user):
    return db.session.scalar(db.select(ActiveGame).filter_by(user_id=user.id))


def present_game(game):
    """Template view of a round. The secret number is included only after a loss."""
    shown = {
        'level': game.level,
        'level_name': game.level_name,
        'round': game.round_num,
        'min': game.min_value,
        'max': game.max_value,
        'base_max': game.base_max,
        'max_attempts': game.max_attempts,
        'base_multiplier': game.base_multiplier,
        'color': game.color,
        'attempts_used': game.attempts_used,
        'guesses': game.guesses or [],
        'status': game.status,
        'score': game.score,
        'effective_mult': game.effective_mult,
    }
    if game.status == 'lost':
        shown['target'] = game.target
    return shown


def start_new_game(user, level=1, increment_round=False):
    level = int(level)
    levels_config = _levels()
    if level not in levels_config:
        level = 1

    config = levels_config[level]
    existing = get_active_game(user)
    if increment_round and existing is not None and existing.level == level and existing.status == 'won':
        round_num = existing.round_num + 1
    else:
        round_num = 1

    base_max = config['base_max']
    scaled_max = int(base_max * (1 + (round_num - 1) * 0.25))
    target = random.randint(config['min'], scaled_max)

    if existing is None:
        existing = ActiveGame(user_id=user.id, guesses=[])
        db.session.add(existing)

    existing.level = level
    existing.level_name = config['name']
    existing.round_num = round_num
    existing.min_value = config['min']
    existing.max_value = scaled_max
    existing.base_max = base_max
    existing.max_attempts = config['max_attempts']
    existing.base_multiplier = config['base_multiplier']
    existing.color = config['color']
    existing.target = target
    existing.attempts_used = 0
    existing.guesses = []
    existing.status = 'in_progress'
    existing.score = 0
    existing.effective_mult = config['base_multiplier']
    db.session.commit()
    return existing


def calculate_score(level_cfg, round_num, attempts_used, max_attempts):
    base_mult = level_cfg['base_multiplier']
    remaining = max_attempts - attempts_used + 1

    speed_factor = max(0.2, remaining / max_attempts)
    round_bonus = 1.0 + ((round_num - 1) * 0.15)

    effective_mult = round(base_mult * (0.8 + (0.5 * speed_factor)) * round_bonus, 2)
    points = int(1000 * effective_mult * (remaining + 1))
    return points, effective_mult


def _drop_legacy_cookie_game():
    """Older builds stored the secret number in the signed session cookie."""
    if session.get('game') is not None:
        session.pop('game', None)


@game_bp.route('/play', methods=['GET', 'POST'])
@login_required
def play():
    _drop_legacy_cookie_game()
    levels_config = _levels()
    progression = current_user.get_progression(levels_config)

    game = get_active_game(current_user)
    if game is None:
        game = start_new_game(current_user, 1)
        progression = current_user.get_progression(levels_config)

    if game.status != 'lost' and game.level not in progression['unlocked_levels']:
        flash(
            f"Level {game.level} is locked! You need {levels_config[game.level]['points_required']:,} total points.",
            'warning'
        )
        start_new_game(current_user, 1)
        return redirect(url_for('game.play'))

    form = GuessForm()

    if form.validate_on_submit() and game.status == 'in_progress':
        guess = form.guess.data
        min_val = game.min_value
        max_val = game.max_value

        if guess < min_val or guess > max_val:
            flash(f'Please enter a number between {min_val} and {max_val:,}.', 'warning')
            return redirect(url_for('game.play'))

        game.attempts_used += 1
        target = game.target
        current_lvl_num = game.level
        lvl_cfg = levels_config[current_lvl_num]
        attempts_left = game.max_attempts - game.attempts_used
        guesses = list(game.guesses or [])

        if guess == target:
            game.status = 'won'
            final_score, eff_mult = calculate_score(
                lvl_cfg, game.round_num, game.attempts_used, game.max_attempts
            )
            game.score = final_score
            game.effective_mult = eff_mult
            guesses.append({
                'guess': guess,
                'hint': 'Spot On! Secret number decrypted!',
                'badge': 'success'
            })
            game.guesses = guesses

            record = GameScore(
                user_id=current_user.id,
                difficulty=str(current_lvl_num),
                target_number=target,
                attempts_used=game.attempts_used,
                max_attempts=game.max_attempts,
                score=final_score,
                won=True
            )
            db.session.add(record)
            db.session.commit()

            new_prog = current_user.get_progression(levels_config)
            if new_prog['current_level'] > progression['current_level']:
                flash(f"LEVEL UP! Unlocked Level {new_prog['current_level']}: {new_prog['level_name']}!", 'success')
            else:
                flash(
                    f'Decrypted in {game.attempts_used} tries! +{final_score:,} pts ({eff_mult}x Mult)',
                    'success'
                )

        elif game.attempts_used >= game.max_attempts:
            game.status = 'lost'
            game.score = 0
            guesses.append({
                'guess': guess,
                'hint': f'10 tries failed. The secret was {target}.',
                'badge': 'danger'
            })
            game.guesses = guesses

            record = GameScore(
                user_id=current_user.id,
                difficulty=str(current_lvl_num),
                target_number=target,
                attempts_used=game.attempts_used,
                max_attempts=game.max_attempts,
                score=0,
                won=False
            )
            db.session.add(record)
            db.session.commit()
            flash(
                f'Run terminated. 10 attempts failed at Level {current_lvl_num}. '
                'The next round starts at Level 1.',
                'danger'
            )

        elif guess < target:
            guesses.append({
                'guess': guess,
                'hint': 'Too low! Aim higher.',
                'badge': 'info'
            })
            game.guesses = guesses
            db.session.commit()
            flash(f'Too low! {attempts_left} try(s) remaining.', 'info')

        else:
            guesses.append({
                'guess': guess,
                'hint': 'Too high! Aim lower.',
                'badge': 'warning'
            })
            game.guesses = guesses
            db.session.commit()
            flash(f'Too high! {attempts_left} try(s) remaining.', 'warning')

        return redirect(url_for('game.play'))

    return render_template(
        'game/play.html',
        title='Play Game',
        game=present_game(game),
        levels_config=levels_config,
        progression=progression,
        form=form
    )


@game_bp.route('/play/restart/<int:level>', methods=['POST'])
@login_required
def restart(level):
    levels_config = _levels()
    progression = current_user.get_progression(levels_config)
    current_game = get_active_game(current_user)

    # A loss sends the player back to level 1, even if they post a higher level.
    if current_game is not None and current_game.status == 'lost':
        level = 1
    elif level not in progression['unlocked_levels']:
        level = 1

    increment = (
        current_game is not None
        and current_game.status == 'won'
        and current_game.level == level
    )
    start_new_game(current_user, level, increment_round=increment)
    return redirect(url_for('game.play'))


@game_bp.route('/leaderboard')
def leaderboard():
    levels_config = _levels()
    selected_level = request.args.get('level', 'all')

    won_filters = [GameScore.won.is_(True)]
    if selected_level != 'all' and selected_level.isdigit():
        won_filters.append(GameScore.difficulty == selected_level)

    best_by_user = (
        db.session.query(
            GameScore.user_id.label('user_id'),
            func.max(GameScore.score).label('best_score'),
        )
        .filter(*won_filters)
        .group_by(GameScore.user_id)
        .subquery()
    )

    # One row per player: their current personal best. If two rounds tied, keep the latest.
    best_row_id = (
        db.session.query(
            GameScore.user_id.label('user_id'),
            func.max(GameScore.id).label('score_id'),
        )
        .join(
            best_by_user,
            db.and_(
                GameScore.user_id == best_by_user.c.user_id,
                GameScore.score == best_by_user.c.best_score,
            ),
        )
        .filter(*won_filters)
        .group_by(GameScore.user_id)
        .subquery()
    )

    top_scores = (
        GameScore.query.options(joinedload(GameScore.player))
        .join(best_row_id, GameScore.id == best_row_id.c.score_id)
        .order_by(GameScore.score.desc(), GameScore.played_at.asc())
        .limit(20)
        .all()
    )

    return render_template(
        'game/leaderboard.html',
        title='Leaderboard',
        top_scores=top_scores,
        levels_config=levels_config,
        selected_level=selected_level
    )


@game_bp.route('/profile')
@login_required
def profile():
    levels_config = _levels()
    progression = current_user.get_progression(levels_config)
    stats = current_user.get_stats()
    history = current_user.games.order_by(GameScore.played_at.desc()).limit(25).all()

    return render_template(
        'game/profile.html',
        title=f"{current_user.username}'s Profile",
        stats=stats,
        progression=progression,
        levels_config=levels_config,
        history=history
    )
