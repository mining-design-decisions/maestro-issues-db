from fastapi.testclient import TestClient

from app import app
from app.dependencies import jira_repos_db, issue_links_collection

client = TestClient(app.app)


def restore_db():
    jira_repos_db['Apache'].delete_many({})
    issue_links_collection.delete_many({})


def setup_db():
    restore_db()
    jira_repos_db['Apache'].insert_one({
        'id': '13211409',
        'key': 'YARN-9230',
        'fields': {
            'summary': 'Write a go hdfs driver for Docker Registry'
        }
    })
    issue_links_collection.insert_one({
        '_id': 'Apache',
        'link': 'https://issues.apache.org/jira'
    })


def test_issue_data_endpoint():
    setup_db()
    response = client.post(
        '/issue-data',
        json={
            'ids': ['Apache-13211409'],
            'attributes': ['key', 'link', 'summary']
        }
    )
    assert response.status_code == 200
    assert response.json() == {
        'data': {
            'Apache-13211409': {
                'key': 'YARN-9230',
                'link': 'https://issues.apache.org/jira/browse/YARN-9230',
                'summary': 'Write a go hdfs driver for Docker Registry'
            }
        }
    }

    # Test attribute not found
    response = client.post(
        '/issue-data',
        json={
            'ids': ['Apache-13211409'],
            'attributes': ['non-existing-attribute']
        }
    )
    assert response.status_code == 404

    # Test non-existing issue
    response = client.post(
        '/issue-data',
        json={
            'ids': ['Apache-0'],
            'attributes': ['key']
        }
    )
    assert response.status_code == 404

    # Test key is None
    jira_repos_db['Apache'].insert_one({
        'id': '13211410',
        'key': None,
        'fields': {
            'summary': None,
            'required_attr': None
        }
    })
    response = client.post(
        '/issue-data',
        json={
            'ids': ['Apache-13211410'],
            'attributes': ['key']
        }
    )
    assert response.status_code == 409

    # Test default value
    response = client.post(
        '/issue-data',
        json={
            'ids': ['Apache-13211410'],
            'attributes': ['summary']
        }
    )
    assert response.status_code == 200
    assert response.json() == {
        'data': {
            'Apache-13211410': {
                'summary': ''
            }
        }
    }

    # Test required attribute
    response = client.post(
        '/issue-data',
        json={
            'ids': ['Apache-13211410'],
            'attributes': ['required_attr']
        }
    )
    assert response.status_code == 409

    # Test duplicate issue exception
    jira_repos_db['Apache'].insert_one({
        'id': '13211409',
        'key': 'YARN-9230',
        'fields': {
            'summary': 'Write a go hdfs driver for Docker Registry'
        }
    })
    jira_repos_db['Apache'].insert_one({
        'id': '13211409',
        'key': 'YARN-9230',
        'fields': {
            'summary': 'Write a go hdfs driver for Docker Registry'
        }
    })
    response = client.post(
        '/issue-data',
        json={
            'ids': ['Apache-13211409'],
            'attributes': ['non-existing-attribute']
        }
    )
    assert response.status_code == 404

    restore_db()
