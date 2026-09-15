"""Dev entrypoint: `python run.py` then open http://127.0.0.1:8000/"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=8000)
