import logging
import os
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from backend.api import api
from backend.auth import auth
from backend.database import get_db, init_database

ROOT = Path(__file__).resolve().parent.parent


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        MAX_CONTENT_LENGTH=16 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE', 'false').lower() == 'true',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        SESSION_REFRESH_EACH_REQUEST=False,
        AUTH_LIMIT=30,
    )
    if config:
        app.config.update(config)
    if not app.config['SECRET_KEY'] or len(app.config['SECRET_KEY']) < 32:
        raise RuntimeError('Configura SECRET_KEY con al menos 32 caracteres aleatorios.')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    init_database(app)
    app.register_blueprint(auth)
    app.register_blueprint(api)

    @app.before_request
    def protect_writes():
        if request.path.startswith('/api/') and request.method in ('POST', 'PATCH', 'DELETE', 'PUT'):
            if request.headers.get('X-Memely-Client') != 'web':
                return jsonify(error='invalid_client', message='Falta X-Memely-Client: web.'), 403
            if request.method != 'DELETE' and not request.is_json:
                return jsonify(error='json_required', message='Usa Content-Type: application/json.'), 415

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        response = error.get_response()
        response.data = app.json.dumps({'error': error.name, 'message': error.description})
        response.content_type = 'application/json'
        return response

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        get_db().rollback()
        return jsonify(error='conflict', message='Los datos entran en conflicto con un registro existente.'), 409

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        get_db().rollback()
        # Do not log SQL parameters, which may contain personal information.
        app.logger.error('Database failure: %s', type(error).__name__)
        return jsonify(error='database_unavailable', message='Base de datos no disponible. Intenta de nuevo.'), 503

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify(error='internal_error', message='No pudimos completar la solicitud.'), 500

    @app.get('/')
    def home():
        return send_from_directory(ROOT, 'index.html')

    @app.get('/<page>.html')
    def legacy_page(page):
        if page not in ('index', 'registro', 'perfil', 'menu'):
            return jsonify(error='not_found', message='Página no encontrada.'), 404
        return send_from_directory(ROOT, 'index.html')

    @app.get('/css/<path:filename>')
    def css(filename):
        return send_from_directory(ROOT / 'css', filename)

    @app.get('/js/<path:filename>')
    def javascript(filename):
        return send_from_directory(ROOT / 'js', filename)

    @app.get('/api/health/live')
    def live():
        return jsonify(status='ok')

    @app.get('/api/health')
    @app.get('/api/health/postgres')
    def health():
        # These columns also confirm that application migrations are installed.
        get_db().execute(text('SELECT preferencia FROM perfiles LIMIT 1'))
        get_db().execute(text('SELECT id FROM planes LIMIT 1'))
        return jsonify(status='ok', database='postgresql')

    return app
