from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from app.config import Config
from app.models import db, User
from app.tokens import decode_access_token, token_from_request

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
csrf = CSRFProtect()

@login_manager.request_loader
def load_user_from_request(request):
    payload = decode_access_token(token_from_request(request))
    if not payload:
        return None
    try:
        user_id = int(payload.get('sub'))
    except (TypeError, ValueError):
        return None
    return db.session.get(User, user_id)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.game import game_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(game_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Pass config info globally to templates
    @app.context_processor
    def inject_global_vars():
        return {
            'app_name': 'I Spy With My Little Brain',
            'org_info': app.config.get('ORGANIZATION_INFO', {})
        }

    return app
