from bson import ObjectId
import io

from app.dependencies import embeddings_collection, fs
from .test_util import client, restore_dbs, setup_users_db, get_auth_header, auth_test_post, auth_test_delete


def test_get_all_embeddings():
    restore_dbs()

    # Init db
    embedding_id = ObjectId()
    config = {'key': 'value'}
    embeddings_collection.insert_one({
        '_id': embedding_id,
        'config': config,
        'file_id': None
    })

    # Get embeddings
    assert client.get('/embeddings').json() == {'embeddings': [{'embedding_id': str(embedding_id), 'config': config}]}

    restore_dbs()


def test_create_embedding():
    restore_dbs()
    setup_users_db()

    auth_test_post('/embeddings')
    headers = get_auth_header()

    # Create embedding
    config = {'key': 'value'}
    response = client.post('/embeddings', headers=headers, json={'config': config})
    assert response.status_code == 200
    assert embeddings_collection.find_one({'_id': ObjectId(response.json()['embedding_id'])}) == {
        '_id': ObjectId(response.json()['embedding_id']),
        'config': config,
        'file_id': None
    }

    restore_dbs()


def test_update_embedding():
    restore_dbs()
    setup_users_db()

    embedding_id = ObjectId()
    auth_test_post(f'/embeddings/{embedding_id}')
    headers = get_auth_header()

    # Init db
    embeddings_collection.insert_one({
        '_id': embedding_id,
        'config': {'key': 'value'},
        'file_id': None
    })

    # Update the embedding
    new_config = {'new-key': 'new-value'}
    assert client.post(f'/embeddings/{embedding_id}', headers=headers, json={'config': new_config}).status_code == 200
    assert embeddings_collection.find_one({'_id': ObjectId(embedding_id)}) == {
        '_id': ObjectId(embedding_id),
        'config': new_config,
        'file_id': None
    }

    # Non-existing embedding
    assert client.post(f'/embeddings/{ObjectId()}', headers=headers, json={'config': new_config}).status_code == 404

    # Illegal id
    assert client.post('/embeddings/illegal-id', headers=headers, json={'config': new_config}).status_code == 422

    restore_dbs()


def test_delete_embedding():
    restore_dbs()
    setup_users_db()

    embedding_id = ObjectId()
    auth_test_delete(f'/embeddings/{embedding_id}')
    headers = get_auth_header()

    # Init db
    file = io.BytesIO(bytes('mock data', 'utf-8'))
    file_id = fs.put(file, filename='filename.txt')
    embeddings_collection.insert_one({
        '_id': embedding_id,
        'config': {'key': 'value'},
        'file_id': file_id
    })

    # Delete embedding
    assert client.delete(f'/embeddings/{embedding_id}', headers=headers).status_code == 200
    assert embeddings_collection.find_one({'_id': embedding_id}) is None
    assert fs.exists(file_id) is False

    # Delete non-existing embedding
    assert client.delete(f'/embeddings/{embedding_id}', headers=headers).status_code == 404

    # Test illegal id
    assert client.delete('/embeddings/illegal-id', headers=headers).status_code == 422

    restore_dbs()


def test_upload_embedding_file():
    restore_dbs()
    setup_users_db()

    embedding_id = ObjectId()
    auth_test_post(f'/embeddings/{embedding_id}/file')
    headers = get_auth_header()

    # Init db
    embeddings_collection.insert_one({
        '_id': embedding_id,
        'config': {'key': 'value'},
        'file_id': None
    })

    # Upload file
    file = io.BytesIO(bytes('mock data', 'utf-8'))
    assert client.post(f'/embeddings/{embedding_id}/file', headers=headers, files={
        'file': ('filename', file)
    }).status_code == 200
    file_id = ObjectId(embeddings_collection.find_one({'_id': embedding_id})['file_id'])
    assert fs.get(file_id).read() == bytes('mock data', 'utf-8')

    # Upload new file to test overwrite
    new_file = io.BytesIO(bytes('new mock data', 'utf-8'))
    assert client.post(f'/embeddings/{embedding_id}/file', headers=headers, files={
        'file': ('filename', new_file)
    }).status_code == 200
    new_file_id = ObjectId(embeddings_collection.find_one({'_id': embedding_id})['file_id'])
    assert fs.get(new_file_id).read() == bytes('new mock data', 'utf-8')

    # Make sure the previous one is deleted
    assert fs.exists(file_id) is False

    restore_dbs()


def test_get_embedding_file():
    restore_dbs()

    # Init db
    embedding_id = ObjectId()
    file = io.BytesIO(bytes('mock data', 'utf-8'))
    file_id = fs.put(file, filename='filename.txt')
    embeddings_collection.insert_one({
        '_id': embedding_id,
        'config': {'key': 'value'},
        'file_id': file_id
    })

    # Get embedding
    assert client.get(f'/embeddings/{embedding_id}/file').content == bytes('mock data', 'utf-8')

    # Get non-existing embedding
    assert client.get(f'/embeddings/{ObjectId()}/file').status_code == 404

    # Get non-existing embedding file
    embeddings_collection.update_one({'_id': embedding_id}, {'$set': {'file_id': None}})
    assert client.get(f'/embeddings/{embedding_id}/file').status_code == 404

    restore_dbs()


def test_delete_embedding_file():
    restore_dbs()
    setup_users_db()

    embedding_id = ObjectId()
    auth_test_delete(f'/embeddings/{embedding_id}/file')
    headers = get_auth_header()

    # Init db
    embedding_id = ObjectId()
    file = io.BytesIO(bytes('mock data', 'utf-8'))
    file_id = fs.put(file, filename='filename.txt')
    embeddings_collection.insert_one({
        '_id': embedding_id,
        'config': {'key': 'value'},
        'file_id': file_id
    })

    # Delete file
    assert client.delete(f'/embeddings/{embedding_id}/file', headers=headers).status_code == 200
    assert fs.exists(file_id) is False

    # Delete non-existing file
    assert client.delete(f'/embeddings/{embedding_id}/file', headers=headers).status_code == 404

    restore_dbs()
