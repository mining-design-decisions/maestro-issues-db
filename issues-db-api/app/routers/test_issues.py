from fastapi.testclient import TestClient

from app import app
from app.dependencies import manual_labels_collection, users_collection
from app.routers.authentication import get_password_hash

client = TestClient(app.app)


def restore_db():
    manual_labels_collection.delete_many({})
    users_collection.delete_many({})


def setup_db():
    restore_db()
    manual_labels_collection.insert_one({
        '_id': 'Apache-01',
        'existence': False,
        'property': False,
        'executive': True,
        'tags': ['has-label']
    })

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


def test_issues_endpoints():
    setup_db()
    token = get_token()

    # Test mark review
    response = client.post(
        '/issues/Apache-01/mark-review'
    )
    # Not authenticated
    assert response.status_code == 401

    response = client.post(
        '/issues/Apache-01/mark-review',
        headers={'Authorization': f'bearer {token}'}
    )
    assert response.status_code == 200

    # Make sure the tag was updated
    response = client.post(
        '/issue-ids',
        json={'filter': {'tags': 'needs-review'}}
    )
    assert response.json() == {'ids': ['Apache-01']}

    # Test non-existing issue
    response = client.post(
        '/issues/Apache-02/mark-review',
        headers={'Authorization': f'bearer {token}'}
    )
    assert response.status_code == 404

    # Test mark training
    response = client.post(
        '/issues/Apache-01/finish-review'
    )
    # Not authenticated
    assert response.status_code == 401

    response = client.post(
        '/issues/Apache-01/finish-review',
        headers={'Authorization': f'bearer {token}'}
    )
    assert response.status_code == 200

    # Make sure the tag was updated
    response = client.post(
        '/issue-ids',
        json={'filter': {'tags': 'has-label'}}
    )
    assert response.json() == {'ids': ['Apache-01']}

    # Test non-existing issue
    response = client.post(
        '/issues/Apache-02/finish-review',
        headers={'Authorization': f'bearer {token}'}
    )
    assert response.status_code == 404

    restore_db()
