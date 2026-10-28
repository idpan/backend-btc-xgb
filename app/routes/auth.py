from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash

from db_manager import DatabaseManager

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/login', methods=['POST'])
def login():
    """Login user/admin"""
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"status": "error", "message": "Email dan password wajib diisi"}), 200

    db = DatabaseManager()
    user = db.get_user_by_email(email)
    
    print(f"User: {user}")
    if user and check_password_hash(user['password'], password):
        access_token = create_access_token(identity=email)
        return jsonify({
            "status": "success",
            "access_token": access_token,
            "user": {
                "email": user['email'],
                "role": user['role']
            }
        }), 200

    return jsonify({"status": "error", "message": "Email atau password salah"}), 200


@auth_bp.route('/api/create-admin', methods=['GET'])
def create_admin():
    db = DatabaseManager()
    email = "admin@example.com"
    password = "admin123"
    hashed_pw = generate_password_hash(password)

    if db.create_user(email, hashed_pw, role='admin'):
        return jsonify({"status": "success", "message": f"Admin {email} berhasil dibuat!"}), 200
    else:
        return jsonify({"status": "error", "message": "Gagal membuat admin."}), 400