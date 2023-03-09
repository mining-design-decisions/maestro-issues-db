import typing
from fastapi import APIRouter, UploadFile, Response, Form
from pydantic import BaseModel
from app.dependencies import mongo_client, fs
from bson import ObjectId
from dateutil import parser

router = APIRouter()
example_request = {
    "example": {
        'model': 'MODEL-1',
        'predictions': {
            'ISSUE-ID-1': {
                "existence": {
                    "prediction": True,
                    "probability": 0.42
                },
                "property": {
                    "prediction": False,
                    "probability": 0.42
                },
                "executive": {
                    "prediction": False,
                    "probability": 0.42
                }
            },
            'ISSUE-ID-2': {
                "existence": {
                    "prediction": False,
                    "probability": 0.42
                },
                "property": {
                    "prediction": True,
                    "probability": 0.42
                },
                "executive": {
                    "prediction": False,
                    "probability": 0.42
                }
            },
        }
    }
}


class SavePredictionsIn(BaseModel):
    model: str
    predictions: dict[str, dict[str, dict[str, typing.Any]]]

    class Config:
        schema_extra = example_request


class PutModelIn(BaseModel):
    config: dict


class PutModelOut(BaseModel):
    id: str


@router.post('/models')
def put_model(request: PutModelIn) -> PutModelOut:
    """
    Creates a new model entry with the given config.
    """
    _id = mongo_client['Models']['ModelInfo'].insert_one({
        'config': request.config,
        'versions': []
    }).inserted_id
    return PutModelOut(id=str(_id))


@router.post('/models/{model_id}/versions')
def put_model_version(model_id: str, time: str = Form(), file: UploadFile = Form()):
    """
    Upload a new version for the given model-id.
    """
    version_id = fs.put(file.file, filename=file.filename)
    mongo_client['Models']['ModelInfo'].update_one(
        {'_id': ObjectId(model_id)},
        {'$push': {'versions': {
            'id': version_id,
            'time': parser.parse(time)
        }}}
    )
    return {
        'version-id': str(version_id)
    }


@router.get('/models/{model_id}/versions/{version_id}')
def get_model_version(model_id: str, version_id: str):
    """
    Get the requested version for the given model.
    """
    model = mongo_client['Models']['ModelInfo'].find_one(
        {'_id': ObjectId(model_id)},
        ['versions']
    )
    if model is None:
        raise Exception(f'Model {model_id} not found')
    for version in model['versions']:
        if version_id == str(version['id']):
            mongo_file = fs.get(version['id'])
            return Response(mongo_file.read(),
                            media_type='application/octet-stream')
    raise Exception(f'Version {version_id} not found for model {model_id}')


class GetModelOut(BaseModel):
    id: str
    config: dict
    versions: typing.Any


@router.get('/models/{model_id}')
def get_model(model_id: str) -> GetModelOut:
    model = mongo_client['Models']['ModelInfo'].find_one({
        '_id': ObjectId(model_id)
    })
    versions = []
    for version in model['versions']:
        versions.append({
            'id': str(version['id']),
            'time': version['time'].isoformat()
        })
    return GetModelOut(
        id=model_id,
        config=model['config'],
        versions=versions
    )


class GetModelsOut(BaseModel):
    ids: list[str]


@router.get('/models')
def get_models():
    models = mongo_client['Models']['ModelInfo'].find(
        {},
        ['_id']
    )
    model_ids = [str(model['_id']) for model in models]
    return GetModelsOut(ids=model_ids)


class PostPredictionsIn(BaseModel):
    predictions: dict[str, dict[str, dict[str, typing.Any]]]


@router.post('/models/{model_id}/versions/{version_id}/predictions')
def post_predictions(model_id: str, version_id: str, request: PostPredictionsIn):
    for issue_id, predicted_classes in request.predictions.items():
        issue = {'_id': issue_id}
        for predicted_class in predicted_classes:
            issue[predicted_class] = predicted_classes[predicted_class]
        mongo_client['PredictedLabels'][f'{model_id}-{version_id}'].insert_one(issue)


class GetPredictionsOut(BaseModel):
    predictions: dict[str, dict[str, dict[str, typing.Any]]]


@router.get('/models/{model_id}/versions/{version_id}/predictions')
def get_predictions(model_id: str, version_id: str):
    issues = mongo_client['PredictedLabels'][f'{model_id}-{version_id}'].find({})
    predictions = dict()
    for issue in issues:
        issue_id = issue.pop('_id')
        predictions[issue_id] = issue
    return GetPredictionsOut(predictions=predictions)
