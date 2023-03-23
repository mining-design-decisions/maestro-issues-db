import typing
from fastapi import APIRouter, UploadFile, Response, Form, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.dependencies import fs, model_info_collection, manual_labels_collection
from app.routers.authentication import validate_token
from bson import ObjectId
from dateutil import parser
from app.util import read_file_in_chunks

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


class PostModelIn(BaseModel):
    config: dict
    name: typing.Optional[str]


class PostModelOut(BaseModel):
    id: str


def _get_model(model_id: str, attributes: list[str]):
    model = model_info_collection.find_one(
        {'_id': ObjectId(model_id)},
        attributes
    )
    if model is None:
        raise HTTPException(
            status_code=404,
            detail=f'Model "{model_id}" was not found'
        )
    return model


def _update_model(model_id: str, update: dict):
    result = model_info_collection.update_one(
        {'_id': ObjectId(model_id)},
        update
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f'Model "{model_id}" was not found'
        )


@router.post('')
def create_model(request: PostModelIn, token=Depends(validate_token)) -> PostModelOut:
    """
    Creates a new model entry with the given config.
    """
    _id = model_info_collection.insert_one({
        'name': '' if request.name is None else request.name,
        'config': request.config,
        'versions': [],
        'performances': {}
    }).inserted_id
    return PostModelOut(id=str(_id))


@router.post('/{model_id}/versions')
def create_model_version(
        model_id: str,
        time: str = Form(),
        file: UploadFile = Form(),
        token=Depends(validate_token)
):
    """
    Upload a new version for the given model-id.
    """
    version_id = fs.put(file.file, filename=file.filename)
    _update_model(model_id, {'$push': {
        'versions': {
            'id': version_id,
            'time': time.replace('.', '_')
        }
    }})
    return {
        'version-id': str(version_id)
    }


@router.get('/{model_id}/versions')
def get_model_versions(model_id: str):
    """
    Get the model versions for the specified model.
    """
    model = _get_model(model_id, ['versions'])
    versions = []
    for version in model['versions']:
        versions.append({
            'id': str(version['id']),
            'time': version['time'].replace('_', '.')
        })
    return {'versions': versions}


@router.get('/{model_id}/versions/{version_id}')
def get_model_version(model_id: str, version_id: str):
    """
    Get the requested version for the given model.
    """
    model = _get_model(model_id, ['versions'])
    for version in model['versions']:
        if version_id == str(version['id']):
            mongo_file = fs.get(version['id'])
            return StreamingResponse(read_file_in_chunks(mongo_file),
                                     media_type='application/octet-stream')
    raise HTTPException(
        status_code=404,
        detail=f'Version "{version_id}" was not found for model "{model_id}"'
    )


class GetModelOut(BaseModel):
    id: str
    name: typing.Optional[str]
    config: dict


@router.get('/{model_id}')
def get_model(model_id: str) -> GetModelOut:
    """
    Return the model with the specified model id.
    """
    model = _get_model(model_id, ['name', 'config'])
    return GetModelOut(
        id=model_id,
        name=model['name'],
        config=model['config']
    )


class UpdateModelIn(BaseModel):
    name: typing.Optional[str]
    config: typing.Optional[dict]


@router.post('/{model_id}')
def update_model(model_id: str, request: UpdateModelIn, token=Depends(validate_token)):
    """
    Update the name and/or config of the model with model_id.
    """
    updated_info = dict()
    if request.name is not None:
        updated_info['name'] = request.name
    if request.config is not None:
        updated_info['config'] = request.config
    _update_model(model_id, {'$set': updated_info})


class GetModelsOut(BaseModel):
    models: list[dict[str, typing.Any]]


@router.get('')
def get_models():
    """
    Returns a list of all models in the database.
    """
    models = model_info_collection.find({}, ['name'])
    response = []
    for model in models:
        response.append({
            'id': str(model['_id']),
            'name': model['name']
        })
    return GetModelsOut(models=response)


class PostPredictionsIn(BaseModel):
    predictions: dict[str, dict[str, dict[str, typing.Any]]]


@router.post('/{model_id}/versions/{version_id}/predictions')
def post_predictions(
        model_id: str,
        version_id: str,
        request: PostPredictionsIn,
        token=Depends(validate_token)
):
    """
    Saves the predictions of the specified model version in the database.
    """
    # Make sure the version of the model exists
    model = _get_model(model_id, ['versions'])
    versions = [str(version['id']) for version in model['versions']]
    if version_id not in versions:
        raise HTTPException(
            status_code=404,
            detail=f'Version "{version_id}" was not found for model "{model_id}"'
        )
    for issue_id, predicted_classes in request.predictions.items():
        predictions = {}
        for predicted_class in predicted_classes:
            predictions[predicted_class] = predicted_classes[predicted_class]
        manual_labels_collection.find_one_and_update(
            {'_id': issue_id},
            {'$set': {
                'predictions': {f'{model_id}-{version_id}': predictions}
            }}
        )


class GetPredictionsIn(BaseModel):
    ids: list[str] | None


class GetPredictionsOut(BaseModel):
    predictions: dict[str, dict[str, dict[str, typing.Any]] | None]


@router.get('/{model_id}/versions/{version_id}/predictions')
def get_predictions(model_id: str, version_id: str, request: GetPredictionsIn):
    """
    Returns the predicted labels of the specified model version.
    """
    if request.ids is None:
        filter_ = {f'predictions.{model_id}-{version_id}': {'$exists': True}}
    else:
        filter_ = {'$and': [
            {'_id': {'$in': request.ids}},
            {f'predictions.{model_id}-{version_id}': {'$exists': True}}
        ]}
    issues = manual_labels_collection.find(filter_, [f'predictions.{model_id}-{version_id}'])
    predictions = dict()
    remaining_ids = set(request.ids)
    for issue in issues:
        issue_id = issue.pop('_id')
        predictions[issue_id] = issue['predictions'][f'{model_id}-{version_id}']
        remaining_ids.remove(issue_id)
    for issue_id in remaining_ids:
        predictions[issue_id] = None
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
    _update_model(model_id, {'$set': {
        f'performances.{request.time.replace(".", "_")}': request.performance
    }})


@router.get('/{model_id}/performances')
def get_performances(model_id: str):
    """
    Get a list of all performance results for the given model.
    """
    model = _get_model(model_id, ['performances'])
    performances = [performance.replace("_", ".") for performance in model['performances']]
    return {'performances': performances}


@router.get('/{model_id}/performances/{performance_time}')
def get_performance(model_id: str, performance_time: str):
    """
    Get the requested performance result.
    """
    model = _get_model(model_id, ['performances'])
    return {performance_time.replace("_", "."): model['performances'][performance_time.replace(".", "_")]}
