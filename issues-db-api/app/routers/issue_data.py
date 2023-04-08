import typing
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.dependencies import jira_repos_db, issue_links_collection

router = APIRouter(
    prefix='/issue-data',
    tags=['issue-data']
)

default_value = {
    'summary': '',
    'description': '',
    'labels': [],
    'components': [],
    'votes': 0,
    'watches': 0,
    'parent': None,
    'issuelinks': [],
    'attachments': [],
    'sub-tasks': [],
    'resolution': None,
    'assignee': None
}


def get_attr_required_exception(attribute: str, issue_id: str):
    return HTTPException(
        status_code=409,
        detail=f'Attribute "{attribute}" is required for issue "{issue_id}"'
    )


class IssueDataIn(BaseModel):
    ids: list[str]
    attributes: list[str]


class IssueDataOut(BaseModel):
    data: dict[str, dict[str, typing.Any]] = {}


@router.get('')
def get_issue_data(request: IssueDataIn) -> IssueDataOut:
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
        issue_link_prefix = issue_links_collection.find_one({'_id': jira_name})['link']
        issues = jira_repos_db[jira_name].find(
            {'id': {'$in': ids[jira_name]}},
            ['id', 'key'] + [f'fields.{attr}' for attr in request.attributes if attr not in ['key', 'link']]
        )

        remaining_ids = set(ids[jira_name])
        for issue in issues:
            if issue['id'] not in remaining_ids:
                raise HTTPException(
                    status_code=409,
                    detail=f'Duplicate issue in the database: {jira_name}-{issue["id"]}'
                )
            remaining_ids.remove(issue['id'])
            attributes = {}
            for attr in request.attributes:
                if attr == 'key':
                    if issue[attr] is None:
                        raise get_attr_required_exception(attr, f'{jira_name}-{issue["id"]}')
                    attributes[attr] = issue[attr]
                elif attr == 'link':
                    attributes[attr] = f'{issue_link_prefix}/browse/{issue["key"]}'
                elif attr not in issue['fields']:
                    if attr == 'parent':
                        attributes[attr] = None
                    else:
                        raise HTTPException(
                            status_code=404,
                            detail=f'Attribute "{attr}" is not found for issue: {jira_name}-{issue["id"]}'
                        )
                elif issue['fields'][attr] is not None:
                    # Attribute exists
                    if attr == 'issuelinks':
                        issuelinks = issue['fields'][attr]
                        for idx in range(len(issuelinks)):
                            if 'outwardIssue' in issuelinks[idx]:
                                issuelinks[idx]['outwardIssue'] = f'{jira_name}-{issuelinks[idx]["outwardIssue"]["id"]}'
                            if 'inwardIssue' in issuelinks[idx]:
                                issuelinks[idx]['inwardIssue'] = f'{jira_name}-{issuelinks[idx]["inwardIssue"]["id"]}'
                        attributes[attr] = issuelinks
                    elif attr == 'parent':
                        attributes[attr] = f'{jira_name}-{issue["fields"][attr]["id"]}'
                    elif attr == 'subtasks':
                        subtasks = []
                        for subtask in issue['fields'][attr]:
                            subtasks.append(f'{jira_name}-{subtask["id"]}')
                        attributes[attr] = subtasks
                    else:
                        attributes[attr] = issue['fields'][attr]
                elif attr not in list(default_value.keys()):
                    # Attribute does not exist, but is required
                    raise get_attr_required_exception(attr, f'{jira_name}-{issue["id"]}')
                else:
                    # Use default value for attribute
                    attributes[attr] = default_value[attr]
            data[f'{jira_name}-{issue["id"]}'] = attributes
        if remaining_ids:
            raise HTTPException(
                status_code=404,
                detail=f'The following issue(s) could not be found: '
                       f'{[f"{jira_name}-{id_}" for id_ in remaining_ids]}'
            )
    response = IssueDataOut()
    response.data = data
    return response
