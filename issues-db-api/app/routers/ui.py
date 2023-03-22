from fastapi import APIRouter
from pydantic import BaseModel
from app.dependencies import manual_labels_collection, jira_repos_db

router = APIRouter(
    prefix='/ui',
    tags=['ui']
)


class Query(BaseModel):
    filter: dict
    sort: dict[str, str] | None
    models: list[dict[str, str]]
    page: int
    limit: int
    # sort = {
    #     'model-id': str,
    #     'version-id': str,
    #     'class': str
    # }
    # models = [
    #     {
    #         'model-id': str,
    #         'version-id': str
    #     }
    # ]


@router.get('')
def get_ui_data(request: Query):
    page = request.page - 1
    limit = request.limit

    if request.sort is not None:
        issues = manual_labels_collection.find(request.filter)\
            .sort(f'predictions.{request.sort["model-id"]}-{request.sort["version-id"]}.{request.sort["class"]}', -1)\
            .skip(page * limit).limit(limit)
    else:
        issues = manual_labels_collection.find(request.filter).skip(page * limit).limit(limit)

    response = []
    for issue in issues:
        issue_data = jira_repos_db[issue['_id'].split('-')[0]].find_one(
            {'id': issue['_id'].split('-')[1]},
            ['key', 'fields.summary', 'fields.description']
        )
        predictions = []
        for model in request.models:
            if 'predictions' in issue and f'{model["model-id"]}-{model["version-id"]}' in issue['predictions']:
                predictions.append({
                    'model-id': model['model-id'],
                    'version-id': model['version-id'],
                    'predictions': issue['predictions'][f'{model["model-id"]}-{model["version-id"]}']
                })
        response.append({
            'id': issue['_id'],
            'key': issue_data['key'],
            'summary': issue_data['fields']['summary'],
            'description': issue_data['fields']['description'],
            'manual-label': {
                'existence': issue['existence'],
                'property': issue['property'],
                'executive': issue['executive']
            },
            'predictions': predictions
        })
    return {'data': response}
