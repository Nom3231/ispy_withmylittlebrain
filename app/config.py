import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))


def _required(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise RuntimeError(
            f'Missing required setting {name}. Copy .env.example to .env and fill it in.'
        )
    return value


class Config:
    SECRET_KEY = _required('SECRET_KEY')

    DB_USER = os.environ.get('DB_USER', 'root')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'ispy_brain_db')

    _database_url = os.environ.get('DATABASE_URL', '').strip()
    if _database_url:
        SQLALCHEMY_DATABASE_URI = _database_url
    else:
        _db_pass = quote_plus(_required('DB_PASS'))
        SQLALCHEMY_DATABASE_URI = (
            f'mysql+pymysql://{DB_USER}:{_db_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        )

    AUTH_TOKEN_MAX_AGE = int(os.environ.get('AUTH_TOKEN_MAX_AGE', str(60 * 60 * 12)))
    AUTH_TOKEN_SECURE = os.environ.get('AUTH_TOKEN_SECURE', '').strip().lower() in ('1', 'true', 'yes')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True
    }

    # 10-Level Progressive Difficulty Curve (Ranges scale up to 100,000)
    GAME_LEVELS = {
        1: {'name': 'Novice Scout', 'min': 0, 'base_max': 50, 'max_attempts': 10, 'base_multiplier': 0.3, 'points_required': 0, 'next_threshold': 10000, 'color': '#39ff14'},
        2: {'name': 'Apprentice Mind', 'min': 0, 'base_max': 200, 'max_attempts': 10, 'base_multiplier': 0.6, 'points_required': 10000, 'next_threshold': 40000, 'color': '#00f0ff'},
        3: {'name': 'Code Breaker', 'min': 0, 'base_max': 600, 'max_attempts': 10, 'base_multiplier': 1.0, 'points_required': 40000, 'next_threshold': 90000, 'color': '#ffb703'},
        4: {'name': 'Cipher Seeker', 'min': 0, 'base_max': 1500, 'max_attempts': 10, 'base_multiplier': 1.5, 'points_required': 90000, 'next_threshold': 160000, 'color': '#fb8500'},
        5: {'name': 'Logic Strategist', 'min': 0, 'base_max': 3500, 'max_attempts': 10, 'base_multiplier': 2.2, 'points_required': 160000, 'next_threshold': 250000, 'color': '#a855f7'},
        6: {'name': 'Neural Hacker', 'min': 0, 'base_max': 8000, 'max_attempts': 10, 'base_multiplier': 3.0, 'points_required': 250000, 'next_threshold': 360000, 'color': '#ec4899'},
        7: {'name': 'Quantum Sleuth', 'min': 0, 'base_max': 18000, 'max_attempts': 10, 'base_multiplier': 4.0, 'points_required': 360000, 'next_threshold': 500000, 'color': '#38bdf8'},
        8: {'name': 'Matrix Commander', 'min': 0, 'base_max': 35000, 'max_attempts': 10, 'base_multiplier': 5.5, 'points_required': 500000, 'next_threshold': 700000, 'color': '#f43f5e'},
        9: {'name': 'Grand Tactician', 'min': 0, 'base_max': 65000, 'max_attempts': 10, 'base_multiplier': 7.5, 'points_required': 700000, 'next_threshold': 1000000, 'color': '#e11d48'},
        10: {'name': 'Cyber Mastermind', 'min': 0, 'base_max': 100000, 'max_attempts': 10, 'base_multiplier': 10.0, 'points_required': 1000000, 'next_threshold': None, 'color': '#ffd700'}
    }

    ORGANIZATION_INFO = {
        'name': 'I Spy Brain Studios Inc.',
        'email': 'support@ispybrain.com',
        'phone': '+1 (800) 555-BRAIN (2724)',
        'address': '100 Brainiac Boulevard, Suite 404, Tech City, TC 94016'
    }
