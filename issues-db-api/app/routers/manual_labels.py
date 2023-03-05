import typing
from fastapi import APIRouter
from pydantic import BaseModel
from app.dependencies import manual_labels_collection

router = APIRouter()
example_request = {
    "example": {
        'keys': [
            'ISSUE-1',
            'ISSUE-2'
        ]
    }
}


class ManualLabelsIn(BaseModel):
    keys: list[str]

    class Config:
        schema_extra = example_request


class Label(typing.TypedDict):
    existence: bool
    property: bool
    executive: bool


class ManualLabelsOut(BaseModel):
    labels: dict[str, Label] = {}


@router.get('/manual-labels', response_model=ManualLabelsOut)
def manual_labels(request: ManualLabelsIn) -> ManualLabelsOut:
    """
    Returns the manual labels of the issue keys that were
    provided in the request body.
    TODO: Fix input validation
    """
    issues = manual_labels_collection.find(
        {
            '$and': [
                {'key': {'$in': request.keys}},
                {'tags': 'has-label'},
            ]
        },
        ['key', 'existence', 'property', 'executive']
    )

    # Build and send response
    response = ManualLabelsOut()
    labels = {}
    for issue in issues:
        labels[issue['key']] = {
            'existence': issue['existence'],
            'property': issue['property'],
            'executive': issue['executive']
        }
    response.labels = labels
    return response
