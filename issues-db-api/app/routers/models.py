import typing
from fastapi import APIRouter, UploadFile, Response, Form, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.dependencies import fs, model_collection, manual_labels_collection
from app.routers.authentication import validate_token
from bson import ObjectId
from app.util import read_file_in_chunks
from app.exceptions import model_not_found_exception, version_not_found_exception, performance_not_found_exception,\
    issue_not_found_exception

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
                    "confidence": 0.42
                },
                "property": {
                    "prediction": False,
                    "confidence": 0.42
                },
                "executive": {
                    "prediction": False,
                    "confidence": 0.42
                }
            },
            'ISSUE-ID-2': {
                "existence": {
                    "prediction": False,
                    "confidence": 0.42
                },
                "property": {
                    "prediction": True,
                    "confidence": 0.42
                },
                "executive": {
                    "prediction": False,
                    "confidence": 0.42
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


class GetModelOut(BaseModel):
    id: str
    name: typing.Optional[str]
    config: dict


class UpdateModelIn(BaseModel):
    name: typing.Optional[str]
    config: typing.Optional[dict]


class GetModelsOut(BaseModel):
    models: list[dict[str, typing.Any]]


class PostPerformanceIn(BaseModel):
    time: str
    performance: list


class PostPredictionsIn(BaseModel):
    predictions: dict[str, dict[str, dict[str, typing.Any]]]


class GetPredictionsIn(BaseModel):
    ids: list[str] | None


class GetPredictionsOut(BaseModel):
    predictions: dict[str, dict[str, dict[str, typing.Any]] | None]


def _get_model(model_id: str, attributes: list[str]):
    model = model_collection.find_one(
        {'_id': ObjectId(model_id)},
        attributes
    )
    if model is None:
        raise model_not_found_exception(model_id)
    return model


def _update_model(model_id: str, update: dict):
    result = model_collection.update_one(
        {'_id': ObjectId(model_id)},
        update
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f'Model "{model_id}" was not found'
        )


def _delete_predictions(model_id: str, version_id: ObjectId):
    # Remove predictions
    manual_labels_collection.update_many(
        {},
        {'$unset': {f'predictions.{model_id}-{version_id}': ""}}
    )
    # Remove indexes
    indexes = manual_labels_collection.index_information()
    for key, value in indexes.items():
        for col in value['key']:
            if f'predictions.{model_id}-{version_id}' in col[0]:
                manual_labels_collection.drop_index(key)
                break


def _delete_version(model_id: str, version_id: ObjectId):
    # Remove file
    fs.delete(version_id)
    _delete_predictions(model_id, version_id)


@router.post('')
def create_model(request: PostModelIn, token=Depends(validate_token)) -> PostModelOut:
    """
    Creates a new model entry with the given config.
    """
    _id = model_collection.insert_one({
        'name': '' if request.name is None else request.name,
        'config': request.config,
        'versions': [],
        'performances': {}
    }).inserted_id
    return PostModelOut(id=str(_id))


@router.get('')
def get_models():
    """
    Returns a list of all models in the database.
    """
    models = model_collection.find({}, ['name'])
    response = []
    for model in models:
        response.append({
            'id': str(model['_id']),
            'name': model['name']
        })
    return GetModelsOut(models=response)


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


@router.delete('/{model_id}')
def delete_model(model_id: str, token=Depends(validate_token)):
    model = model_collection.find_one({'_id': ObjectId(model_id)})
    if model is None:
        raise model_not_found_exception(model_id)

    # Delete versions and their predictions
    for version in model['versions']:
        _delete_version(model_id, version['id'])

    # Delete the model itself, including performances
    model_collection.delete_one({'_id': model_id})


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
    raise version_not_found_exception(version_id, model_id)


@router.delete('/{model_id}/versions/{version_id}')
def delete_version(model_id: str, version_id: str, token=Depends(validate_token)):
    model = _get_model(model_id, ['versions'])
    for version in model['versions']:
        if version_id == str(version['id']):
            _delete_version(model_id, version['id'])
            return
    raise version_not_found_exception(version_id, model_id)


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
        raise version_not_found_exception(version_id, model_id)
    classes = set()
    for issue_id, predicted_classes in request.predictions.items():
        predictions = {}
        for predicted_class in predicted_classes:
            predictions[predicted_class] = predicted_classes[predicted_class]
            classes.add(predicted_class)
        result = manual_labels_collection.update_one(
            {'_id': issue_id},
            {'$set': {
                'predictions': {f'{model_id}-{version_id}': predictions}
            }}
        )
        if result.matched_count != 1:
            raise issue_not_found_exception(issue_id)
    for class_ in classes:
        # Make sure the predictions are indexed for speed
        manual_labels_collection.create_index(f'predictions.{model_id}-{version_id}.{class_}.confidence')


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
    if request.ids is not None:
        remaining_ids = set(request.ids)
    for issue in issues:
        issue_id = issue.pop('_id')
        predictions[issue_id] = issue['predictions'][f'{model_id}-{version_id}']
        if request.ids is not None:
            remaining_ids.remove(issue_id)
    if request.ids is not None:
        for issue_id in remaining_ids:
            predictions[issue_id] = None
    return GetPredictionsOut(predictions=predictions)


@router.delete('/{model_id}/versions/{version_id}/predictions')
def delete_predictions(model_id: str, version_id: str, token=Depends(validate_token)):
    model = _get_model(model_id, ['versions'])
    for version in model['versions']:
        if version_id == str(version['id']):
            _delete_predictions(model_id, version['id'])
            return
    raise version_not_found_exception(version_id, model_id)


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


@router.delete('/{model_id}/performances/{performance_time}')
def delete_performance(model_id: str, performance_time: str, token=Depends(validate_token)):
    field = f'performances.{performance_time.replace(".", "_")}'
    result = model_collection.update_one(
        {
            '_id': ObjectId(model_id),
            field: {'$exists': True}
        },
        {
            '$unset': {field: ""}
        }
    )
    if result.modified_count != 1:
        if model_collection.find_one({'_id': ObjectId(model_id)}) is None:
            raise model_not_found_exception(model_id)
        raise performance_not_found_exception(performance_time, model_id)
