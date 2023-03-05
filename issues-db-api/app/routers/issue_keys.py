from fastapi import APIRouter
from pydantic import BaseModel
from app.dependencies import manual_labels_collection

router = APIRouter()
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


def validate_filter(query, *, __force_eq=False):
    if not isinstance(query, dict):
        raise _invalid_query(query)
    if len(query) != 1:
        raise _invalid_query(query, 'expected exactly 1 element')
    match query:
        case {'$and': operands}:
            if __force_eq:
                raise _invalid_query(query, '$and was not expected here')
            if not isinstance(operands, list):
                raise _invalid_query(query, '$and operand must be a list')
            for o in operands:
                validate_filter(o)
        case {'$or': operands}:
            if __force_eq:
                raise _invalid_query(query, '$or was not expected here')
            if not isinstance(operands, list):
                raise _invalid_query(query, '$or operand must be a list')
            for o in operands:
                validate_filter(o)
        case {'tags': operand}:
            if not isinstance(operand, dict):
                raise _invalid_query('tag operand must be an object')
            validate_filter(operand, __force_eq=True)
        case {'project': operand}:
            if not isinstance(operand, dict):
                raise _invalid_query('project operand must be an object')
            validate_filter(operand, __force_eq=True)
        case {'$eq': operand}:
            if not __force_eq:
                raise _invalid_query(query, '$eq not expected here')
            if not isinstance(operand, str):
                raise _invalid_query(query, '$eq operand must be a string')
        case {'$ne': operand}:
            if not __force_eq:
                raise _invalid_query(query, '$ne not expected here')
            if not isinstance(operand, str):
                raise _invalid_query(query, '$ne operand must be a string')
        case _ as x:
            raise _invalid_query(x, 'Invalid operation')


def _invalid_query(q, msg=None):
    if msg is not None:
        return ValueError(f'Invalid (sub-)query ({msg}): {q}')
    return ValueError(f'Invalid (sub-)query: {q}')


class IssueKeysIn(BaseModel):
    filter: dict

    class Config:
        schema_extra = example_request


class IssueKeysOut(BaseModel):
    keys: list[str] = []


@router.get('/issue-keys')
def issue_keys(request: IssueKeysIn) -> IssueKeysOut:
    """
    Returns the issue keys for which the issue tags match
    the provided filtering options. These filtering options are
    given in the body of the request.
    TODO: Fix input validation
    """
    validate_filter(request.filter)
    issues = manual_labels_collection.find(
        request.filter,
        ['key']
    )
    response = IssueKeysOut()
    response.keys = [issue['key'] for issue in issues]
    print(response.keys)
    return response
