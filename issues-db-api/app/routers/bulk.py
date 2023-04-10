from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.dependencies import manual_labels_collection, tags_collection
from app.routers.authentication import validate_token
from app.exceptions import illegal_tags_insertion_exception, issues_not_found_exception

router = APIRouter(
    prefix='/bulk',
    tags=['bulk']
)


class IssueTags(BaseModel):
    issue_id: str
    tags: list[str]


class AddTagsIn(BaseModel):
    data: list[IssueTags]


@router.post('/add-tags')
def add_tags_in_bulk(request: AddTagsIn, token=Depends(validate_token)):
    """
    Method for adding tags to issues in bulk. The tags and
    issue ids should be specified in the request body.
    """
    # Check if tags may be inserted
    tags = set()
    for issue in request.data:
        for tag in issue.tags:
            tags.add(tag)
    allowed_tags = tags_collection.find({'type': 'manual-tag'}, ['_id'])
    allowed_tags = set([tag['_id'] for tag in allowed_tags])
    if not tags.issubset(allowed_tags):
        raise illegal_tags_insertion_exception(list(tags - allowed_tags))

    # Add tags
    not_found_keys = set()
    for issue in request.data:
        result = manual_labels_collection.update_one(
            {'_id': issue.issue_id},
            {'$addToSet': {'tags': {'$each': issue.tags}}}
        )
        if result.matched_count == 0:
            not_found_keys.add(issue.issue_id)
    if not_found_keys:
        raise issues_not_found_exception(list(not_found_keys))
