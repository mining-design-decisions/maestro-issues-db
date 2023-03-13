from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.dependencies import manual_labels_collection
from app.routers.authentication import validate_token

router = APIRouter(
    prefix='/tags',
    tags=['tags']
)


class AddTagsIn(BaseModel):
    data: dict[str, list[str]]


@router.post('/add-tags')
def add_tags(request: AddTagsIn, token=Depends(validate_token)):
    """
    Method for adding tags to issues in bulk. The tags and
    issue ids should be specified in the request body.
    """
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
