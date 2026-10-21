import os

from flask import current_app, g
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker


def database_url():
    if os.environ.get('DATABASE_URL'):
        return os.environ['DATABASE_URL']
    return URL.create(
        'postgresql+psycopg',
        username=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD'],
        host=os.environ.get('POSTGRES_HOST', 'db'),
        port=int(os.environ.get('POSTGRES_PORT', '5432')),
        database=os.environ['POSTGRES_DB'],
    )


def init_database(app):
    engine = create_engine(app.config.get('DATABASE_URL') or database_url(),
                           pool_pre_ping=True, pool_size=5, max_overflow=5,
                           connect_args={'connect_timeout': 5})
    app.extensions['postgres_engine'] = engine
    app.extensions['postgres_sessions'] = sessionmaker(bind=engine, expire_on_commit=False)

    @app.teardown_appcontext
    def close_database(error=None):
        db = g.pop('db', None)
        if db is not None:
            db.close()


def get_db():
    if 'db' not in g:
        g.db = current_app.extensions['postgres_sessions']()
    return g.db
