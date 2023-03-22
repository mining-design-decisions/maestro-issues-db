from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.dependencies import manual_labels_collection, tags_collection
from app.routers.authentication import validate_token
from pymongo.errors import DuplicateKeyError

router = APIRouter(
    prefix='/tags',
    tags=['tags']
)


class Tag(BaseModel):
    tag: str
    description: str


class AddTagsIn(BaseModel):
    data: dict[str, list[str]]


@router.get('')
def get_tags():
    """
    Retrieve all unique tags in the database.
    """
    tags = tags_collection.find({})
    response = []
    for tag in tags:
        response.append({
            'name': tag['_id'],
            'description': tag['description'],
            'type': tag['type']
        })
    return {'tags': response}


@router.post('')
def create_tag(tag: Tag, token=Depends(validate_token)):
    """
    Create a new manual tag with the given description.
    """
    try:
        tags_collection.insert_one({
            '_id': tag.tag,
            'description': tag.description,
            'type': 'manual-tag'
        })
    except DuplicateKeyError:
        return HTTPException(
            status_code=409,
            detail=f'Tag {tag.tag} already exists'
        )


@router.post('/add-tags')
def add_tags(request: AddTagsIn, token=Depends(validate_token)):
    """
    Method for adding tags to issues in bulk. The tags and
    issue ids should be specified in the request body.
    """
    # Check if tags may be inserted
    tags = set()
    for issue_id in request.data:
        for tag in request.data[issue_id]:
            tags.add(tag)
    allowed_tags = tags_collection.find({'type': 'manual-tag'}, ['_id'])
    allowed_tags = set([tag['_id'] for tag in allowed_tags])
    if not tags - allowed_tags:
        return HTTPException(
            status_code=409,
            detail=f'The following tags may not be inserted: {list(tags - allowed_tags)}'
        )

    # Add tags
    not_found_keys = set()
    for issue_id in request.data:
        result = manual_labels_collection.update_one(
            {'_id': issue_id},
            {'$addToSet': {'tags': {'$each': request.data[issue_id]}}}
        )
        if result.matched_count == 0:
            not_found_keys.add(issue_id)
    if not_found_keys:
        raise HTTPException(
            status_code=404,
            detail=f'The following issues were not found: {list(not_found_keys)}'
        )
