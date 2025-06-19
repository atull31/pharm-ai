from fastapi import FastAPI
from app.routes import auth_routes, record_routes
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.include_router(auth_routes.router, prefix="/auth")
app.include_router(record_routes.router, prefix="/records")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
def root():
    return RedirectResponse(url="/frontend/frontend-signup.html")