from fastapi import FastAPI

from app.routes import router as api_router

app = FastAPI(title="Simple Marketing Event Service")
app.include_router(api_router)
