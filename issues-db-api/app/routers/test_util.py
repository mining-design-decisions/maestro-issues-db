from app import app
from app.dependencies import (
    users_collection,
    issue_labels_collection,
    models_collection,
    jira_repos_db,
    issue_links_collection,
    projects_collection,
    tags_collection,
    mining_add_db,
    embeddings_collection,
    mongo_client,
)
from app.schemas import (
    issue_labels_collection_schema,
    issue_links_collection_schema,
    tags_collection_schema,
    projects_collection_schema,
    dl_models_collection_schema,
    embeddings_collection_schema,
    users_collection_schema,
)
from fastapi.testclient import TestClient

from .authentication import get_password_hash

client = TestClient(app.app)


def setup_users_db():
    users_collection.insert_one(
        {"_id": "test", "hashed_password": get_password_hash("test")}
    )
    users_collection.insert_one(
        {"_id": "other-user", "hashed_password": get_password_hash("other-user")}
    )


def restore_dbs():
    users_collection.drop()
    issue_labels_collection.drop()
    models_collection.drop()
    jira_repos_db["Apache"].drop()
    issue_links_collection.drop()
    projects_collection.drop()
    tags_collection.drop()
    mining_add_db["fs_file"].drop()
    mining_add_db["fs_chunks"].drop()
    embeddings_collection.drop()

    mining_add_db.create_collection(
        "IssueLabels", validator=issue_labels_collection_schema
    )
    mining_add_db.create_collection(
        "IssueLinks", validator=issue_links_collection_schema
    )
    mining_add_db.create_collection("Tags", validator=tags_collection_schema)
    mining_add_db.create_collection("Projects", validator=projects_collection_schema)
    mining_add_db.create_collection("DLModels", validator=dl_models_collection_schema)
    mining_add_db.create_collection(
        "DLEmbeddings", validator=embeddings_collection_schema
    )
    mongo_client["Users"].create_collection("Users", validator=users_collection_schema)


def get_auth_header():
    response = client.post(
        "/token", files={"username": (None, "test"), "password": (None, "test")}
    )
    return {"Authorization": f'bearer {response.json()["access_token"]}'}


def get_auth_header_other_user():
    response = client.post(
        "/token",
        files={"username": (None, "other-user"), "password": (None, "other-user")},
    )
    return {"Authorization": f'bearer {response.json()["access_token"]}'}


def auth_test_post(endpoint: str, payload=None):
    response = client.post(endpoint, json=payload)
    assert response.status_code == 401


def auth_test_patch(endpoint: str, payload=None):
    response = client.patch(endpoint, json=payload)
    assert response.status_code == 401


def auth_test_put(endpoint: str, payload=None):
    response = client.put(endpoint, json=payload)
    assert response.status_code == 401


def auth_test_delete(endpoint: str):
    response = client.delete(endpoint)
    assert response.status_code == 401
