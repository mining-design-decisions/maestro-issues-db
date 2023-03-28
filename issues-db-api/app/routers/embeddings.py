from fastapi import APIRouter, Form, UploadFile, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.routers.authentication import validate_token
from app.dependencies import embeddings_fs, embeddings_collection
from bson import ObjectId
from app.util import read_file_in_chunks
from pydantic import BaseModel

router = APIRouter(
    prefix='/embeddings',
    tags=['embeddings']
)


class Config(BaseModel):
    config: dict


def _get_embedding(embedding_id: str, attributes: list[str]):
    embedding = embeddings_collection.find_one({'_id': ObjectId(embedding_id)}, attributes)
    if embedding is None:
        raise HTTPException(
            status_code=404,
            detail=f'Embedding "{embedding_id}" was not found'
        )
    return embedding


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


@router.post('')
def create_embedding(request: Config, token=Depends(validate_token)) -> dict[str, str]:
    """
    Create a new embedding with the given config and the uploaded file.
    """
    _id = embeddings_collection.insert_one({
        'config': request.config,
        'file_id': None
    })
    return {
        'embedding-id': str(_id)
    }


@router.post('/{embedding_id}')
def update_embedding(embedding_id: str, request: Config, token=Depends(validate_token)):
    """
    Update the config of the given embedding.
    """
    result = embeddings_collection.update_one({
        '_id': ObjectId(embedding_id),
        '$set': {'config': request.config}
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
    if embedding['file_id'] is not None:
        embeddings_fs.delete(embedding['file_id'])
    embeddings_collection.delete_one({'_id': ObjectId(embedding_id)})


@router.post('/{embedding_id}/file')
def update_file(embedding_id: str, file: UploadFile = Form(), token=Depends(validate_token)):
    """
    Upload embedding file for the given embedding.
    """
    embedding = _get_embedding(embedding_id, ['file_id'])
    if embedding['file_id'] is not None:
        # Delete existing embedding
        embeddings_fs.delete(embedding['file_id'])
    # Upload new embedding
    file_id = embeddings_fs.put(file.file, filename=file.filename)
    embeddings_collection.update_one(
        {'_id': ObjectId(embedding_id)},
        {'file_id': file_id}
    )


@router.get('/{embedding_id}/file')
def get_file(embedding_id: str):
    """
    Get the embedding file for the given embedding.
    """
    embedding = _get_embedding(embedding_id, ['file_id'])
    if embedding['file_id'] is None:
        # File does not exist
        raise HTTPException(
            status_code=404,
            detail=f'File for embedding "{embedding_id}" was not found'
        )
    mongo_file = embeddings_fs.get(embedding['file_id'])
    return StreamingResponse(read_file_in_chunks(mongo_file),
                             media_type='application/octet-stream')


@router.delete('/{embedding_id}/file')
def delete_file(embedding_id: str, token=Depends(validate_token)):
    """
    Delete embedding file for the given embedding.
    """
    embedding = _get_embedding(embedding_id, ['file_id'])
    if embedding['file_id'] is None:
        # File does not exist
        raise HTTPException(
            status_code=404,
            detail=f'File for embedding "{embedding_id}" was not found'
        )
    # Delete existing embedding
    embeddings_fs.delete(embedding['file_id'])
    embeddings_collection.update_one(
        {'_id': ObjectId(embedding_id)},
        {'file_id': None}
    )
