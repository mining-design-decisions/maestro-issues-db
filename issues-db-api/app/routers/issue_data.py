import typing
from fastapi import APIRouter
from pydantic import BaseModel
from app.dependencies import jira_repos_db, issue_links_collection
from app.exceptions import get_attr_required_exception, duplicate_issue_exception, attribute_not_found_exception,\
    issues_not_found_exception

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


class IssueDataIn(BaseModel):
    issue_ids: list[str]
    attributes: list[str]


class AttributeOut(BaseModel):
    name: str
    value: typing.Any


class IssueOut(BaseModel):
    issue_id: str
    attributes: list[AttributeOut]


class IssueDataOut(BaseModel):
    data: list[IssueOut]


@router.post('')
def get_issue_data(request: IssueDataIn) -> IssueDataOut:
    """
    Returns issue data. The returned data is determined by the
    specified issue ids and the attributes that are requested.
    """
    # Collect the ids belonging to each Jira repo
    ids = dict()
    for jira_name in jira_repos_db.list_collection_names():
        ids[jira_name] = []
    for issue_id in request.issue_ids:
        split_id = issue_id.split('-')
        # First part is the jira repo name, second part is the id
        ids[split_id[0]].append(split_id[1])

    data = []
    for jira_name in jira_repos_db.list_collection_names():
        issue_link_prefix = issue_links_collection.find_one({'_id': jira_name})['link']
        issues = jira_repos_db[jira_name].find(
            {'id': {'$in': ids[jira_name]}},
            ['id', 'key'] + [f'fields.{attr}' for attr in request.attributes if attr not in ['key', 'link']]
        )

        remaining_ids = set(ids[jira_name])
        for issue in issues:
            if issue['id'] not in remaining_ids:
                raise duplicate_issue_exception(jira_name, issue['id'])
            remaining_ids.remove(issue['id'])
            attributes = []
            for attr in request.attributes:
                if attr == 'key':
                    if issue[attr] is None:
                        raise get_attr_required_exception(attr, f'{jira_name}-{issue["id"]}')
                    attributes.append(AttributeOut(name=attr, value=issue[attr]))
                elif attr == 'link':
                    attributes.append(AttributeOut(name=attr, value=f'{issue_link_prefix}/browse/{issue["key"]}'))
                elif attr not in issue['fields']:
                    if attr == 'parent':
                        attributes.append(AttributeOut(name=attr, value=None))
                    else:
                        raise attribute_not_found_exception(attr, jira_name, issue['id'])
                elif issue['fields'][attr] is not None:
                    # Attribute exists
                    if attr in 'issuelinks':
                        issuelinks = issue['fields'][attr]
                        for idx in range(len(issuelinks)):
                            if 'outwardIssue' in issuelinks[idx]:
                                issuelinks[idx]['outwardIssue'] = f'{jira_name}-{issuelinks[idx]["outwardIssue"]["id"]}'
                            if 'inwardIssue' in issuelinks[idx]:
                                issuelinks[idx]['inwardIssue'] = f'{jira_name}-{issuelinks[idx]["inwardIssue"]["id"]}'
                        attributes.append(AttributeOut(name=attr, value=issuelinks))
                    elif attr == 'parent':
                        attributes.append(AttributeOut(name=attr, value=f'{jira_name}-{issue["fields"][attr]["id"]}'))
                    elif attr == 'subtasks':
                        subtasks = []
                        for subtask in issue['fields'][attr]:
                            subtasks.append(f'{jira_name}-{subtask["id"]}')
                        attributes.append(AttributeOut(name=attr, value=subtasks))
                    else:
                        attributes.append(AttributeOut(name=attr, value=issue['fields'][attr]))
                elif attr not in list(default_value.keys()):
                    # Attribute does not exist, but is required
                    raise get_attr_required_exception(attr, f'{jira_name}-{issue["id"]}')
                else:
                    # Use default value for attribute
                    attributes.append(AttributeOut(name=attr, value=default_value[attr]))
            data.append(IssueOut(issue_id=f'{jira_name}-{issue["id"]}', attributes=attributes))
        if remaining_ids:
            raise issues_not_found_exception([f'{jira_name}-{id_}' for id_ in remaining_ids])
    return IssueDataOut(data=data)
