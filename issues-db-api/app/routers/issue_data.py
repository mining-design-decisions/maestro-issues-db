import typing
from fastapi import APIRouter
from pydantic import BaseModel
from app.dependencies import jira_repos_db

router = APIRouter(
    prefix='/issue-data',
    tags=['issue-data']
)
example_request = {
    "example": {
        'ids': [
            'ISSUE-ID-1',
            'ISSUE-ID-2'
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
    ids: list[str]
    attributes: list[str]

    class Config:
        schema_extra = example_request


class IssueDataOut(BaseModel):
    data: dict[str, dict[str, typing.Any]] = {}


@router.get('')
def issue_data(request: IssueDataIn) -> IssueDataOut:
    """
    Returns issue data. The returned data is determined by the
    specified issue ids and the attributes that are requested.
    """
    # Collect the ids belonging to each Jira repo
    ids = dict()
    for jira_name in jira_repos_db.list_collection_names():
        ids[jira_name] = []
    for issue_id in request.ids:
        split_id = issue_id.split('-')
        # First part is the jira repo name, second part is the id
        ids[split_id[0]].append(split_id[1])

    data = {}
    for jira_name in jira_repos_db.list_collection_names():
        issues = jira_repos_db[jira_name].find(
            {'id': {'$in': ids[jira_name]}},
            ['id'] + [attr if attr == 'key' else f'fields.{attr}' for attr in request.attributes]
        )

        for issue in issues:
            attributes = {}
            for attr in request.attributes:
                if attr == 'key':
                    if issue[attr] is None:
                        raise AttributeError(f'Attribute {attr} is required for issue {jira_name}-{issue["id"]}')
                    attributes[attr] = issue[attr]
                elif issue['fields'][attr] is not None:
                    # Attribute exists
                    attributes[attr] = issue['fields'][attr]
                elif attr not in list(default_value.keys()):
                    # Attribute does not exist, but is required
                    raise AttributeError(f'Attribute {attr} is required for issue {jira_name}-{issue["id"]}')
                else:
                    # Use default value for attribute
                    attributes[attr] = default_value[attr]
            data[f'{jira_name}-{issue["id"]}'] = attributes
    response = IssueDataOut()
    response.data = data
    return response
