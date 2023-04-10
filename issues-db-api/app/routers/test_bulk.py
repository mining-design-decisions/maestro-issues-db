from .test_util import client
from .test_util import setup_users_db, restore_dbs, get_auth_header, auth_test_post
from app.dependencies import manual_labels_collection, tags_collection


def setup_db():
    manual_labels_collection.insert_one({
        '_id': 'Apache-01',
        'existence': False,
        'property': False,
        'executive': True,
        'tags': []
    })
    tags_collection.insert_one({
        '_id': 'tag',
        'description': 'text',
        'type': 'manual-tag'
    })


def test_add_tags_in_bulk():
    restore_dbs()
    setup_users_db()
    setup_db()

    auth_test_post('/bulk/add-tags')
    headers = get_auth_header()

    # Add tags
    payload = {
        'data': [{
            'issue_id': 'Apache-01',
            'tags': ['tag']
        }]
    }
    assert client.post('/bulk/add-tags', headers=headers, json=payload).status_code == 200
    assert manual_labels_collection.find_one({'_id': 'Apache-01'}, ['tags'])['tags'] == ['tag']

    # Insert existing tag
    assert client.post('/bulk/add-tags', headers=headers, json=payload).status_code == 200
    assert manual_labels_collection.find_one({'_id': 'Apache-01'}, ['tags'])['tags'] == ['tag']

    # Insert illegal tag
    payload = {
        'data': [{
            'issue_id': 'Apache-01',
            'tags': ['illegal-tag']
        }]
    }
    assert client.post('/bulk/add-tags', headers=headers, json=payload).status_code == 404
    assert manual_labels_collection.find_one({'_id': 'Apache-01'}, ['tags'])['tags'] == ['tag']

    # Test non-existing issue
    payload = {
        'data': [{
            'issue_id': 'Apache-02',
            'tags': ['tag']
        }]
    }
    assert client.post('/bulk/add-tags', headers=headers, json=payload).status_code == 404
    assert manual_labels_collection.find_one({'_id': 'Apache-01'}, ['tags'])['tags'] == ['tag']

    restore_dbs()
