from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash

from db_manager import DatabaseManager

users_bp = Blueprint('users', __name__)


@users_bp.route('/api/users', methods=['GET'])
@jwt_required()
def get_all_users():
    """Daftar semua user (admin only)"""
    current_user_email = get_jwt_identity()
    db = DatabaseManager()

    admin = db.get_user_by_email(current_user_email)
    if not admin or admin.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    users = db.get_all_users_list()
    return jsonify({"status": "success", "data": users}), 200


@users_bp.route('/api/create-user', methods=['POST'])
@jwt_required()
def create_new_user():
    """Buat user baru (admin only)"""
    current_user_email = get_jwt_identity()
    db = DatabaseManager()

    admin = db.get_user_by_email(current_user_email)
    if not admin or admin.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'user')

    if not email or not password:
        return jsonify({"status": "error", "message": "Email dan password wajib diisi"}), 400

    if role not in ['admin', 'user']:
        return jsonify({"status": "error", "message": "Role harus 'admin' atau 'user'"}), 400

    hashed_pw = generate_password_hash(password)

    if db.create_user(email, hashed_pw, role=role):
        return jsonify({"status": "success", "message": f"User {email} berhasil dibuat!"}), 200
    else:
        return jsonify({"status": "error", "message": "Gagal membuat user. Email mungkin sudah digunakan."}), 400


@users_bp.route('/api/delete-user', methods=['DELETE'])
@jwt_required()
def delete_user():
    """Hapus user (admin only)"""
    current_user_email = get_jwt_identity()
    db = DatabaseManager()

    admin = db.get_user_by_email(current_user_email)
    if not admin or admin.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    data = request.get_json() or {}
    email_to_delete = data.get('email')

    if not email_to_delete:
        return jsonify({"status": "error", "message": "Email wajib diisi"}), 400

    if email_to_delete == current_user_email:
        return jsonify({"status": "error", "message": "Tidak dapat menghapus diri sendiri"}), 400

    user_to_delete = db.get_user_by_email(email_to_delete)
    if not user_to_delete:
        return jsonify({"status": "error", "message": "User tidak ditemukan"}), 400

    if user_to_delete.get('role') == 'admin':
        all_users = db.get_all_users_list()
        admin_count = sum(1 for u in all_users if u.get('role') == 'admin')
        if admin_count <= 1:
            return jsonify({
                "status": "error",
                "message": "Gagal: Harus ada minimal 1 Admin di sistem."
            }), 400

    if db.delete_user(email_to_delete):
        return jsonify({"status": "success", "message": f"User {email_to_delete} berhasil dihapus!"}), 200
    else:
        return jsonify({"status": "error", "message": "Gagal menghapus user."}), 400