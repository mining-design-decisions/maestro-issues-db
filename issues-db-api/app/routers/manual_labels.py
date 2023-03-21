import typing
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.dependencies import manual_labels_collection
from app.routers.authentication import validate_token
from app.routers.issues import _update_manual_label

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


class Comment(BaseModel):
    comment: str


class Comments(BaseModel):
    comments: list[dict[str, str]]


@router.post('/{issue_id}')
def update_manual_label(issue_id: str, request: Label, token=Depends(validate_token)):
    """
    Update the manual label of the given issue.
    """
    result = manual_labels_collection.update_one(
        {'_id': issue_id},
        {
            '$set': request,
            '$addToSet': {'tags': {'$each': ['has-label', token['username']]}}
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


@router.post('/{issue_id}/comments')
def add_comment(issue_id: str, comment: Comment, token=Depends(validate_token)):
    """
    Adds a comment to the manual label of the given issue.
    """
    _update_manual_label(issue_id, {
        '$push': {'comments': {
            token['username']: comment.comment
        }},
        '$addToSet': {'tags': token['username']}
    })


@router.get('/{issue_id}/comments', response_model=Comments)
def get_comments(issue_id: str):
    """
    Gets the comments for the specified issue.
    """
    issue = manual_labels_collection.find_one(
        {'_id': issue_id},
        ['comments']
    )
    if issue is None:
        raise HTTPException(
            status_code=404,
            detail=f'Issue "{issue_id}" was not found'
        )
    if issue['comments'] is None:
        return Comments(comments=[])
    return Comments(comments=issue['comments'])
