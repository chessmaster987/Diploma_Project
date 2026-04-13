import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask


def create_app():
    load_dotenv()

    package_dir = Path(__file__).resolve().parent
    project_dir = package_dir.parent

    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("SECRET_KEY is required. Set it in the environment or .env file.")

    app = Flask(
        __name__,
        template_folder=str(package_dir / "templates"),
        static_folder=str(project_dir / "static"),
    )
    app.secret_key = secret_key

    from app.routes.auth import auth_bp
    from app.routes.student import student_bp
    from app.routes.teacher import teacher_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp)

    return app
