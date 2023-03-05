from fastapi import APIRouter
from pydantic import BaseModel
from app.dependencies import manual_labels_collection

router = APIRouter()
example_request = {
    "example": {
        'data': {
            'ISSUE-1': [
                'TAG-1',
                'TAG-2'
            ],
            'ISSUE-2': [
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


@router.patch('/add-tags')
def add_tags(request: AddTagsIn):
    """
    Method for adding tags to issues in bulk. The tags and
    issue keys should be specified in the request body.
    """
    for key in request.data:
        # Get the current list of tags of this issue
        issue = manual_labels_collection.find_one(
            {'key': key},
            ['tags']
        )
        tags = issue['tags']

        # Add the new tags
        for tag in request.data[key]:
            # Only add non-existing tags
            if tag not in tags:
                tags.append(tag)

        # Update entry with the new tags
        manual_labels_collection.update_one(
            {'key': key},
            {'$set': {'tags': tags}}
        )
    # TODO: what to do with error handling here?
