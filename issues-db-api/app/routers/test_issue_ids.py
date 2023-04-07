from fastapi.testclient import TestClient

from app import app
from app.dependencies import manual_labels_collection

client = TestClient(app.app)


def restore_db():
    manual_labels_collection.delete_many({})


def setup_db():
    restore_db()
    manual_labels_collection.insert_one({
        '_id': 'Apache-01',
        'existence': False,
        'property': False,
        'executive': True,
        'tags': ['Tag-01']
    })
    manual_labels_collection.insert_one({
        '_id': 'Apache-02',
        'existence': False,
        'property': False,
        'executive': True,
        'tags': ['Tag-01', 'Tag-02']
    })


def test_issue_ids_endpoint():
    setup_db()

    # Test 2 matches
    response = client.post(
        '/issue-ids',
        json={
            'filter': {'tags': 'Tag-01'}
        }
    )
    assert response.status_code == 200
    assert response.json() == {'ids': ['Apache-01', 'Apache-02']}

    # Test 1 match
    response = client.post(
        '/issue-ids',
        json={
            'filter': {'tags': 'Tag-02'}
        }
    )
    assert response.status_code == 200
    assert response.json() == {'ids': ['Apache-02']}

    # Test no matches
    response = client.post(
        '/issue-ids',
        json={
            'filter': {'tags': 'Tag-03'}
        }
    )
    assert response.status_code == 200
    assert response.json() == {'ids': []}

    restore_db()
