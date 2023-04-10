from fastapi.testclient import TestClient

from app import app
from app.dependencies import users_collection, manual_labels_collection, model_collection, jira_repos_db,\
    issue_links_collection, projects_collection, tags_collection, mining_add_db, embeddings_collection
from .authentication import get_password_hash

client = TestClient(app.app)


def setup_users_db():
    users_collection.insert_one({
        '_id': 'test',
        'hashed_password': get_password_hash('test')
    })
    users_collection.insert_one({
        '_id': 'other-user',
        'hashed_password': get_password_hash('other-user')
    })


def restore_dbs():
    users_collection.delete_many({})
    manual_labels_collection.delete_many({})
    model_collection.delete_many({})
    jira_repos_db['Apache'].delete_many({})
    issue_links_collection.delete_many({})
    projects_collection.delete_many({})
    tags_collection.delete_many({})
    mining_add_db['fs_file'].drop()
    mining_add_db['fs_chunks'].drop()
    embeddings_collection.drop()


def get_auth_header():
    response = client.post(
        '/token',
        files={
            'username': (None, 'test'),
            'password': (None, 'test')
        }
    )
    return {'Authorization': f'bearer {response.json()["access_token"]}'}


def get_auth_header_other_user():
    response = client.post(
        '/token',
        files={
            'username': (None, 'other-user'),
            'password': (None, 'other-user')
        }
    )
    return {'Authorization': f'bearer {response.json()["access_token"]}'}


def auth_test_post(endpoint: str, payload=None):
    response = client.post(endpoint, json=payload)
    assert response.status_code == 401


def auth_test_patch(endpoint: str, payload=None):
    response = client.patch(endpoint, json=payload)
    assert response.status_code == 401


def auth_test_delete(endpoint: str):
    response = client.delete(endpoint)
    assert response.status_code == 401
