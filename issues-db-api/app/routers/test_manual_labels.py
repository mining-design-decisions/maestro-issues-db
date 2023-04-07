from .test_util import client
from app.dependencies import manual_labels_collection, users_collection
from .test_util import setup_users_db, restore_dbs, get_auth_header, auth_test_post, auth_test_patch, auth_test_delete
from bson import ObjectId


def setup_db():
    manual_labels_collection.insert_one({
        '_id': 'Apache-01',
        'existence': False,
        'property': False,
        'executive': True,
        'tags': ['has-label']
    })


def label():
    # Update label
    headers = get_auth_header()
    auth_test_post('/manual-labels/Apache-01')
    response = client.post(
        '/manual-labels/Apache-01',
        headers=headers,
        json={'existence': True, 'property': True, 'executive': False}
    )
    assert response.status_code == 200

    # Make sure author tag is added
    response = client.post(
        '/issue-ids',
        json={'filter': {'tags': 'test'}}
    )
    assert response.json() == {'ids': ['Apache-01']}

    response = client.post(
        '/manual-labels/Apache-02',
        headers=headers,
        json={'existence': True, 'property': True, 'executive': False}
    )
    assert response.status_code == 404

    # Get label
    response = client.post(
        '/manual-labels',
        json={'ids': ['Apache-01']}
    )
    assert response.status_code == 200
    assert response.json() == {
        'labels': {
            'Apache-01': {
                'existence': True,
                'property': True,
                'executive': False
            }
        }
    }

    response = client.post(
        '/manual-labels',
        json={'ids': ['Apache-02']}
    )
    assert response.status_code == 404


def comment():
    # No comments for the issue
    response = client.get('/manual-labels/Apache-01/comments')
    assert response.json() == {'comments': {}}

    # Non-existing issue
    response = client.get('/manual-labels/Apache-02/comments')
    assert response.status_code == 404

    auth_test_post('manual-labels/Apache-01/comments')

    # Add comment
    headers = get_auth_header()
    response = client.post(
        'manual-labels/Apache-01/comments',
        headers=headers,
        json={'comment': 'Test comment'}
    )
    assert response.status_code == 200
    comment_id = response.json()['id']

    # Make sure comment is inserted
    response = client.get('manual-labels/Apache-01/comments')
    assert response.json() == {
        'comments': {
            comment_id: {
                'author': 'test',
                'comment': 'Test comment'
            }
        }
    }

    # Make sure author tag is added
    response = client.post(
        '/issue-ids',
        json={'filter': {'tags': 'test'}}
    )
    assert response.json() == {'ids': ['Apache-01']}

    # Non-existing issue
    response = client.post(
        'manual-labels/Apache-02/comments',
        headers=headers,
        json={'comment': 'Test comment'}
    )
    assert response.status_code == 404

    # Test updating a comment
    auth_test_patch(f'/manual-labels/Apache-01/comments/{comment_id}')

    response = client.patch(
        f'/manual-labels/Apache-01/comments/{comment_id}',
        headers=headers,
        json={'comment': 'Updated comment'}
    )
    assert response.status_code == 200

    # Make sure comment is updated
    response = client.get('manual-labels/Apache-01/comments')
    assert response.json() == {
        'comments': {
            comment_id: {
                'author': 'test',
                'comment': 'Updated comment'
            }
        }
    }

    # Non-existing issue
    response = client.patch(
        f'manual-labels/Apache-02/comments/{comment_id}',
        headers=headers,
        json={'comment': 'Updated comment'}
    )
    assert response.status_code == 404

    # Non-existing comment
    random_id = ObjectId()
    response = client.patch(
        f'manual-labels/Apache-02/comments/{random_id}',
        headers=headers,
        json={'comment': 'Updated comment'}
    )
    assert response.status_code == 404

    # Test deleting a comment
    auth_test_delete(f'/manual-labels/Apache-01/comments/{comment_id}')
    response = client.delete(
        f'/manual-labels/Apache-01/comments/{comment_id}',
        headers=headers
    )
    assert response.status_code == 200

    # Non-existing comment
    response = client.delete(
        f'/manual-labels/Apache-01/comments/{comment_id}',
        headers=headers
    )
    assert response.status_code == 404

    # Non-existing issue
    response = client.delete(
        f'/manual-labels/Apache-02/comments/{comment_id}',
        headers=headers
    )
    assert response.status_code == 404


def test_manual_labels_endpoints():
    restore_dbs()
    setup_users_db()
    setup_db()
    label()

    restore_dbs()
    setup_users_db()
    setup_db()
    comment()

    restore_dbs()
