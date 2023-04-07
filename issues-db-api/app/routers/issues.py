from fastapi import APIRouter, Depends
from app.dependencies import manual_labels_collection
from app.exceptions import issue_not_found_exception
from app.routers.authentication import validate_token

router = APIRouter(
    prefix='/issues',
    tags=['issues']
)


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
def mark_training(issue_id: str, token=Depends(validate_token)):
    _update_manual_label(issue_id, {'$pull': {'tags': 'needs-review'}})
