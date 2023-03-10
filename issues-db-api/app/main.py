from fastapi import FastAPI
from .routers import tags, issue_data, issue_ids, manual_labels,\
    models, issues, authentication

app = FastAPI()

app.include_router(tags.router)
app.include_router(issue_data.router)
app.include_router(issue_ids.router)
app.include_router(manual_labels.router)
app.include_router(models.router)
app.include_router(issues.router)
app.include_router(authentication.router)
