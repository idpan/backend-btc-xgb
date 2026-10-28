import unittest
import os
import sys
import json

# Add current dir to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app as app_flask
try:
    from app.app import app
except ImportError:
    app = app_flask
from db_manager import DatabaseManager
from werkzeug.security import generate_password_hash

class TestOpenAPICompliance(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Ensure test admin user exists in DB or mock user
        db = DatabaseManager()
        try:
            db.create_user("admin@example.com", generate_password_hash("admin123"), role="admin")
        except Exception:
            pass

    def test_01_login_and_auth(self):
        """Test POST /api/login"""
        res = self.client.post('/api/login', json={
            "email": "admin@example.com",
            "password": "admin123"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "success")
        self.assertIn("access_token", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["role"], "admin")

    def test_02_users_management(self):
        """Test GET /api/users, POST /api/create-user, DELETE /api/delete-user"""
        # Login to get token
        login_res = self.client.post('/api/login', json={
            "email": "admin@example.com",
            "password": "admin123"
        })
        token = login_res.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. GET /api/users
        res_users = self.client.get('/api/users', headers=headers)
        self.assertEqual(res_users.status_code, 200)
        self.assertEqual(res_users.get_json()["status"], "success")

        # 2. POST /api/create-user
        test_email = "testuser_temp@example.com"
        res_create = self.client.post('/api/create-user', headers=headers, json={
            "email": test_email,
            "password": "password123",
            "role": "user"
        })
        self.assertEqual(res_create.status_code, 200)
        self.assertEqual(res_create.get_json()["status"], "success")

        # 3. DELETE /api/delete-user
        res_delete = self.client.delete('/api/delete-user', headers=headers, json={
            "email": test_email
        })
        self.assertEqual(res_delete.status_code, 200)
        self.assertEqual(res_delete.get_json()["status"], "success")

    def test_03_prediction_latest(self):
        """Test GET /api/predict/latest"""
        login_res = self.client.post('/api/login', json={
            "email": "admin@example.com",
            "password": "admin123"
        })
        token = login_res.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.get('/api/predict/latest', headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("data", data)
        p_data = data["data"]
        self.assertIn("direction", p_data)
        self.assertIn("confidence_level", p_data)
        self.assertIn("target_date", p_data)
        self.assertIn("previous_close", p_data)

    def test_04_prediction_history(self):
        """Test GET /api/prediction-history"""
        res = self.client.get('/api/prediction-history')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsInstance(data, list)
        if len(data) > 0:
            item = data[0]
            self.assertIn("date", item)
            self.assertIn("prediction_direction", item)
            self.assertIn("actual_direction", item)
            self.assertIn("prediction_status", item)

    def test_05_data_lake(self):
        """Test GET /api/data-lake and GET /api/data-lake/{tanggal}"""
        # All rows
        res = self.client.get('/api/data-lake')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        sample_date = data[0]["tanggal"]

        # Single row
        res_single = self.client.get(f'/api/data-lake/{sample_date}')
        self.assertEqual(res_single.status_code, 200)
        row = res_single.get_json()
        self.assertEqual(row["tanggal"], sample_date)
        self.assertIn("fitur_21", row)

        # 404 test
        res_404 = self.client.get('/api/data-lake/1999-01-01')
        self.assertEqual(res_404.status_code, 404)

    def test_06_anatomi_model(self):
        """Test Anatomi endpoints: config, trees-meta, tree svg"""
        # 1. Config
        res_cfg = self.client.get('/api/anatomi/config')
        self.assertEqual(res_cfg.status_code, 200)
        cfg = res_cfg.get_json()
        self.assertIn("model_config", cfg)
        self.assertIn("base_score", cfg)

        # 2. Trees Meta
        res_meta = self.client.get('/api/anatomi/trees-meta')
        self.assertEqual(res_meta.status_code, 200)
        meta = res_meta.get_json()
        self.assertIsInstance(meta, list)
        self.assertEqual(len(meta), 100)

        # 3. Tree SVG (valid id 1)
        res_svg = self.client.get('/api/anatomi/trees/1')
        self.assertEqual(res_svg.status_code, 200)
        self.assertIn('image/svg+xml', res_svg.content_type)

        # 4. Tree SVG (invalid id 105 -> 404)
        res_svg_404 = self.client.get('/api/anatomi/trees/105')
        self.assertEqual(res_svg_404.status_code, 404)

if __name__ == '__main__':
    unittest.main()
