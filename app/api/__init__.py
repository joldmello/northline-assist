from flask import Flask

from app.api.cases import cases_bp


def register_api(app: Flask) -> None:
    app.register_blueprint(cases_bp, url_prefix="/api")
