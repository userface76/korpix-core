"""KorPIX Policy Engine — 서버 실행"""
    import uvicorn
    from .engine import app

    if __name__ == "__main__":
        uvicorn.run(app, host="0.0.0.0", port=8001)
