import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from backend.app import create_app


@pytest.fixture
def app():
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        pytest.skip('Use compose.test.yaml or configure TEST_DATABASE_URL ending in _test.')
    if not make_url(url).database.endswith('_test'):
        pytest.fail('Refusing to clean a database whose name does not end in _test.')
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret-with-at-least-32-characters',
                      'DATABASE_URL': url, 'AUTH_LIMIT': 100})
    engine = app.extensions['postgres_engine']
    with engine.begin() as connection:
        connection.execute(text('TRUNCATE usuarios, login_limits RESTART IDENTITY CASCADE'))
    yield app
    engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()
