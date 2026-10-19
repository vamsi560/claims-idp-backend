
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://happy-flower-02c7dc30f.4.azurestaticapps.net",
        "https://delightful-flower-05bbda40f.4.azurestaticapps.net",
        "https://claims-idp-byhphxaphvexd4ak.eastus-01.azurewebsites.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "FNOL Backend is running"}
