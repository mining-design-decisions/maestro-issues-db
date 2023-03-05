from fastapi import APIRouter
from app.dependencies import manual_labels_collection

router = APIRouter()


@router.get('/tags')
def tags() -> list[str]:
    """
    Returns a list of all tags that are present in the database.
    """
    tags = set()
    issues = manual_labels_collection.find({}, ['tags'])
    for issue in issues:
        for tag in issue['tags']:
            tags.add(tag)
    return tags
