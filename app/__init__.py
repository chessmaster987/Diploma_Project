from flask import Flask

def create_app():
    app = Flask(__name__)
    app.secret_key = "supersecretkey"

    # import routes
    from app.routes.teacher import teacher_bp
    app.register_blueprint(teacher_bp)

    return app