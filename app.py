
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import api


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://happy-flower-02c7dc30f.4.azurestaticapps.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router)

@app.get("/")
def root():
    return {"message": "FNOL Backend API"}
