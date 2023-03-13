from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.dependencies import manual_labels_collection

router = APIRouter(
    prefix='/issue-ids',
    tags=['issue-ids']
)
example_request = {
    "example": {
        "filter": {
            "$and": [
                {"tags": {"$eq": "tag1"}},
                {"$or": [
                    {"tags": {"$ne": "tag2"}},
                    {"tags": {"$eq": "tag3"}}
                ]}
            ]
        }
    }
}


class IssueIdsIn(BaseModel):
    filter: dict

    class Config:
        schema_extra = example_request


class IssueIdsOut(BaseModel):
    ids: list[str] = []


@router.get('')
def get_issue_ids(request: IssueIdsIn) -> IssueIdsOut:
    """
    Returns the issue ids for which the issue tags match
    the provided filtering options. These filtering options are
    given in the body of the request.
    """
    issues = manual_labels_collection.find(
        request.filter,
        ['_id']
    )
    return IssueIdsOut(ids=[issue['_id'] for issue in issues])
