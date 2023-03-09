from fastapi import APIRouter
from app.dependencies import manual_labels_collection

router = APIRouter()


@router.post('/issues/{issue_id}/mark-review')
def mark_review(issue_id: str):
    tags = manual_labels_collection.find_one(
        {'_id': issue_id},
        ['tags']
    )['tags']
    if 'has-label' in tags:
        # Issue cannot be used for training if it needs review
        tags.remove('has-label')
    if 'needs-review' not in tags:
        # Add the needs-review tag if it was non-existent
        tags.append('needs-review')
    manual_labels_collection.update_one(
        {'_id': issue_id},
        {'$set': {'tags': tags}}
    )


@router.post('/issues/{issue_id}/mark-training')
def mark_training(issue_id: str):
    tags = manual_labels_collection.find_one(
        {'_id': issue_id},
        ['tags']
    )['tags']
    if 'needs-review' in tags:
        # Issue is not allowed to need review if used for training
        tags.remove('needs-review')
    if 'has-label' not in tags:
        # Add the has-label tag if it was non-existent
        tags.append('has-label')
    manual_labels_collection.update_one(
        {'_id': issue_id},
        {'$set': {'tags': tags}}
    )
