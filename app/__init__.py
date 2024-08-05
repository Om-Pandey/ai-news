from flask import Flask
from .config import Config
from .db import init_app
from .auth import bp as auth_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_app(app)
    app.register_blueprint(auth_bp)

    return app
