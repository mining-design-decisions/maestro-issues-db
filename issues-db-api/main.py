from fastapi import FastAPI, Request
from pymongo import MongoClient
import os

app = FastAPI()

# Database setup
# client = MongoClient('mongodb://localhost:27017')
client = MongoClient(os.environ['MONGO_URL'])
database = client['IssueLabels']
collection = database['ManualLabels']
jira_repos = client['JiraRepos']


@app.get('/issue-keys')
async def issue_keys(request: Request):
    '''
    Returns the issue keys for which the issue tags match
    the provided filtering options. These filtering options are
    given in the body of the request.
    TODO: Fix input validation
    '''
    filter = await request.json()
    issues = collection.find(
        filter,
        {'_id'}
    )
    return [issue['_id'] for issue in issues]


@app.get('/manual-labels')
async def manual_labels(request: Request):
    '''
    Returns the manual labels of the issue keys that were
    provided in the request body.
    TODO: Fix input validation
    '''
    keys = await request.json()
    issues = collection.find(
        {'_id': {'$in': keys}},
        ['existence', 'property', 'executive']
    )

    # Build and send response
    response = {}
    for issue in issues:
        response[issue['_id']] = {
            'existence': issue['existence'],
            'property': issue['property'],
            'executive': issue['executive']
        }
    return response


@app.get('/issue-data')
async def issue_data(request: Request):
    data = await request.json()
    keys = data['keys']

    issues = []
    for repo in jira_repos.list_collection_names():
        repo_issues = jira_repos[repo].find(
            {'key': {'$in': keys}},
            ['key'] + [f'fields.{attr}' for attr in data['attributes']]
        )
        issues.extend(list(repo_issues))
    response = {}
    for issue in issues:
        attributes = {}
        for attr in data['attributes']:
            attributes[attr] = issue['fields'][attr]
        response[issue['key']] =  attributes
    return response


@app.get('/save-predictions')
async def save_predictions(request: Request):
    return []


@app.patch('/add-tags')
async def add_tags(request: Request):
    data = await request.json()
    for item in data:
        # Get the current list of tags of this issue
        issue = collection.find_one(
            {'_id': item['key']},
            ['tags']
        )
        tags = issue['tags']

        # Add the new tags
        for tag in item['tags']:
            # Only add non-existing tags
            if tag not in tags:
                tags.append(tag)
        
        # Update entry with the new tags
        collection.update_one(
            {'_id': item['key']},
            {'$set': {'tags': tags}}
        )
    # TODO: what to do with error handling here?


@app.get('/fix-project-tags')
def add_project_tags():
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
