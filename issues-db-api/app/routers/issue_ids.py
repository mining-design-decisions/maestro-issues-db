from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.dependencies import manual_labels_collection, jira_repos_db
from app.exceptions import repo_not_found_exception, issue_not_found_exception

router = APIRouter(
    prefix='/issue-ids',
    tags=['issue-ids']
)
example_request = {
    "example": {
        "filter": {
            "$and": [
                {"tags": {"$eq": "tag1"}},
                {"$or": [
                    {"tags": {"$ne": "tag2"}},
                    {"tags": {"$eq": "tag3"}}
                ]}
            ]
        }
    }
}


class IssueIdsIn(BaseModel):
    filter: dict

    class Config:
        schema_extra = example_request


class IssueIdsOut(BaseModel):
    issue_ids: list[str]


class IssueIdOut(BaseModel):
    issue_id: str


@router.get('', response_model=IssueIdsOut)
def get_issue_ids(request: IssueIdsIn):
    """
    Returns the issue ids for which the issue tags match
    the provided filtering options. These filtering options are
    given in the body of the request.
    """
    issues = manual_labels_collection.find(
        request.filter,
        ['_id']
    )
    return IssueIdsOut(issue_ids=[issue['_id'] for issue in issues])


@router.get('/{repo_name}/{issue_key}', response_model=IssueIdOut)
def get_issue_id_from_key(repo_name: str, issue_key: str):
    if repo_name not in jira_repos_db.list_collection_names():
        raise repo_not_found_exception(repo_name)
    issue = jira_repos_db[repo_name].find_one({'key': issue_key})
    if issue is None:
        raise issue_not_found_exception(issue_key)
    return IssueIdOut(issue_id=f'{repo_name}-{issue["id"]}')
