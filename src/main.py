import os
import uvicorn
from fastapi import FastAPI
# Assuming you are running from the root folder
from src.routers import ping 

app = FastAPI(
    title="arXiv Paper Curator API",
    version="0.1.0",
)

# This matches the code in your ping.py

app.include_router(ping.router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)