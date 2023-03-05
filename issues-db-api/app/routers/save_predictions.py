from fastapi import APIRouter
from pydantic import BaseModel
from app.dependencies import mongo_client

router = APIRouter()
example_request = {
    "example": {
        'model': 'MODEL-1',
        'predictions': {
            'ISSUE-1': {
                'existence': True,
                'property': False,
                'executive': False
            },
            'ISSUE-2': {
                'existence': False,
                'property': True,
                'executive': False
            }
        }
    }
}


class SavePredictionsIn(BaseModel):
    model: str
    predictions: dict[str, dict[str, bool]]

    class Config:
        schema_extra = example_request


@router.put('/save-predictions')
def save_predictions(request: SavePredictionsIn):
    """
    Saves the given predictions for the given model.
    """
    model_collection = mongo_client['PredictedLabels'][request.model]
    for key in request.predictions:
        model_collection.insert_one({
            'key': key,
            'existence': request.predictions[key]['existence'],
            'property': request.predictions[key]['property'],
            'executive': request.predictions[key]['executive']
        })
