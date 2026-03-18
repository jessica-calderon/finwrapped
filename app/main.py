from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="FinWrapped")

app.include_router(router)

@app.get("/")
def root():
    return {"status": "FinWrapped running"}