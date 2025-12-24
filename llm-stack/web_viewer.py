from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

os.makedirs("/app/reports", exist_ok=True)
app.mount("/", StaticFiles(directory="/app/reports", html=True), name="reports")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5050)