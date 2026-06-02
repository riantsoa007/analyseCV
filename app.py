from flask import Flask, redirect, url_for

from config import Config
from database import ensure_database_exists, init_db
from routes.cv_routes import cv_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db(app)
    app.register_blueprint(cv_bp)

    @app.route("/")
    def home():
        return redirect(url_for("cv.index"))

    return app


if __name__ == "__main__":
    ensure_database_exists()
    application = create_app()
    application.run(debug=True)
