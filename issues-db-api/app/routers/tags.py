from fastapi import APIRouter, Query
from app.dependencies import manual_labels_collection, mongo_client

router = APIRouter()


@router.get('/tags')
def get_tags(filter_projects: bool = Query(default=False, alias='filter-projects')) -> list[str]:
    """
    Returns a list of all tags that are present in the database.
    Optionally the project tags can be filtered out.
    """
    # Find all tags in the db
    tags = list(manual_labels_collection.distinct('tags'))
    if filter_projects:
        # Filter the project tags
        projects = mongo_client['IssueLabels']['Projects'].find({})
        for project in projects:
            if project['_id'] in tags:
                tags.remove(project['_id'])
    return list(tags)
