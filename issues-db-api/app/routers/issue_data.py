import typing
from fastapi import APIRouter
from pydantic import BaseModel
from app.dependencies import jira_repos_db

router = APIRouter()
example_request = {
    "example": {
        'keys': [
            'ISSUE-1',
            'ISSUE-2'
        ],
        'attributes': [
            'summary',
            'description'
        ]
    }
}


default_value = {
    'summary': '',
    'description': '',
    'labels': [],
    'components': [],
    'votes': 0,
    'watches': 0,
    'parent': False,
    'issuelinks': [],
    'attachments': [],
    'sub-tasks': []
}


class IssueDataIn(BaseModel):
    keys: list[str]
    attributes: list[str]

    class Config:
        schema_extra = example_request


class IssueDataOut(BaseModel):
    data: dict[str, dict[str, typing.Any]] = {}


@router.get('/issue-data')
def issue_data(request: IssueDataIn) -> IssueDataOut:
    """
    Returns issue data. The returned data is determined by the
    specified issue keys and the attributes that are requested.
    """
    issues = []
    for repo in jira_repos_db.list_collection_names():
        repo_issues = jira_repos_db[repo].find(
            {'key': {'$in': request.keys}},
            ['key'] + [f'fields.{attr}' for attr in request.attributes]
        )
        issues.extend(list(repo_issues))

    # Build and send response
    response = IssueDataOut()
    data = {}
    for issue in issues:
        attributes = {}
        for attr in request.attributes:
            if issue['fields'][attr] is not None:
                attributes[attr] = issue['fields'][attr]
            elif attr not in list(default_value.keys()):
                raise AttributeError(f'Attribute {attr} is required for issue {issue["key"]}')
            else:
                attributes[attr] = default_value[attr]
        data[issue['key']] = attributes
    response.data = data
    return response
