"""Northline Assist: layered Flask app for a roadside-assistance copilot.

Layers (outer -> inner):
    api / web  ->  services (business logic)  ->  models  ->  database (CSV store)
"""
from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify

from app.api import register_api
from app.config import Config
from app.database.store import Database
from app.services.container import Services
from app.services.exceptions import AppError
from app.web.routes import web_bp


def create_app(data_dir: str | None = None) -> Flask:
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY

    db = Database(data_dir or Config.DATA_DIR)
    services = Services(db)
    app.config["services"] = services

    register_api(app)
    app.register_blueprint(web_bp)

    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        return jsonify({"error": err.message}), err.status_code

    return app
