from fastapi import FastAPI
from src.api.proofpacks_api import router as proofpacks_router

app = FastAPI(title="ChainBridge ProofPack API", version="1.0.0")
app.include_router(proofpacks_router)
