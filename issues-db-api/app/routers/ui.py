from fastapi import APIRouter
from pydantic import BaseModel
from app.dependencies import manual_labels_collection, jira_repos_db, issue_labels_db

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
        issues = manual_labels_collection.aggregate([
            {'$match': request.filter},
            {'$lookup': {
                'from': f'{request.sort["model-id"]}-{request.sort["version-id"]}',
                'localField': '_id',
                'foreignField': '_id',
                'as': 'predicted_label'
            }},
            {'$sort': {
                f'predicted_label.0.{request.sort["class"]}.probability': -1
            }},
            {'$skip': page * limit},
            {'$limit': limit}
        ])
    else:
        issues = manual_labels_collection.find(request.filter, ['_id']).skip(page * limit).limit(limit)

    response = []
    for issue in issues:
        issue_data = jira_repos_db[issue['_id'].split('-')[0]].find_one(
            {'id': issue['_id'].split('-')[1]},
            ['key', 'fields.summary', 'fields.description']
        )
        manual_label = manual_labels_collection.find_one({'_id': issue['_id']})
        predictions = []
        for model in request.models:
            prediction = issue_labels_db[f'{model["model-id"]}-{model["version-id"]}'].find_one({
                '_id': issue['_id']
            })
            if prediction is not None:
                del prediction['_id']
            predictions.append({
                'model-id': model['model-id'],
                'version-id': model['version-id'],
                'predictions': prediction
            })
        response.append({
            'id': issue['_id'],
            'key': issue_data['key'],
            'summary': issue_data['fields']['summary'],
            'description': issue_data['fields']['description'],
            'manual-label': {
                'existence': manual_label['existence'],
                'property': manual_label['property'],
                'executive': manual_label['executive']
            },
            'predictions': predictions
        })
    return {'data': response}
