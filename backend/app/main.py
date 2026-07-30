from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.mongo import load_seed_if_needed
from app.routes.restaurants import router as restaurants_router
from app.scheduler import shutdown_scheduler, start_scheduler

app = FastAPI(title="District Lead Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    load_seed_if_needed()
    start_scheduler(app)


@app.on_event("shutdown")
def shutdown_event():
    shutdown_scheduler()


app.include_router(restaurants_router)
