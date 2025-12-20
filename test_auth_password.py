import pytest
from flask_jwt_extended import create_access_token

from app import create_app, db
from app.models.user import User, Role


@pytest.fixture
def app():
    app = create_app('testing')
    app.config['JWT_SECRET_KEY'] = 'testing_secret'
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    with app.app_context():
        user = User(
            identification=123456789,
            fullname='Test User',
            email='user@example.com',
            phone='3000000000',
            role=Role.Aprendiz,
            status=True,
        )
        user.set_password('OldPass123!')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def auth_headers(app, user):
    with app.app_context():
        access_token = create_access_token(identity=str(user.id))
    return {'Authorization': f'Bearer {access_token}'}


def test_change_password_success(client, app, user, auth_headers):
    payload = {'current_password': 'OldPass123!', 'new_password': 'NewPass123!'}
    response = client.post('/api/v1/auth/change-password', json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['should_clear_auth'] is True

    with app.app_context():
        refreshed = User.get_by_id(user.id)
        assert refreshed.check_password('NewPass123!')
        assert not refreshed.check_password('OldPass123!')


def test_change_password_rejects_wrong_current(client, app, user, auth_headers):
    payload = {'current_password': 'WrongPass!', 'new_password': 'NewPass123!'}
    response = client.post('/api/v1/auth/change-password', json=payload, headers=auth_headers)

    assert response.status_code == 401
    data = response.get_json()
    assert data['success'] is False
    assert 'Contrasena actual incorrecta' in data['message']

    with app.app_context():
        refreshed = User.get_by_id(user.id)
        assert refreshed.check_password('OldPass123!')


def test_recover_and_reset_password_flow(client, app, user):
    recover_resp = client.post('/api/v1/auth/recover', json={'email': user.email})

    assert recover_resp.status_code == 200
    recover_data = recover_resp.get_json()
    assert recover_data['success'] is True
    reset_token = recover_data['data']['reset_token']
    assert reset_token

    reset_resp = client.post(
        '/api/v1/auth/reset-password',
        json={'reset_token': reset_token, 'new_password': 'BrandNew123!'},
    )

    assert reset_resp.status_code == 200
    reset_data = reset_resp.get_json()
    assert reset_data['success'] is True
    assert reset_data['data']['should_clear_auth'] is True

    with app.app_context():
        refreshed = User.get_by_id(user.id)
        assert refreshed.check_password('BrandNew123!')
