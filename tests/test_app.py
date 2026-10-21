from datetime import date, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from backend.models import Usuario

HEADERS = {'X-Memely-Client': 'web'}
PASSWORD = 'Una frase de prueba para Memely!'


def register(client, email='ana@example.com'):
    return client.post('/api/usuarios', json={'nombre': 'Ana', 'email': email, 'password': PASSWORD}, headers=HEADERS)


def profile(client, **updates):
    data = {'fecha_nacimiento': '1994-03-12', 'sexo_registrado': 'no_indicado',
            'actividad': 'media', 'preferencia': 'vegetarian', **updates}
    return client.post('/api/profile', json=data, headers=HEADERS)


def create_plan(client):
    monday = date.today() - timedelta(days=date.today().weekday())
    return client.post('/api/plans', json={'nombre': 'Mi semana', 'fecha_inicio': monday.isoformat()}, headers=HEADERS)


def test_auth_flow_and_password_hash(client, app):
    assert client.get('/api/me').status_code == 401
    assert register(client).status_code == 201
    assert client.get('/api/me').json['usuario']['email'] == 'ana@example.com'
    with app.extensions['postgres_sessions']() as db:
        user = db.scalar(select(Usuario))
        assert user.password_hash != PASSWORD
        assert check_password_hash(user.password_hash, PASSWORD)
    assert 'HttpOnly' in client.get('/api/me').headers.get('Set-Cookie', '') or client.get_cookie('session').http_only
    assert client.post('/api/logout', json={}, headers=HEADERS).status_code == 204
    assert client.get('/api/me').status_code == 401
    assert client.post('/api/login', json={'email': 'ANA@example.com', 'password': PASSWORD}, headers=HEADERS).status_code == 200
    assert register(client).status_code == 409


def test_invalid_login(client):
    register(client)
    response = client.post('/api/login', json={'email': 'ana@example.com', 'password': 'wrong-password-long-enough'}, headers=HEADERS)
    assert response.status_code == 401
    missing = client.post('/api/login', json={'email': 'missing@example.com', 'password': PASSWORD}, headers=HEADERS)
    assert missing.status_code == 401 and response.json == missing.json


def test_full_plan_flow_and_persistence(client, app):
    register(client)
    assert create_plan(client).status_code == 409
    assert profile(client).status_code == 200
    response = create_plan(client)
    assert response.status_code == 201
    plan = response.json['plan']
    assert len(plan['days']) == 7
    assert sum(len(day['meals']) for day in plan['days']) == 21
    assert 'Pollo' not in str(plan)
    meal_id = plan['days'][0]['meals'][0]['id']
    url = f"/api/plans/{plan['id']}/meals/{meal_id}"
    assert client.patch(url, json={'completed': True}, headers=HEADERS).status_code == 200
    assert client.get('/api/plans/latest').json['plan']['days'][0]['meals'][0]['completed']
    # New app instance and session, same database: data must survive worker replacement.
    from backend.app import create_app
    second_app = create_app(dict(app.config))
    second_client = second_app.test_client()
    second_client.set_cookie('session', client.get_cookie('session').value)
    assert second_client.get('/api/plans/latest').json['plan']['id'] == plan['id']
    second_app.extensions['postgres_engine'].dispose()
    assert client.delete(f"/api/plans/{plan['id']}", headers=HEADERS).status_code == 204
    assert client.get('/api/plans').json['total'] == 0
    with app.extensions['postgres_engine'].connect() as connection:
        assert connection.scalar(text('SELECT count(*) FROM comidas')) == 0


def test_user_isolation(client, app):
    register(client)
    profile(client)
    plan = create_plan(client).json['plan']
    record = client.post('/api/measurements', json={'peso_kg': '68.50', 'estatura_cm': '172.00'}, headers=HEADERS).json['measurement']
    other = app.test_client()
    register(other, 'other@example.com')
    assert other.get('/api/profile').json['profile'] is None
    assert other.get('/api/plans').json['total'] == 0
    assert other.get('/api/measurements').json['total'] == 0
    assert other.get(f"/api/plans/{plan['id']}").status_code == 404
    assert other.delete(f"/api/plans/{plan['id']}", headers=HEADERS).status_code == 404
    assert other.patch(f"/api/plans/{plan['id']}/meals/{plan['days'][0]['meals'][0]['id']}", json={'completed': True}, headers=HEADERS).status_code == 404
    assert other.delete(f"/api/measurements/{record['id']}", headers=HEADERS).status_code == 404


@pytest.mark.parametrize('value', [0, -1, True, None, 'NaN', 'Infinity', '99999', '65.555', {}, []])
def test_invalid_measurements(client, value):
    register(client)
    response = client.post('/api/measurements', json={'peso_kg': value, 'estatura_cm': '170.00'}, headers=HEADERS)
    assert response.status_code == 400


def test_measurement_history_and_delete(client):
    register(client)
    first = client.post('/api/measurements', json={'peso_kg': '68.50', 'estatura_cm': '170.00'}, headers=HEADERS)
    assert first.status_code == 201
    second = client.post('/api/measurements', json={'peso_kg': '69.25', 'estatura_cm': '170.00'}, headers=HEADERS)
    assert second.status_code == 201
    history = client.get('/api/measurements').json
    assert history['total'] == 2
    assert history['measurements'][0]['peso_kg'] == '69.25'
    assert client.delete(f"/api/measurements/{first.json['measurement']['id']}", headers=HEADERS).status_code == 204
    assert client.get('/api/measurements').json['total'] == 1


@pytest.mark.parametrize('updates', [{'fecha_nacimiento': '2999-01-01'}, {'fecha_nacimiento': 'invalid'},
    {'sexo_registrado': []}, {'actividad': 'invalid'}, {'preferencia': 'invalid'}])
def test_profile_validation(client, updates):
    register(client)
    assert profile(client, **updates).status_code == 400


def test_profile_update_and_age(client):
    register(client)
    assert profile(client).status_code == 200
    assert profile(client, actividad='alta').status_code == 200
    data = client.get('/api/profile').json['profile']
    born = date(1994, 3, 12)
    today = date.today()
    assert data['edad'] == today.year - born.year - ((today.month, today.day) < (3, 12))
    assert data['actividad'] == 'alta'


def test_rate_limit_shared_in_database(client, app):
    app.config['AUTH_LIMIT'] = 2
    assert register(client).status_code == 201
    assert register(client).status_code == 409
    response = register(app.test_client(), 'second@example.com')
    assert response.status_code == 429
    assert response.headers['Retry-After'] == '900'


def test_request_security(client):
    assert client.post('/api/usuarios', json={}).status_code == 403
    assert client.post('/api/usuarios', data='hello', headers=HEADERS).status_code == 415
    assert client.post('/api/usuarios', data='{', content_type='application/json', headers=HEADERS).status_code == 400
    assert client.post('/api/usuarios', json={'nombre': 'a' * 20000}, headers=HEADERS).status_code == 413
    assert client.get('/api/me').headers['Cache-Control'] == 'no-store'
    assert client.get('/').headers['Content-Security-Policy']
    for url in ('/.env', '/backend/app.py', '/migrations/env.py'):
        assert client.get(url).status_code == 404


def test_database_constraints(app):
    engine = app.extensions['postgres_engine']
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("INSERT INTO mediciones (usuario_id, peso_kg, estatura_cm) VALUES (999, 60, 170)"))
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("INSERT INTO usuarios (nombre,email,password_hash) VALUES ('Test','constraint@example.com','hash')"))
        connection.execute(text("INSERT INTO mediciones (usuario_id,peso_kg,estatura_cm) SELECT id,-1,170 FROM usuarios LIMIT 1"))


def test_assets_and_health(client):
    for path in ('/', '/menu.html', '/css/styles.css', '/js/app.js', '/api/health', '/api/health/live'):
        assert client.get(path).status_code == 200
    assert client.get('/api/health').json['database'] == 'postgresql'


def test_pagination(client, app):
    register(client)
    with app.extensions['postgres_engine'].begin() as connection:
        connection.execute(text('INSERT INTO mediciones (usuario_id,peso_kg,estatura_cm) SELECT 1,68.50,172 FROM generate_series(1,21)'))
    first = client.get('/api/measurements').json
    second = client.get('/api/measurements?page=2').json
    assert first['total'] == 21 and len(first['measurements']) == 20
    assert len(second['measurements']) == 1
    assert client.get('/api/measurements?page=invalid').status_code == 400
    assert client.get('/api/plans?page=invalid').status_code == 400


@pytest.mark.parametrize('start', ['9999-12-27', '2026-10-20'])
def test_plan_dates(client, start):
    register(client)
    profile(client)
    assert client.post('/api/plans', json={'nombre': 'Mi semana', 'fecha_inicio': start}, headers=HEADERS).status_code == 400
