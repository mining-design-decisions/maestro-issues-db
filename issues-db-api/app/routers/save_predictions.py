import typing
from fastapi import APIRouter
from pydantic import BaseModel
from app.dependencies import mongo_client

router = APIRouter()
example_request = {
    "example": {
        'model': 'MODEL-1',
        'predictions': {
            'ISSUE-ID-1': {
                "existence": {
                    "prediction": True,
                    "probability": 0.42
                },
                "property": {
                    "prediction": False,
                    "probability": 0.42
                },
                "executive": {
                    "prediction": False,
                    "probability": 0.42
                }
            },
            'ISSUE-ID-2': {
                "existence": {
                    "prediction": False,
                    "probability": 0.42
                },
                "property": {
                    "prediction": True,
                    "probability": 0.42
                },
                "executive": {
                    "prediction": False,
                    "probability": 0.42
                }
            },
        }
    }
}


class SavePredictionsIn(BaseModel):
    model: str
    predictions: dict[str, dict[str, dict[str, typing.Any]]]

    class Config:
        schema_extra = example_request


@router.put('/save-predictions')
def save_predictions(request: SavePredictionsIn):
    """
    Saves the given predictions for the given model.
    """
    if request.model in ['ManualLabels', 'Projects']:
        raise ValueError(f'{request.model} is a reserved name')
    model_collection = mongo_client['IssueLabels'][request.model]
    for issue_id, predicted_classes in request.predictions.items():
        issue = {'_id': issue_id}
        for predicted_class in predicted_classes:
            issue[predicted_class] = predicted_classes[predicted_class]
        model_collection.insert_one(issue)
