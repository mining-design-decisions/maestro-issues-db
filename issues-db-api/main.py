from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
import os

app = FastAPI()

# Database setup
# client = MongoClient('mongodb://localhost:27017')
client = MongoClient(os.environ['MONGO_URL'])
database = client['IssueLabels']
collection = database['ManualLabels']
jira_repos = client['JiraRepos']


class IssueKeysIn(BaseModel):
    filter: dict = {
        "$and": [
            {"tags": {"$eq": "tag1"}},
            {"$or": [
                {"tags": {"$ne": "tag2"}},
                {"tags": {"$eq": "tag3"}}
            ]}
        ]
    }


class IssueKeysOut(BaseModel):
    keys: list[str] = [
        'ISSUE-1',
        'ISSUE-2'
    ]


@app.get('/issue-keys', response_model=IssueKeysOut)
def issue_keys(request: IssueKeysIn):
    '''
    Returns the issue keys for which the issue tags match
    the provided filtering options. These filtering options are
    given in the body of the request.
    TODO: Fix input validation
    '''
    filter = request.filter
    issues = collection.find(
        filter,
        {'_id'}
    )
    response = IssueKeysOut()
    response.keys = [issue['_id'] for issue in issues]
    return response


class ManualLabelsIn(BaseModel):
    keys: list[str] = [
        'ISSUE-1',
        'ISSUE-2'
    ]


class ManualLabelsOut(BaseModel):
    labels: dict = {
        'ISSUE-1': {
            'existence': True,
            'property': False,
            'executive': False
        },
        'ISSUE-2': {
            'existence': False,
            'property': True,
            'executive': False
        }
    }


@app.get('/manual-labels', response_model=ManualLabelsOut)
def manual_labels(request: ManualLabelsIn):
    '''
    Returns the manual labels of the issue keys that were
    provided in the request body.
    TODO: Fix input validation
    '''
    issues = collection.find(
        {'_id': {'$in': request.keys}},
        ['existence', 'property', 'executive']
    )

    # Build and send response
    response = ManualLabelsOut()
    labels = {}
    for issue in issues:
        labels[issue['_id']] = {
            'existence': issue['existence'],
            'property': issue['property'],
            'executive': issue['executive']
        }
    response.labels = labels
    return response


class IssueDataIn(BaseModel):
    keys: list[str] = [
        'ISSUE-1',
        'ISSUE-2'
    ]
    attributes: list[str] = [
        'summary',
        'description'
    ]

class IssueDataOut(BaseModel):
    data: dict = {
        'ISSUE-1': {
            'summary': 'Summary of ISSUE-1',
            'description': 'Description of ISSUE-1'
        },
        'ISSUE-2': {
            'summary': 'Summary of ISSUE-2',
            'description': 'Description of ISSUE-2'
        }
    }


@app.get('/issue-data', response_model=IssueDataOut)
def issue_data(request: IssueDataIn):
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
    model: str = 'MODEL-1'
    predictions: dict = {
        'ISSUE-1': {
            'existence': True,
            'property': False,
            'executive': False
        },
        'ISSUE-2': {
            'existence': False,
            'property': True,
            'executive': False
        }
    }


@app.put('/save-predictions')
def save_predictions(request: SavePredictionsIn):
    '''
    Saves the given predictions for the given model.
    '''
    model_collection = client['PredictedLabels'][request.model]
    for key in request.predictions:
        model_collection.insert_one({
            '_id': key,
            'existence': request.predictions[key]['existence'],
            'property': request.predictions[key]['property'],
            'executive': request.predictions[key]['executive']
        })


class AddTags(BaseModel):
    data = {
        'ISSUE-1': [
            'TAG-1',
            'TAG-2'
        ],
        'ISSUE-2': [
            'TAG-3',
            'TAG-4'
        ]
    }


@app.patch('/add-tags')
def add_tags(request: AddTags):
    '''
    Method for adding tags to issues in bulk. The tags and
    issue keys should be specified in the request body.
    '''
    for key in request.data:
        # Get the current list of tags of this issue
        issue = collection.find_one(
            {'_id': key},
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
            {'_id': key},
            {'$set': {'tags': tags}}
        )
    # TODO: what to do with error handling here?


@app.patch('/fix-project-tags')
def fix_project_tags():
    '''
    This method adds the project to the tags field
    for each issue in the manual labels database.
    '''
    issues = collection.find({})
    for issue in issues:
        project = issue['_id'].split('-')[0]
        tags = issue['tags']
        if project not in tags:
            tags.append(project)
        collection.update_one(
            {'_id': issue['_id']},
            {'$set': {'tags': tags}}
        )
