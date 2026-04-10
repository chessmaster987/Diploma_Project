from flask import Flask
from dotenv import load_dotenv

def create_app():
    load_dotenv()  

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.secret_key = "supersecretkey"

    from app.routes.teacher import teacher_bp
    app.register_blueprint(teacher_bp)

    return app