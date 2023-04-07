from fastapi.testclient import TestClient
from bson import ObjectId
import io

from app import app
from app.dependencies import users_collection
from app.routers.authentication import get_password_hash

client = TestClient(app.app)


def restore_db():
    users_collection.delete_many({})


def setup_db():
    restore_db()
    users_collection.insert_one({
        '_id': 'test',
        'hashed_password': get_password_hash('test')
    })


def get_token():
    response = client.post(
        '/token',
        files={
            'username': (None, 'test'),
            'password': (None, 'test')
        }
    )
    return response.json()["access_token"]


def create_embedding(token: str):
    config = {'key': 'value'}

    # Test creating an embedding
    response = client.post(
        '/embeddings',
        json={'config': config}
    )
    # Not authenticated
    assert response.status_code == 401

    response = client.post(
        '/embeddings',
        headers={'Authorization': f'bearer {token}'},
        json={'config': config}
    )
    # Authenticated
    assert response.status_code == 200
    embedding_id = response.json()['embedding-id']

    # Get embeddings
    response = client.get('/embeddings')
    assert response.status_code == 200
    # Make sure the embedding was inserted
    assert response.json() == {embedding_id: config}
    return embedding_id


def update_embedding(embedding_id: str, token: str):
    new_config = {'new_key': 'new_value'}
    # Test authentication
    response = client.post(
        f'/embeddings/{embedding_id}',
        json={'config': new_config}
    )
    assert response.status_code == 401

    response = client.post(
        f'/embeddings/{embedding_id}',
        headers={'Authorization': f'bearer {token}'},
        json={'config': new_config}
    )
    assert response.status_code == 200

    # Make sure the config was updated
    response = client.get('/embeddings')
    assert response.json()[embedding_id] == new_config

    # Restore original config
    response = client.post(
        f'/embeddings/{embedding_id}',
        headers={'Authorization': f'bearer {token}'},
        json={'config': {'key': 'value'}}
    )
    assert response.status_code == 200

    # Test updating with illegal ObjectId
    response = client.post(
        f'/embeddings/non-existing-id',
        headers={'Authorization': f'bearer {token}'},
        json={'config': {'key': 'value'}}
    )
    assert response.status_code == 422

    # Test updating non-existing embedding
    new_id = ObjectId()
    response = client.post(
        f'/embeddings/{new_id}',
        headers={'Authorization': f'bearer {token}'},
        json={'config': {'key': 'value'}}
    )
    assert response.status_code == 404


def upload_file(embedding_id: str, token: str):
    file = io.BytesIO(bytes('mock data', 'utf-8'))
    response = client.post(
        f'/embeddings/{embedding_id}/file',
        files={
            'file': ('filename', file)
        }
    )
    # Not authenticated
    assert response.status_code == 401

    response = client.post(
        f'/embeddings/{embedding_id}/file',
        headers={'Authorization': f'bearer {token}'},
        files={
            'file': ('filename', file)
        }
    )
    assert response.status_code == 200

    response = client.get(
        f'/embeddings/{embedding_id}/file'
    )
    assert response.status_code == 200
    assert bytes('mock data', 'utf-8') == response.content

    # Upload new file to test overwrite
    file = io.BytesIO(bytes('mock data 2', 'utf-8'))
    response = client.post(
        f'/embeddings/{embedding_id}/file',
        headers={'Authorization': f'bearer {token}'},
        files={
            'file': ('filename', file)
        }
    )
    assert response.status_code == 200

    response = client.get(
        f'/embeddings/{embedding_id}/file'
    )
    assert response.status_code == 200
    assert bytes('mock data 2', 'utf-8') == response.content


def delete_file(embedding_id: str, token: str):
    # Make sure the file exists
    response = client.get(
        f'/embeddings/{embedding_id}/file'
    )
    assert response.status_code == 200

    # Test file deletion
    response = client.delete(
        f'/embeddings/{embedding_id}/file'
    )
    # Not authenticated
    assert response.status_code == 401

    response = client.delete(
        f'/embeddings/{embedding_id}/file',
        headers={'Authorization': f'bearer {token}'}
    )
    assert response.status_code == 200

    # Make sure the file is deleted
    response = client.get(
        f'/embeddings/{embedding_id}/file'
    )
    assert response.status_code == 404

    # Cannot delete a second time
    response = client.delete(
        f'/embeddings/{embedding_id}/file',
        headers={'Authorization': f'bearer {token}'}
    )
    assert response.status_code == 404


def delete_embedding(embedding_id: str, token: str):
    # Make sure file exists and will be deleted
    file = io.BytesIO(bytes('mock data', 'utf-8'))
    response = client.post(
        f'/embeddings/{embedding_id}/file',
        headers={'Authorization': f'bearer {token}'},
        files={
            'file': ('filename', file)
        }
    )
    assert response.status_code == 200

    # Delete embedding
    response = client.delete(
        f'/embeddings/{embedding_id}'
    )
    # Not authenticated
    assert response.status_code == 401

    response = client.delete(
        f'/embeddings/{embedding_id}',
        headers={'Authorization': f'bearer {token}'}
    )
    # Authenticated
    assert response.status_code == 200

    # Get embeddings
    response = client.get('/embeddings')
    assert response.status_code == 200
    # Make sure embedding is deleted
    assert response.json() == {}

    # Try to delete with illegal id
    response = client.delete(
        f'/embeddings/non-existing-id',
        headers={'Authorization': f'bearer {token}'}
    )
    assert response.status_code == 422

    # Try to delete non exsting id
    response = client.delete(
        f'/embeddings/{embedding_id}',
        headers={'Authorization': f'bearer {token}'}
    )
    assert response.status_code == 404


def test_embeddings_endpoints():
    setup_db()
    token = get_token()

    embedding_id = create_embedding(token)
    update_embedding(embedding_id, token)
    upload_file(embedding_id, token)
    delete_file(embedding_id, token)
    delete_embedding(embedding_id, token)

    restore_db()
