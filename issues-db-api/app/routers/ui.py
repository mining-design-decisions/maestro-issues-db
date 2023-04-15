from fastapi import APIRouter
from pydantic import BaseModel
from app.dependencies import issue_labels_collection, jira_repos_db, issue_links_collection, models_collection
from app.exceptions import ui_sort_exception, version_not_specified_exception, model_not_found_exception,\
    version_not_found_exception
from bson import ObjectId
import math

router = APIRouter(
    prefix='/ui',
    tags=['ui']
)


class Query(BaseModel):
    filter: dict
    sort: str | None
    sort_ascending: bool
    models: list[str]
    page: int
    limit: int

    class Config:
        schema_extra = {
            "example": {
                'filter': 'object',
                'sort': 'predictions.model_id-version_id.existence',
                'sort_ascending': True,
                'models': ['model_id-version_id'],
                'page': 42,
                'limit': 42
            }
        }


class ManualLabel(BaseModel):
    existence: bool | None
    property: bool | None
    executive: bool | None


class UIData(BaseModel):
    issue_id: str
    issue_link: str
    issue_key: str
    summary: str
    description: str
    manual_label: ManualLabel
    predictions: dict[str, dict | None]
    tags: list[str]
    comments: dict[str, dict[str, str]]


class UIDataOut(BaseModel):
    data: list[UIData]
    total_pages: int

    class Config:
        schema_extra = {
            "example": {
                "data": [{
                    "issue_id": "string",
                    "issue_link": "string",
                    "issue_key": "string",
                    "summary": "string",
                    "description": "string",
                    "manual_label": {
                        "existence": True,
                        "property": False,
                        "executive": True
                    },
                    "predictions": {
                        "model_id-version_id": {
                            "existence": {
                                "prediction": False,
                                "confidence": 0.42
                            }
                        }
                    },
                    "tags": ["example-tag"],
                    "comments": {
                        "comment_id": {
                            "author": "username",
                            "comment": "sample comment"
                        }
                    }
                }],
                "total_pages": 42
            }
        }


@router.get('', response_model=UIDataOut)
def get_ui_data(request: Query):
    page = request.page - 1
    limit = request.limit
    total_pages = math.ceil(issue_labels_collection.count_documents(request.filter) / limit)

    for model in request.models:
        if len(model.split('-')) != 2:
            raise version_not_specified_exception(model)
        model_id = model.split('-')[0]
        version_id = model.split('-')[1]
        db_model = models_collection.find_one({'_id': ObjectId(model_id)})
        if db_model is None:
            raise model_not_found_exception(model_id)
        if ObjectId(version_id) not in [version['id'] for version in db_model['versions']]:
            raise version_not_found_exception(version_id, model_id)

    if request.sort is not None:
        predictions_found = False
        indexes = issue_labels_collection.index_information()
        for key, value in indexes.items():
            for col in value['key']:
                if col[0] == request.sort:
                    predictions_found = True
                    break
        if not predictions_found:
            raise ui_sort_exception(request.sort)
        sort_direction = 1 if request.sort_ascending else -1
        issues = issue_labels_collection.find(request.filter)\
            .sort(request.sort, sort_direction)\
            .skip(page * limit).limit(limit)
    else:
        issues = issue_labels_collection.find(request.filter).skip(page * limit).limit(limit)

    response = []
    for issue in issues:
        issue_data = jira_repos_db[issue['_id'].split('-')[0]].find_one(
            {'id': issue['_id'].split('-')[1]},
            ['key', 'fields.summary', 'fields.description']
        )
        issue_link_prefix = issue_links_collection.find_one({'_id': issue['_id'].split('-')[0]})['link']
        predictions = {}
        for model in request.models:
            if 'predictions' in issue and model in issue['predictions']:
                predictions[model] = issue['predictions'][model]
        response.append(UIData(
            issue_id=issue['_id'],
            issue_link=f'{issue_link_prefix}/browse/{issue_data["key"]}',
            issue_key=issue_data['key'],
            summary=issue_data['fields']['summary'],
            description=issue_data['fields']['description'],
            manual_label=ManualLabel(
                existence=issue['existence'],
                property=issue['property'],
                executive=issue['executive']
            ),
            predictions=predictions,
            tags=issue['tags'],
            comments=issue["comments"]
        ))
    return UIDataOut(data=response, total_pages=total_pages)
