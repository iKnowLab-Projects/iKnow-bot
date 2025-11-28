from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# 리포트 저장소 생성 및 마운트
os.makedirs("/app/reports", exist_ok=True)
app.mount("/", StaticFiles(directory="/app/reports", html=True), name="reports")

if __name__ == "__main__":
    import uvicorn
    # 도커 내부 포트 8000 (외부에는 5050으로 매핑됨)
    uvicorn.run(app, host="0.0.0.0", port=8000)