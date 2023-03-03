from fastapi import FastAPI, Request
from pymongo import MongoClient

app = FastAPI()

# Database setup
client = MongoClient('mongodb://localhost:27017')
database = client['IssueLabels']
collection = database['ManualLabels']
jira_repos = client['JiraRepos']


@app.get('/issue-keys')
async def issue_keys(request: Request):
    '''
    TODO: add support for PROJECT
    TODO: Fix input validation
    '''
    filter = await request.json()
    issues = collection.find(filter)
    return list(issues)


@app.get('/manual-labels')
async def manual_labels(request: Request):
    '''
    TODO: Fix input validation
    '''
    keys = await request.json()
    issues = collection.find(
        {'_id': {'$in': keys}},
        ['existence', 'property', 'executive']
    )
    return list(issues)


@app.get('/issue-data')
async def issue_data(request: Request):
    data = await request.json()
    keys = data['keys']
    attributes = [f'fields.{attr}' for attr in data['attributes']]
    print(keys)
    print(attributes)

    issues = []
    for repo in jira_repos.list_collection_names():
        repo_issues = jira_repos[repo].find(
            {'key': {'$in': keys}},
            attributes
        )
        issues.extend(list(repo_issues))
    for idx in range(len(issues)):
        del issues[idx]['_id']
    return issues


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
