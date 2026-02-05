from fastapi import FastAPI
from . import api

app = FastAPI()
app.include_router(api.router)

@app.get("/")
def root():
    return {"message": "FNOL Backend API"}
