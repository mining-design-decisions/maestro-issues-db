from .test_util import client
from .test_util import setup_users_db, restore_dbs, get_auth_header, auth_test_post
from app.dependencies import users_collection


def test_authentication():
    setup_users_db()

    # Get token
    response = client.post('/token', files={'username': (None, 'test2'), 'password': (None, 'test2')})
    assert response.status_code == 401
    response = client.post('/token', files={'username': (None, 'test'), 'password': (None, 'test2')})
    assert response.status_code == 401
    response = client.post('/token', files={'username': (None, 'test'), 'password': (None, 'test')})
    assert response.status_code == 200

    # Create account
    auth_test_post('/create-account')
    headers = {'Authorization': f'bearer {response.json()["access_token"]}'}
    payload = {'username': 'test2', 'password': 'test2'}
    assert client.post('/create-account', headers=headers, json=payload).status_code == 200
    assert users_collection.find_one({'_id': 'test2'}) is not None
    assert client.post('/create-account', headers=headers, json=payload).status_code == 409

    # Get token for new account
    response = client.post('/token', files={'username': (None, 'test2'), 'password': (None, 'test2')})
    assert response.status_code == 200

    restore_dbs()
