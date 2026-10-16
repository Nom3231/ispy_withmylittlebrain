from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app

COOKIE_NAME = 'access_token'
ALGORITHM = 'HS256'


def issue_access_token(user):
    now = datetime.now(timezone.utc)
    lifetime = int(current_app.config['AUTH_TOKEN_MAX_AGE'])
    payload = {
        'sub': str(user.id),
        'username': user.username,
        'adm': bool(user.is_admin),
        'iat': now,
        'exp': now + timedelta(seconds=lifetime),
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm=ALGORITHM)


def decode_access_token(token):
    if not token:
        return None
    try:
        return jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=[ALGORITHM],
        )
    except jwt.PyJWTError:
        return None


def token_from_request(req):
    header = req.headers.get('Authorization', '')
    if header.lower().startswith('bearer '):
        return header.split(' ', 1)[1].strip()
    return req.cookies.get(COOKIE_NAME)


def set_access_cookie(response, token):
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=int(current_app.config['AUTH_TOKEN_MAX_AGE']),
        httponly=True,
        samesite='Lax',
        path='/',
        secure=bool(current_app.config.get('AUTH_TOKEN_SECURE')),
    )
    return response


def clear_access_cookie(response):
    response.delete_cookie(COOKIE_NAME, path='/')
    return response
