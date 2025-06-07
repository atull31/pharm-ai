from fastapi import FastAPI
from app.routes import auth_routes, record_routes
app = FastAPI()
app.include_router(auth_routes.router, prefix="/auth")
app.include_router(record_routes.router, prefix="/records")