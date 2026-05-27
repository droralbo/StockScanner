"""Entry point — `uvicorn src.main:app --host 0.0.0.0 --port $PORT`"""
from src.web.app import create_app

app = create_app()
