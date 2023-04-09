from fastapi import APIRouter, Depends
from app.dependencies import manual_labels_collection, tags_collection
from app.exceptions import issue_not_found_exception, illegal_tag_insertion_exception, tag_exists_for_issue_exception,\
    non_existing_tag_for_issue_exception
from app.routers.authentication import validate_token
from pydantic import BaseModel

router = APIRouter(
    prefix='/issues',
    tags=['issues']
)


class Tag(BaseModel):
    tag: str


class Tags(BaseModel):
    tags: list[str]


def _update_manual_label(issue_id: str, update: dict):
    result = manual_labels_collection.update_one(
        {'_id': issue_id},
        update,
    )
    if result.matched_count == 0:
        raise issue_not_found_exception(issue_id)


@router.post('/{issue_id}/mark-review')
def mark_review(issue_id: str, token=Depends(validate_token)):
    _update_manual_label(issue_id, {'$addToSet': {'tags': 'needs-review'}})


@router.post('/{issue_id}/finish-review')
def finish_review(issue_id: str, token=Depends(validate_token)):
    _update_manual_label(issue_id, {'$pull': {'tags': 'needs-review'}})


@router.get('/{issue_id}/tags', response_model=Tags)
def get_tags(issue_id: str):
    issue = manual_labels_collection.find_one({'_id': issue_id}, ['tags'])
    if issue is None:
        raise issue_not_found_exception(issue_id)
    return Tags(tags=issue['tags'])


@router.post('/{issue_id}/tags')
def add_tag(issue_id: str, request: Tag, token=Depends(validate_token)):
    allowed_tags = tags_collection.find({'type': 'manual-tag'}, ['_id'])
    allowed_tags = set([tag['_id'] for tag in allowed_tags])
    if request.tag not in allowed_tags:
        raise illegal_tag_insertion_exception(request.tag)
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


@router.delete('/{issue_id}/tags/{tag}')
def delete_tag(issue_id: str, tag: str, token=Depends(validate_token)):
    result = manual_labels_collection.update_one(
        {
            '_id': issue_id,
            'tags': tag
        },
        {
            '$pull': {'tags': tag}
        }
    )
    if result.modified_count != 1:
        if manual_labels_collection.find_one({'_id': issue_id}) is None:
            raise issue_not_found_exception(issue_id)
        raise non_existing_tag_for_issue_exception(tag, issue_id)
