from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
import typing
import os
import request_examples
# from routers import issue_keys

app = FastAPI()

# app.include_router(issue_keys.router)

# Database setup
client = MongoClient('mongodb://localhost:27017')
# client = MongoClient(os.environ['MONGO_URL'])
database = client['IssueLabels']
collection = database['ManualLabels']
jira_repos = client['JiraRepos']


def validate_filter(query, *, __force_eq=False):
    if not isinstance(query, dict):
        raise _invalid_query(query)
    if len(query) != 1:
        raise _invalid_query(query, 'expected exactly 1 element')
    match query:
        case {'$and': operands}:
            if __force_eq:
                raise _invalid_query(query, '$and was not expected here')
            if not isinstance(operands, list):
                raise _invalid_query(query, '$and operand must be a list')
            for o in operands:
                validate_filter(o)
        case {'$or': operands}:
            if __force_eq:
                raise _invalid_query(query, '$or was not expected here')
            if not isinstance(operands, list):
                raise _invalid_query(query, '$or operand must be a list')
            for o in operands:
                validate_filter(o)
        case {'tags': operand}:
            if not isinstance(operand, dict):
                raise _invalid_query('tag operand must be an object')
            validate_filter(operand, __force_eq=True)
        case {'project': operand}:
            if not isinstance(operand, dict):
                raise _invalid_query('project operand must be an object')
            validate_filter(operand, __force_eq=True)
        case {'$eq': operand}:
            if not __force_eq:
                raise _invalid_query(query, '$eq not expected here')
            if not isinstance(operand, str):
                raise _invalid_query(query, '$eq operand must be a string')
        case {'$ne': operand}:
            if not __force_eq:
                raise _invalid_query(query, '$ne not expected here')
            if not isinstance(operand, str):
                raise _invalid_query(query, '$ne operand must be a string')
        case _ as x:
            raise _invalid_query(x, 'Invalid operation')


def _invalid_query(q, msg=None):
    if msg is not None:
        return ValueError(f'Invalid (sub-)query ({msg}): {q}')
    return ValueError(f'Invalid (sub-)query: {q}')


class IssueKeysIn(BaseModel):
    filter: dict

    class Config:
        schema_extra = request_examples.issue_keys_example


class IssueKeysOut(BaseModel):
    keys: list[str] = []


@app.get('/issue-keys')
def issue_keys(request: IssueKeysIn) -> IssueKeysOut:
    '''
    Returns the issue keys for which the issue tags match
    the provided filtering options. These filtering options are
    given in the body of the request.
    TODO: Fix input validation
    '''
    filter = request.filter
    validate_filter(filter)
    issues = collection.find(
        filter,
        {'key'}
    )
    response = IssueKeysOut()
    response.keys = [issue['key'] for issue in issues]
    return response


class ManualLabelsIn(BaseModel):
    keys: list[str]
    
    class Config:
        schema_extra = request_examples.manual_labels_example


class Label(typing.TypedDict):
    existence: bool
    property: bool
    executive: bool

class ManualLabelsOut(BaseModel):

    labels: dict[str, Label] = {}


@app.get('/manual-labels', response_model=ManualLabelsOut)
def manual_labels(request: ManualLabelsIn) -> ManualLabelsOut:
    '''
    Returns the manual labels of the issue keys that were
    provided in the request body.
    TODO: Fix input validation
    '''
    issues = collection.find(
        {'key': {'$in': request.keys}},
        ['key', 'existence', 'property', 'executive']
    )

    # Build and send response
    response = ManualLabelsOut()
    labels = {}
    for issue in issues:
        labels[issue['key']] = {
            'existence': issue['existence'],
            'property': issue['property'],
            'executive': issue['executive']
        }
    response.labels = labels
    return response


class IssueDataIn(BaseModel):
    keys: list[str]
    attributes: list[str]

    class Config:
        schema_extra = request_examples.issue_data_example

class IssueDataOut(BaseModel):
    data: dict[str, dict[str, typing.Any]] = {}


@app.get('/issue-data')
def issue_data(request: IssueDataIn) -> IssueDataOut:
    '''
    Returns issue data. The returned data is determined by the
    specified issue keys and the attributes that are requested.
    '''
    issues = []
    for repo in jira_repos.list_collection_names():
        repo_issues = jira_repos[repo].find(
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
            attributes[attr] = issue['fields'][attr]
        data[issue['key']] =  attributes
    response.data = data
    return response


class SavePredictionsIn(BaseModel):
    model: str
    predictions: dict[str, dict[str, bool]]

    class Config:
        schema_extra = request_examples.save_prediction_example


@app.put('/save-predictions')
def save_predictions(request: SavePredictionsIn):
    '''
    Saves the given predictions for the given model.
    '''
    model_collection = client['PredictedLabels'][request.model]
    for key in request.predictions:
        model_collection.insert_one({
            'key': key,
            'existence': request.predictions[key]['existence'],
            'property': request.predictions[key]['property'],
            'executive': request.predictions[key]['executive']
        })


class AddTagsIn(BaseModel):
    data: dict[str, list[str]]
    
    class Config:
        schema_extra = request_examples.add_tags_example


@app.patch('/add-tags')
def add_tags(request: AddTagsIn):
    '''
    Method for adding tags to issues in bulk. The tags and
    issue keys should be specified in the request body.
    '''
    for key in request.data:
        # Get the current list of tags of this issue
        issue = collection.find_one(
            {'key': key},
            ['tags']
        )
        tags = issue['tags']

        # Add the new tags
        for tag in request.data[key]:
            # Only add non-existing tags
            if tag not in tags:
                tags.append(tag)
        
        # Update entry with the new tags
        collection.update_one(
            {'key': key},
            {'$set': {'tags': tags}}
        )
    # TODO: what to do with error handling here?


@app.get('/tags')
def tags() -> list[str]:
    '''
    Returns a list of all tags that are present in the database.
    '''
    tags = set()
    issues = collection.find({}, ['tags'])
    for issue in issues:
        for tag in issue['tags']:
            tags.add(tag)
    return tags


@app.get('/fix-db')
def fix_db():
    renamed_issues = {}
    keys = set()
    # Find all keys and renamed keys in all repos
    for repo in jira_repos.list_collection_names():
        issues = jira_repos[repo].find(
            {},
            ['key', 'changelog']
        )

        for issue in issues:
            keys.add(issue['key'])
            if 'changelog' not in issue:
                continue
            if 'histories' not in issue['changelog']:
                continue
            for history in issue['changelog']['histories']:
                for change in history['items']:
                    if 'field' not in change:
                        continue
                    if change['field'] != 'Key':
                        continue
                    renamed_issues[change['fromString']] = issue['key']

    # Fix renamed issue key inconsistencies
    issues = collection.find({}, {'key', 'tags'})
    for issue in issues:
        if issue['key'] in renamed_issues:
            new_key = renamed_issues[issue['key']]
        else:
            new_key = issue['key']
        tags = issue['tags']
        tags.append('has-label')
        collection.update_one(
            {'key': issue['key']},
            {'$set': {'key': new_key,
                      'tags': tags}}
        )
        if new_key in keys:
            keys.remove(new_key)

    # Add the keys that are not yet in the db
    for key in keys:
        project = key.split('-')[0]
        collection.insert_one({
            'key': key,
            'existence': None,
            'property': None,
            'executive': None,
            'tags': [project]
        })
    
    # TODO: Return duplicate keys
