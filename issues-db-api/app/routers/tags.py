from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.dependencies import manual_labels_collection
from app.routers.authentication import validate_token

router = APIRouter(
    prefix='/tags',
    tags=['tags']
)
example_request = {
    "example": {
        'data': {
            'ISSUE-ID-1': [
                'TAG-1',
                'TAG-2'
            ],
            'ISSUE-ID-2': [
                'TAG-3',
                'TAG-4'
            ]
        }
    }
}


class AddTagsIn(BaseModel):
    data: dict[str, list[str]]

    class Config:
        schema_extra = example_request


@router.post('/add-tags')
def add_tags(request: AddTagsIn, token=Depends(validate_token)):
    """
    Method for adding tags to issues in bulk. The tags and
    issue ids should be specified in the request body.
    """
    for issue_id in request.data:
        # Get the current list of tags of this issue
        issue = manual_labels_collection.find_one(
            {'_id': issue_id},
            ['tags']
        )
        tags = issue['tags']

        # Add the new tags
        for tag in request.data[issue_id]:
            # Only add non-existing tags
            if tag not in tags:
                tags.append(tag)

        # Update entry with the new tags
        manual_labels_collection.update_one(
            {'_id': issue_id},
            {'$set': {'tags': tags}}
        )
    # TODO: what to do with error handling here?
