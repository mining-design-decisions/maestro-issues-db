from fastapi import FastAPI
from app.routers import tags, issue_data, issue_ids, manual_labels,\
    models, issues, authentication, embeddings, ui, repos
from app.config import SSL_KEYFILE, SSL_CERTFILE
import uvicorn

app = FastAPI()

app.include_router(repos.router)
app.include_router(embeddings.router)
app.include_router(tags.router)
app.include_router(issue_data.router)
app.include_router(issue_ids.router)
app.include_router(manual_labels.router)
app.include_router(models.router)
app.include_router(issues.router)
app.include_router(authentication.router)
app.include_router(ui.router)

if __name__ == '__main__':
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=8000,
        ssl_keyfile=SSL_KEYFILE,
        ssl_certfile=SSL_CERTFILE
    )
