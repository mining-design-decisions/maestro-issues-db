import typing
from fastapi import APIRouter, UploadFile, Response, Form, Depends
from pydantic import BaseModel
from app.dependencies import mongo_client, fs
from app.routers.authentication import validate_token
from bson import ObjectId
from dateutil import parser

router = APIRouter(
    prefix='/models',
    tags=['models']
)
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


@router.post('')
def put_model(request: PutModelIn, token=Depends(validate_token)) -> PutModelOut:
    """
    Creates a new model entry with the given config.
    """
    _id = mongo_client['Models']['ModelInfo'].insert_one({
        'config': request.config,
        'versions': [],
        'performances': {}
    }).inserted_id
    return PutModelOut(id=str(_id))


@router.post('/{model_id}/versions')
def put_model_version(
        model_id: str,
        time: str = Form(),
        file: UploadFile = Form(),
        token=Depends(validate_token)
):
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


@router.get('/{model_id}/versions')
def get_model_versions(model_id: str):
    """
    Get the model versions for the specified model.
    """
    model = mongo_client['Models']['ModelInfo'].find_one(
        {'_id': ObjectId(model_id)},
        ['versions']
    )
    versions = [str(version['id']) for version in model['versions']]
    return {'versions': versions}


@router.get('/{model_id}/versions/{version_id}')
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


@router.get('/{model_id}')
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


@router.get('')
def get_models():
    models = mongo_client['Models']['ModelInfo'].find(
        {},
        ['_id']
    )
    model_ids = [str(model['_id']) for model in models]
    return GetModelsOut(ids=model_ids)


class PostPredictionsIn(BaseModel):
    predictions: dict[str, dict[str, dict[str, typing.Any]]]


@router.post('/{model_id}/versions/{version_id}/predictions')
def post_predictions(
        model_id: str,
        version_id: str,
        request: PostPredictionsIn,
        token=Depends(validate_token)
):
    for issue_id, predicted_classes in request.predictions.items():
        issue = {'_id': issue_id}
        for predicted_class in predicted_classes:
            issue[predicted_class] = predicted_classes[predicted_class]
        mongo_client['PredictedLabels'][f'{model_id}-{version_id}'].insert_one(issue)


class GetPredictionsOut(BaseModel):
    predictions: dict[str, dict[str, dict[str, typing.Any]]]


@router.get('/{model_id}/versions/{version_id}/predictions')
def get_predictions(model_id: str, version_id: str):
    issues = mongo_client['PredictedLabels'][f'{model_id}-{version_id}'].find({})
    predictions = dict()
    for issue in issues:
        issue_id = issue.pop('_id')
        predictions[issue_id] = issue
    return GetPredictionsOut(predictions=predictions)


class PostPerformanceIn(BaseModel):
    time: str
    performance: list


@router.post('/{model_id}/performances')
def post_performance(
        model_id: str,
        request: PostPerformanceIn,
        token=Depends(validate_token)
):
    """
    Add a performance result for the given model.
    """
    mongo_client['Models']['ModelInfo'].update_one(
        {'_id': ObjectId(model_id)},
        {'$set': {f'performances.{request.time.replace(".", "_")}': request.performance}}
    )


@router.get('/{model_id}/performances')
def get_performances(model_id: str):
    """
    Get a list of all performance results for the given model.
    """
    model = mongo_client['Models']['ModelInfo'].find_one(
        {'_id': ObjectId(model_id)},
        ['performances']
    )
    performances = [performance.replace("_", ".") for performance in model['performances']]
    return {'performances': performances}


@router.get('/{model_id}/performances/{performance_time}')
def get_performance(model_id: str, performance_time: str):
    """
    Get the requested performance result.
    """
    model = mongo_client['Models']['ModelInfo'].find_one(
        {'_id': ObjectId(model_id)},
        ['performances']
    )
    if model is None:
        raise Exception(f'Model {model_id} not found')
    return {performance_time.replace("_", "."): model['performances'][performance_time.replace(".", "_")]}
