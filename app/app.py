import os
from datetime import timedelta
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv

# Import seluruh Blueprint
from routes.auth import auth_bp
from routes.users import users_bp
from routes.prediction import prediction_bp

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

app = Flask(__name__)
CORS(app)

# Konfigurasi JWT
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "btc-predict-v2-secret-key-2026")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)
jwt = JWTManager(app)


# Custom JWT Error Handlers
@jwt.unauthorized_loader
def unauthorized_response(callback):
    return jsonify({"status": "error", "message": "Token tidak ada / tidak valid"}), 401


@jwt.invalid_token_loader
def invalid_token_response(callback):
    return jsonify({"status": "error", "message": "Token tidak ada / tidak valid"}), 401


@jwt.expired_token_loader
def expired_token_response(jwt_header, jwt_payload):
    return jsonify({"status": "error", "message": "Token telah kadaluarsa"}), 401


# Root Endpoint
@app.route('/')
def index():
    return jsonify({"status": "success", "message": "BitcoinPredict-V2 API Server is running"})


# Register All Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(prediction_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)