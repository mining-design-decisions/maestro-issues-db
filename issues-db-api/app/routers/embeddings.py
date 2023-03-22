from fastapi import APIRouter, Form, UploadFile, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.routers.authentication import validate_token
from app.dependencies import embeddings_fs, embeddings_collection
import json
from bson import ObjectId
from app.util import read_file_in_chunks

router = APIRouter(
    prefix='/embeddings',
    tags=['embeddings']
)


def _get_embedding(embedding_id: str, attributes: list[str]):
    embedding = embeddings_collection.find_one({'_id': ObjectId(embedding_id)}, attributes)
    if embedding is None:
        raise HTTPException(
            status_code=404,
            detail=f'Embedding "{embedding_id}" was not found'
        )
    return embedding


@router.post('')
def create_embedding(config: str = Form(),
                     file: UploadFile = Form(),
                     token=Depends(validate_token)) -> dict[str, str]:
    """
    Create a new embedding with the given config and the uploaded file.
    """
    file_id = embeddings_fs.put(file.file, filename=file.filename)
    try:
        parsed_config = json.loads(config)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=422,
            detail=f'Failed to parse the config: {e}'
        )
    _id = embeddings_collection.insert_one({
        'config': parsed_config,
        'file_id': file_id
    })
    return {
        'embedding-id': str(_id)
    }


@router.get('')
def get_embeddings() -> dict[str, dict]:
    """
    Get all embeddings and their config.
    """
    embeddings = embeddings_collection.find({}, ['config'])
    response = {}
    for embedding in embeddings:
        response[str(embedding['_id'])] = embeddings['config']
    return response


@router.get('/{embedding_id}')
def get_embedding(embedding_id: str):
    embedding = _get_embedding(embedding_id, ['file_id'])
    mongo_file = embeddings_fs.get(embedding['file_id'])
    return StreamingResponse(read_file_in_chunks(mongo_file),
                             media_type='application/octet-stream')


@router.post('/{embedding_id}')
def update_embedding(embedding_id: str, file: UploadFile = Form(), token=Depends(validate_token)):
    """
    Update the embedding file with the uploaded file.
    """
    embedding = _get_embedding(embedding_id, ['file_id'])
    embeddings_fs.delete(embedding['file_id'])
    file_id = embeddings_fs.put(file.file, filename=file.filename)
    result = embeddings_collection.update_one({
        '_id': ObjectId(embedding_id),
        '$set': {'file_id': file_id}
    })
    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f'Embedding "{embedding_id}" was not found'
        )


@router.delete('/{embedding_id}')
def delete_embedding(embedding_id: str, token=Depends(validate_token)):
    """
    Delete the embedding with the given embedding id
    """
    embedding = _get_embedding(embedding_id, ['file_id'])
    embeddings_fs.delete(embedding['file_id'])
    embeddings_fs.delete_one({'_id': ObjectId(embedding_id)})
