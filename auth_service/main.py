from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.core.config import config
from app.core.tags_doc import tags_metadata
from app.middleware.logging import LoggingMiddleware
from app.api import auth, users, health



app = FastAPI(
    title=config.PROJECT_NAME,
    description=config.DESCRIPTION,
    openapi_tags=tags_metadata,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "docExpansion": "none",
        "filter": True,
        "displayRequestDuration": True,
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)


@app.on_event("startup")
async def startup_event():
    from app.services.auth_service import auth_service
    await auth_service.initialize()
    print("Auth service started")


@app.on_event("shutdown")
async def shutdown_event():
    from app.services.auth_service import auth_service
    await auth_service.cleanup()
    print("Auth service stopped")


app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/auth", tags=["Users"])
app.include_router(health.router, tags=["Health"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
