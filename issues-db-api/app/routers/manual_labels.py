import typing
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.dependencies import manual_labels_collection
from app.routers.authentication import validate_token
from app.routers.issues import _update_manual_label
from app.exceptions import issue_not_found_exception, manual_labels_not_found_exception, comment_not_found_exception
from bson import ObjectId

router = APIRouter(
    prefix='/manual-labels',
    tags=['manual-labels']
)


class ManualLabelsIn(BaseModel):
    ids: list[str]


class Label(typing.TypedDict):
    existence: bool | None
    property: bool | None
    executive: bool | None


class ManualLabelsOut(BaseModel):
    labels: dict[str, Label] = {}


class Comment(BaseModel):
    comment: str


class Comments(BaseModel):
    comments: dict[str, dict[str, str]]


def _update_comment(issue_id, comment_id, username, update):
    result = manual_labels_collection.update_one(
        {
            '_id': issue_id,
            f'comments.{comment_id}': {'$exists': True},
            f'comments.{comment_id}.author': {'$eq': username}
        },
        update
    )
    if result.modified_count != 1:
        if manual_labels_collection.find_one({'_id': issue_id}) is None:
            raise issue_not_found_exception(issue_id)
        else:
            raise comment_not_found_exception(comment_id, issue_id)


@router.post('', response_model=ManualLabelsOut)
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
        raise manual_labels_not_found_exception(list(ids))
    return ManualLabelsOut(labels=labels)


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
        raise issue_not_found_exception(issue_id)


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
        raise issue_not_found_exception(issue_id)
    if 'comments' not in issue or issue['comments'] is None:
        return Comments(comments={})
    return Comments(comments=issue['comments'])


@router.post('/{issue_id}/comments')
def add_comment(issue_id: str, request: Comment, token=Depends(validate_token)):
    """
    Adds a comment to the manual label of the given issue.
    """
    comment_id = ObjectId()
    _update_manual_label(
        issue_id,
        {
            '$set': {
                f'comments.{comment_id}': {
                    'author': token['username'],
                    'comment': request.comment
                }
            },
            '$addToSet': {'tags': token['username']}
        }
    )
    return {'id': str(comment_id)}


@router.patch('/{issue_id}/comments/{comment_id}')
def update_comment(issue_id: str, comment_id: str, request: Comment, token=Depends(validate_token)):
    _update_comment(
        issue_id,
        comment_id,
        token['username'],
        {'$set': {f'comments.{comment_id}.comment': request.comment}}
    )


@router.delete('/{issue_id}/comments/{comment_id}')
def delete_comment(issue_id: str, comment_id: str, token=Depends(validate_token)):
    _update_comment(
        issue_id,
        comment_id,
        token['username'],
        {'$unset': {f'comments.{comment_id}': ''}}
    )
