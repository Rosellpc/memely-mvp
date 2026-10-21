import hashlib
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request, session
from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import Unauthorized, TooManyRequests
from werkzeug.security import check_password_hash, generate_password_hash

from backend.database import get_db
from backend.models import LoginLimit, Usuario
from backend.validation import body, email_value, password_value, text_value

auth = Blueprint('auth', __name__)
DUMMY_HASH = generate_password_hash('dummy-password-never-used-for-login')


def user_json(user):
    return {'id': user.id, 'nombre': user.nombre, 'email': user.email}


def login_required(function):
    @wraps(function)
    def decorated(*args, **kwargs):
        user_id = session.get('usuario_id')
        user = get_db().get(Usuario, user_id) if isinstance(user_id, int) else None
        if user is None:
            session.clear()
            raise Unauthorized('Inicia sesión para continuar.')
        g.user = user
        return function(*args, **kwargs)
    return decorated


def limit_auth():
    # Uses the direct peer, never trusts spoofable X-Forwarded-For headers.
    # Configure trusted proxy handling before putting this service behind a proxy.
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=15)
    key = hashlib.sha256((request.remote_addr or 'unknown').encode()).hexdigest()
    db = get_db()
    db.execute(delete(LoginLimit).where(LoginLimit.expira_en < now))
    statement = insert(LoginLimit).values(clave=key, intentos=1, expira_en=expires)
    statement = statement.on_conflict_do_update(
        index_elements=[LoginLimit.clave],
        set_={'intentos': case((LoginLimit.expira_en <= now, 1), else_=LoginLimit.intentos + 1),
              'expira_en': case((LoginLimit.expira_en <= now, expires), else_=LoginLimit.expira_en)},
    ).returning(LoginLimit.intentos)
    attempts = db.execute(statement).scalar_one()
    db.commit()
    if attempts > current_app.config['AUTH_LIMIT']:
        raise TooManyRequests('Demasiados intentos. Espera 15 minutos antes de reintentar.', retry_after=900)


@auth.post('/api/usuarios')
def register():
    limit_auth()
    data = body()
    name = text_value(data, 'nombre', 2, 100)
    email = email_value(data)
    password = password_value(data)
    db = get_db()
    user = Usuario(nombre=name, email=email, password_hash=generate_password_hash(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return jsonify(error='email_exists', message='No se pudo registrar ese correo. Prueba iniciar sesión.'), 409
    session.clear()
    session['usuario_id'] = user.id
    session.permanent = True
    return jsonify(usuario=user_json(user)), 201


@auth.post('/api/login')
def login():
    limit_auth()
    data = body()
    email = email_value(data)
    password = password_value(data)
    user = get_db().scalar(select(Usuario).where(Usuario.email == email))
    valid = check_password_hash(user.password_hash if user else DUMMY_HASH, password)
    if user is None or not valid:
        raise Unauthorized('Correo o contraseña incorrectos.')
    session.clear()
    session['usuario_id'] = user.id
    session.permanent = True
    return jsonify(usuario=user_json(user))


@auth.get('/api/me')
@login_required
def me():
    return jsonify(usuario=user_json(g.user))


@auth.post('/api/logout')
def logout():
    session.clear()
    return '', 204
