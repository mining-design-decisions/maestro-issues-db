import typing
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.dependencies import manual_labels_collection

router = APIRouter(
    prefix='/manual-labels',
    tags=['manual-labels']
)


class ManualLabelsIn(BaseModel):
    ids: list[str]


class Label(typing.TypedDict):
    existence: bool
    property: bool
    executive: bool


class ManualLabelsOut(BaseModel):
    labels: dict[str, Label] = {}


@router.post('/{issue_id}')
def update_manual_label(issue_id: str, request: Label):
    """
    Update the manual label of the given issue.
    """
    result = manual_labels_collection.update_one(
        {'_id': issue_id},
        {
            '$set': request,
            '$addToSet': {'tags': 'has-label'}
        }
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f'Issue "{issue_id}" was not found'
        )


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
    labels = {}
    ids = set(request.ids)
    for issue in issues:
        ids.remove(issue['_id'])
        labels[issue['_id']] = {
            'existence': issue['existence'],
            'property': issue['property'],
            'executive': issue['executive']
        }
    if ids:
        raise HTTPException(
            status_code=404,
            detail=f'The following issues do not have a manual label: {list(ids)}'
        )
    return ManualLabelsOut(labels=labels)
