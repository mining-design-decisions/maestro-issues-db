from .test_util import client
from app.dependencies import manual_labels_collection
from .test_util import setup_users_db, restore_dbs, get_auth_header, auth_test_post, auth_test_delete
from .models import get_predictions, GetPredictionsIn
from bson import ObjectId
import datetime
import io


def auth_tests():
    test_id = str(ObjectId())
    auth_test_post('/models')
    auth_test_post(f'/models/{test_id}')
    auth_test_delete(f'/models/{test_id}')
    auth_test_post(f'/models/{test_id}/versions')
    auth_test_delete(f'/models/{test_id}/versions/{test_id}')
    auth_test_post(f'/models/{test_id}/versions/{test_id}/predictions')
    auth_test_delete(f'/models/{test_id}/versions/{test_id}/predictions')
    auth_test_post(f'/models/{test_id}/performances')
    auth_test_delete(f'/models/{test_id}/performances/{test_id}')


def model_tests():
    # Create models
    headers = get_auth_header()
    response = client.post('/models', headers=headers, json={
        'name': None,
        'config': {'key': 'value'}
    })
    assert response.status_code == 200
    model_id1 = response.json()['id']
    response = client.post('/models', headers=headers, json={
        'name': 'model-name',
        'config': {'key': 'value'}
    })
    assert response.status_code == 200
    model_id2 = response.json()['id']

    # Get models
    assert client.get('/models').json() == {
        'models': [
            {
                'id': model_id1,
                'name': ''
            },
            {
                'id': model_id2,
                'name': 'model-name'
            }
        ]
    }

    # Model not found
    assert client.get(f'/models/{ObjectId()}').status_code == 404

    # Update model
    response = client.post(f'/models/{model_id1}', headers=headers, json={
        'name': 'new-name',
        'config': {'new-key': 'new-value'}
    })
    assert response.status_code == 200

    # Model not found
    assert client.post(f'/models/{ObjectId()}', headers=headers, json={}).status_code == 404

    # Get model
    assert client.get(f'/models/{model_id1}').json() == {
        'id': model_id1,
        'name': 'new-name',
        'config': {'new-key': 'new-value'}
    }

    # Add version
    time = datetime.datetime.utcnow().isoformat()
    file = io.BytesIO(bytes('mock data', 'utf-8'))
    response = client.post(f'/models/{model_id1}/versions', headers=headers, files={
        'time': (None, time),
        'file': ('filename', file)
    })
    assert response.status_code == 200
    version_id = response.json()['version-id']

    # Get version
    response = client.get(f'/models/{model_id1}/versions/{version_id}')
    assert response.status_code == 200
    assert bytes('mock data', 'utf-8') == response.content

    test_id = str(ObjectId())
    response = client.get(f'/models/{model_id1}/versions/{test_id}')
    assert response.status_code == 404

    # Get model versions
    response = client.get(f'/models/{model_id1}/versions')
    assert response.status_code == 200
    assert response.json() == {
        'versions': [
            {
                'id': version_id,
                'time': time
            }
        ]
    }

    # Delete version
    response = client.delete(f'/models/{model_id1}/versions/{version_id}', headers=headers)
    assert response.status_code == 200

    response = client.delete(f'/models/{model_id1}/versions/{test_id}', headers=headers)
    assert response.status_code == 404

    # Add predictions
    manual_labels_collection.insert_one({
        '_id': 'Apache-01',
        'existence': False,
        'property': False,
        'executive': True,
        'tags': ['has-label']
    })
    payload = {
        'predictions': {
            'Apache-01': {
                'existence': {
                    'confidence': 0.42,
                    'prediction': False
                }
            }
        }
    }
    response = client.post(f'/models/{model_id1}/versions/{version_id}/predictions', headers=headers, json=payload)
    assert response.status_code == 200
    assert len(manual_labels_collection.index_information()) == 2

    response = client.post(f'/models/{model_id1}/versions/{test_id}/predictions', headers=headers, json=payload)
    assert response.status_code == 404

    # Get predictions
    response = get_predictions(model_id1, version_id, GetPredictionsIn(ids=None))
    assert response == payload

    response = get_predictions(model_id1, version_id, GetPredictionsIn(ids=['Apache-01']))
    assert response == payload

    response = get_predictions(model_id1, version_id, GetPredictionsIn(ids=['Apache-01', 'Apache-02']))
    payload['predictions']['Apache-02'] = None
    assert response == payload

    response = client.delete(f'/models/{model_id1}/versions/{version_id}/predictions', headers=headers)
    assert response.status_code == 200
    assert len(manual_labels_collection.index_information()) == 1

    response = client.delete(f'/models/{model_id1}/versions/{ObjectId()}/predictions', headers=headers)
    assert response.status_code == 404

    payload = {
        'predictions': {
            'Apache-02': {
                'existence': {
                    'confidence': 0.42,
                    'prediction': False
                }
            }
        }
    }
    response = client.post(f'/models/{model_id1}/versions/{version_id}/predictions', headers=headers, json=payload)
    assert response.status_code == 404

    response = client.post(f'/models/{model_id1}/performances', headers=headers, json={
        'time': time,
        'performance': [{'key': 'value'}]
    })
    assert response.status_code == 200

    response = client.get(f'/models/{model_id1}/performances')
    assert response.json() == {'performances': [time]}

    response = client.get(f'/models/{model_id1}/performances/{time}')
    assert response.json() == {time: [{'key': 'value'}]}

    response = client.delete(f'/models/{model_id1}/performances/{time}', headers=headers)
    assert response.status_code == 200

    response = client.get(f'/models/{model_id1}/performances')
    assert response.json() == {'performances': []}

    response = client.delete(f'/models/{test_id}/performances/{time}', headers=headers)
    assert response.status_code == 404

    response = client.delete(f'/models/{model_id1}/performances/{test_id}', headers=headers)
    assert response.status_code == 404

    # Delete model
    client.post(f'/models/{model_id1}/versions', headers=headers, files={
        'time': (None, time),
        'file': ('filename', file)
    })

    response = client.delete(f'/models/{model_id1}', headers=headers)
    assert response.status_code == 200

    response = client.delete(f'/models/{test_id}', headers=headers)
    assert response.status_code == 404


def test_models():
    restore_dbs()
    setup_users_db()

    auth_tests()
    model_tests()

    restore_dbs()
