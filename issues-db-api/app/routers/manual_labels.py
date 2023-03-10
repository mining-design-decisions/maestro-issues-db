import typing
from fastapi import APIRouter
from pydantic import BaseModel
from app.dependencies import manual_labels_collection

router = APIRouter(
    prefix='/manual-labels',
    tags=['manual-labels']
)
example_request = {
    "example": {
        'ids': [
            'ISSUE-ID-1',
            'ISSUE-ID-2'
        ]
    }
}


class ManualLabelsIn(BaseModel):
    ids: list[str]

    class Config:
        schema_extra = example_request


class Label(typing.TypedDict):
    existence: bool
    property: bool
    executive: bool


class ManualLabelsOut(BaseModel):
    labels: dict[str, Label] = {}


@router.get('', response_model=ManualLabelsOut)
def manual_labels(request: ManualLabelsIn) -> ManualLabelsOut:
    """
    Returns the manual labels of the issue ids that were
    provided in the request body.
    """
    issues = manual_labels_collection.find(
        {
            '$and': [
                {'_id': {'$in': request.ids}},
                {'tags': 'has-label'},
            ]
        },
        ['existence', 'property', 'executive']
    )

    # Build and send response
    response = ManualLabelsOut()
    labels = {}
    for issue in issues:
        labels[issue['_id']] = {
            'existence': issue['existence'],
            'property': issue['property'],
            'executive': issue['executive']
        }
    response.labels = labels
    return response
