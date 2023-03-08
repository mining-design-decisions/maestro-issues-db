from fastapi import FastAPI
from .routers import add_tags, issue_data, issue_ids, manual_labels, save_predictions, tags

app = FastAPI()

app.include_router(add_tags.router)
app.include_router(issue_data.router)
app.include_router(issue_ids.router)
app.include_router(manual_labels.router)
app.include_router(save_predictions.router)
app.include_router(tags.router)
