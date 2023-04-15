from .test_util import client
from app.dependencies import issue_labels_collection, models_collection, fs
from .test_util import setup_users_db, restore_dbs, get_auth_header, auth_test_post, auth_test_delete
from .models import get_predictions, GetPredictionsIn, GetPredictionsOut
from bson import ObjectId
import datetime
import io


def setup_db():
    time = datetime.datetime.utcnow().isoformat()
    version_id = fs.put(io.BytesIO(bytes('mock data', 'utf-8')), filename='filename')
    model_id = ObjectId()
    models_collection.insert_one({
        '_id': model_id,
        'name': 'model_name',
        'config': {'key': 'value'},
        'versions': [{'id': version_id, 'time': time.replace('.', '_')}],
        'performances': {
            time.replace('.', '_'): {'key': 'value'}
        }
    })

    issue_labels_collection.insert_one({
        '_id': 'Apache-01',
        'predictions': {
            f'{model_id}-{version_id}': {
                'existence': {
                    'confidence': 0.42,
                    'prediction': False
                }
            }
        }
    })
    issue_labels_collection.create_index(f'predictions.{model_id}-{version_id}.existence.confidence')

    return model_id, version_id, time


def test_get_all_models():
    restore_dbs()
    model_id, version_id, time = setup_db()

    assert client.get('/models').json() == {'models': [{
        'model_id': str(model_id),
        'model_name': 'model_name'
    }]}

    restore_dbs()


def test_create_model():
    restore_dbs()
    setup_users_db()

    auth_test_post('/models')
    headers = get_auth_header()

    # Create model with no name
    payload = {'model_name': None, 'model_config': {'key': 'value'}}
    model_id = client.post('/models', headers=headers, json=payload).json()['model_id']
    assert models_collection.find_one({'_id': ObjectId(model_id)}) == {
        '_id': ObjectId(model_id),
        'name': '',
        'config': {'key': 'value'},
        'versions': [],
        'performances': {}
    }

    # Create model with name
    payload = {'model_name': 'model_name', 'model_config': {'key': 'value'}}
    model_id = client.post('/models', headers=headers, json=payload).json()['model_id']
    assert models_collection.find_one({'_id': ObjectId(model_id)}) == {
        '_id': ObjectId(model_id),
        'name': 'model_name',
        'config': {'key': 'value'},
        'versions': [],
        'performances': {}
    }

    restore_dbs()


def test_get_model():
    restore_dbs()
    model_id, version_id, time = setup_db()

    # Get model
    assert client.get(f'/models/{model_id}').json() == {
        'model_id': str(model_id),
        'model_name': 'model_name',
        'model_config': {'key': 'value'}
    }

    # Non-existing model
    assert client.get(f'/models/{ObjectId()}').status_code == 404

    restore_dbs()


def test_update_model():
    restore_dbs()
    setup_users_db()
    model_id, version_id, time = setup_db()

    auth_test_post(f'/models/{model_id}')
    headers = get_auth_header()

    # Update model
    payload = {'model_name': 'new-name', 'model_config': {'new-key': 'new-value'}}
    assert client.post(f'/models/{model_id}', headers=headers, json=payload).status_code == 200
    assert models_collection.find_one({'_id': ObjectId(model_id)}, ['name', 'config']) == {
        '_id': ObjectId(model_id),
        'name': 'new-name',
        'config': {'new-key': 'new-value'}
    }

    # Non-existing model
    assert client.post(f'/models/{ObjectId()}', headers=headers, json=payload).status_code == 404

    restore_dbs()


def test_delete_model():
    restore_dbs()
    setup_users_db()
    model_id, version_id, time = setup_db()

    auth_test_delete(f'/models/{model_id}')
    headers = get_auth_header()

    # Delete model
    assert client.delete(f'/models/{model_id}', headers=headers).status_code == 200
    assert models_collection.find_one({'_id': model_id}) is None
    assert fs.exists(version_id) is False

    # Non-existing model
    assert client.delete(f'/models/{model_id}', headers=headers).status_code == 404

    restore_dbs()


def test_create_model_version():
    restore_dbs()
    setup_users_db()
    model_id, _, _ = setup_db()

    auth_test_post(f'/models/{model_id}/versions')
    headers = get_auth_header()

    # Create version
    time = datetime.datetime.utcnow().isoformat()
    files = {'time': (None, time), 'file': ('filename', io.BytesIO(bytes('mock data', 'utf-8')))}
    version_id = client.post(f'/models/{model_id}/versions', headers=headers, files=files).json()['version_id']
    assert models_collection.find_one({'_id': model_id})['versions'][1]['id'] == ObjectId(version_id)
    assert fs.get(ObjectId(version_id)).read() == bytes('mock data', 'utf-8')

    # Non-existing model
    assert client.post(f'/models/{ObjectId()}/versions', headers=headers, files=files).status_code == 404

    restore_dbs()


def test_get_model_versions():
    restore_dbs()
    model_id, version_id, time = setup_db()

    # Get version
    assert client.get(f'/models/{model_id}/versions').json() == {
        'versions': [{
            'version_id': str(version_id),
            'time': time.replace('_', '.')
        }]
    }

    restore_dbs()


def test_get_model_version():
    restore_dbs()
    model_id, version_id, time = setup_db()

    # Get version
    assert client.get(f'/models/{model_id}/versions/{version_id}').content == bytes('mock data', 'utf-8')

    # Non-existing version
    assert client.get(f'/models/{model_id}/versions/{ObjectId()}').status_code == 404

    restore_dbs()


def test_delete_model_version():
    restore_dbs()
    setup_users_db()
    model_id, version_id, time = setup_db()

    auth_test_delete(f'/models/{model_id}/versions/{version_id}')
    headers = get_auth_header()

    # Delete version
    assert client.delete(f'/models/{model_id}/versions/{version_id}', headers=headers).status_code == 200
    assert models_collection.find_one({'_id': model_id})['versions'] == []
    assert fs.exists(version_id) is False

    # Non-existing version
    assert client.delete(f'/models/{model_id}/versions/{ObjectId()}', headers=headers).status_code == 404

    restore_dbs()


def test_post_predictions():
    restore_dbs()
    setup_users_db()
    model_id, version_id, time = setup_db()

    auth_test_post(f'/models/{model_id}/versions/{version_id}/predictions')
    headers = get_auth_header()

    # Post predictions
    payload = {
        'predictions': {
            'Apache-01': {
                'property': {
                    'confidence': 0.42,
                    'prediction': False
                }
            }
        }
    }
    response = client.post(f'/models/{model_id}/versions/{version_id}/predictions', headers=headers, json=payload)
    assert response.status_code == 200
    assert issue_labels_collection.find_one({'_id': 'Apache-01'})['predictions'] == {
        f'{model_id}-{version_id}': {
            'property': {
                'confidence': 0.42,
                'prediction': False
            }
        }
    }
    assert len(issue_labels_collection.index_information()) == 3

    # Non-existing version
    response = client.post(f'/models/{model_id}/versions/{ObjectId()}/predictions', headers=headers, json=payload)
    assert response.status_code == 404

    # Non-existing issue
    payload = {
        'predictions': {
            'Non-existing-id': {
                'property': {
                    'confidence': 0.42,
                    'prediction': False
                }
            }
        }
    }
    response = client.post(f'/models/{model_id}/versions/{version_id}/predictions', headers=headers, json=payload)
    assert response.status_code == 404

    restore_dbs()


def test_get_predictions():
    restore_dbs()
    model_id, version_id, time = setup_db()

    # Get predictions
    desired_result = GetPredictionsOut(predictions={
        'Apache-01': {
            'existence': {
                'confidence': 0.42,
                'prediction': False
            }
        }
    })
    assert get_predictions(str(model_id), version_id, GetPredictionsIn(issue_ids=None)) == desired_result
    assert get_predictions(str(model_id), version_id, GetPredictionsIn(issue_ids=['Apache-01'])) == desired_result
    assert get_predictions(str(model_id), version_id, GetPredictionsIn(issue_ids=['Apache-02'])) == GetPredictionsOut(
        predictions={'Apache-02': None}
    )

    restore_dbs()


def test_delete_predictions():
    restore_dbs()
    setup_users_db()
    model_id, version_id, time = setup_db()

    auth_test_delete(f'/models/{model_id}/versions/{version_id}/predictions')
    headers = get_auth_header()

    # Delete version
    assert client.delete(f'/models/{model_id}/versions/{version_id}/predictions', headers=headers).status_code == 200
    assert issue_labels_collection.find_one({'_id': 'Apache-01'})['predictions'] == {}

    # Non-existing version
    assert client.delete(f'/models/{model_id}/versions/{ObjectId()}/predictions', headers=headers).status_code == 404

    restore_dbs()


def test_post_performance():
    restore_dbs()
    setup_users_db()
    model_id, version_id, _ = setup_db()

    auth_test_post(f'/models/{model_id}/performances')
    headers = get_auth_header()

    # Post performance
    time = datetime.datetime.utcnow().isoformat()
    payload = {'time': time, 'performance': [{'key': 'value'}]}
    assert client.post(f'/models/{model_id}/performances', headers=headers, json=payload).status_code == 200
    assert models_collection.find_one({'_id': model_id})['performances'][time.replace(".", "_")] == [{'key': 'value'}]

    # Non-existing model
    assert client.post(f'/models/{ObjectId()}/performances', headers=headers, json=payload).status_code == 404

    restore_dbs()


def test_get_performances():
    restore_dbs()
    model_id, version_id, time = setup_db()

    # Get performance
    desired_result = {'performances': [time]}
    assert client.get(f'/models/{model_id}/performances').json() == desired_result

    restore_dbs()


def test_get_performance():
    restore_dbs()
    model_id, version_id, time = setup_db()

    # Get performance
    desired_result = {'performance_time': time, 'performance': {'key': 'value'}}
    assert client.get(f'/models/{model_id}/performances/{time}').json() == desired_result

    restore_dbs()


def test_delete_performance():
    restore_dbs()
    setup_users_db()
    model_id, version_id, time = setup_db()

    auth_test_delete(f'/models/{model_id}/performances/{time}')
    headers = get_auth_header()

    # Delete version
    assert client.delete(f'/models/{model_id}/performances/{time}', headers=headers).status_code == 200
    assert models_collection.find_one({'_id': model_id})['performances'] == {}

    # Non-existing model
    assert client.delete(f'/models/{ObjectId()}/performances/{time}', headers=headers).status_code == 404

    # Non-existing performance
    assert client.delete(f'/models/{model_id}/performances/non-existing', headers=headers).status_code == 404

    restore_dbs()
