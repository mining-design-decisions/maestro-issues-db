from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.dependencies import manual_labels_collection, tags_collection
from app.routers.authentication import validate_token
from pymongo.errors import DuplicateKeyError
from app.exceptions import tag_exists_exception, illegal_tags_insertion_exception, issues_not_found_exception,\
    issue_not_found_exception, tag_exists_for_issue_exception, non_existing_tag_for_issue_exception

router = APIRouter(
    prefix='/tags',
    tags=['tags']
)


class NewTag(BaseModel):
    tag: str
    description: str


class AddTagsIn(BaseModel):
    data: dict[str, list[str]]


class Tag(BaseModel):
    tag: str


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
def create_tag(tag: NewTag, token=Depends(validate_token)):
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
        raise tag_exists_exception(tag.tag)


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
    if not tags.issubset(allowed_tags):
        raise illegal_tags_insertion_exception(list(tags - allowed_tags))

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
        raise issues_not_found_exception(list(not_found_keys))


@router.post('/{issue_id}')
def add_tag(issue_id: str, request: Tag, token=Depends(validate_token)):
    result = manual_labels_collection.update_one(
        {
            '_id': issue_id,
            'tags': {'$ne': request.tag}
        },
        {
            '$addToSet': {'tags': request.tag}
        }
    )
    if result.modified_count != 1:
        if manual_labels_collection.find_one({'_id': issue_id}) is None:
            raise issue_not_found_exception(issue_id)
        raise tag_exists_for_issue_exception(request.tag, issue_id)


@router.delete('/{issue_id}')
def delete_tag(issue_id: str, request: Tag, token=Depends(validate_token)):
    result = manual_labels_collection.update_one(
        {
            '_id': issue_id,
            'tags': request.tag
        },
        {
            '$pull': {'tags': request.tag}
        }
    )
    if result.modified_count != 1:
        if manual_labels_collection.find_one({'_id': issue_id}) is None:
            raise issue_not_found_exception(issue_id)
        raise non_existing_tag_for_issue_exception(request.tag, issue_id)
