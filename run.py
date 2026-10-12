import os

from app import create_app
from app.models import db, User, ContentUpdate

app = create_app()

WELCOME_TITLE = "System Operational: Welcome to I Spy With My Little Brain!"
WELCOME_CONTENT = (
    "The deduction terminal is live. Ten ranks run from Novice Scout (0-50) "
    "up to Cyber Mastermind (0-100,000). Win rounds to earn points, unlock ranks, "
    "and climb the leaderboard."
)
OLD_WELCOME_SNIPPET = "difficulty cartridge"


def init_db():
    with app.app_context():
        db.create_all()

        if ContentUpdate.query.count() == 0:
            existing_admin = User.query.filter_by(is_admin=True).first()
            welcome_update = ContentUpdate(
                title=WELCOME_TITLE,
                content=WELCOME_CONTENT,
                author_id=existing_admin.id if existing_admin else None
            )
            db.session.add(welcome_update)
        else:
            stale = ContentUpdate.query.filter(ContentUpdate.content.contains(OLD_WELCOME_SNIPPET)).all()
            for item in stale:
                item.content = WELCOME_CONTENT

        db.session.commit()


if __name__ == '__main__':
    init_db()
    debug = os.environ.get('FLASK_DEBUG', '').strip().lower() in ('1', 'true', 'yes')
    print("=" * 60)
    print("I SPY WITH MY LITTLE BRAIN is running!")
    print("Open your browser at: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=debug, host='127.0.0.1', port=5000)
