import json
import logging
from odoo.tests import HttpCase, tagged

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', 'user_crud_api')
class TestUserCRUD(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Set up a target company and a mock center ID for testing boundaries
        cls.test_company = cls.env['res.company'].sudo().create({'name': 'CRUD Test Company'})
        cls.center_id = 42

        cls.base_url = '/api/odutech/users'
        cls.headers = {"Content-Type": "application/json"}

        # Shared tracking payload variables
        cls.user_email = "crud.user@odutech.com"
        cls.user_phone = "+254700000000"
        cls.user_name = "John Doe"

    def test_01_create_user_minimal_success(self):
        """ Test that a user can be created with ONLY email, phone, name, and company_id """
        payload = {
            "name": self.user_name,
            "email": self.user_email,
            "phone": self.user_phone,
            "company_id": self.test_company.id,
            "center_id": self.center_id  # Tracking association context
        }

        response = self.url_open(
            f"{self.base_url}/create",
            data=json.dumps({"params": payload}),
            headers=self.headers
        )

        self.assertEqual(response.status_code, 200)
        result = response.json().get('result', {})
        self.assertEqual(result.get('status'), 201)

        # Cache the created ID for documentation purposes
        user_id = result.get('data', {}).get('user_id')
        self.assertTrue(user_id, "Should return the newly created user's ID")

        # DB Verification: Check if record properties match expectations
        db_user = self.env['res.users'].sudo().browse(user_id)
        self.assertEqual(db_user.name, self.user_name)
        self.assertEqual(db_user.login, self.user_email)
        self.assertEqual(db_user.partner_id.phone, self.user_phone)

    def test_02_create_user_missing_required_fields(self):
        """ Test that missing any of the core 4 requirements drops a 400 error """
        incomplete_payload = {
            "name": self.user_name,
            "email": self.user_email,
            # 'phone' and 'company_id' are missing
        }

        response = self.url_open(
            f"{self.base_url}/create",
            data=json.dumps({"params": incomplete_payload}),
            headers=self.headers
        )

        result = response.json().get('result', {})
        self.assertEqual(result.get('status'), 400)
        self.assertIn("missing required fields", result.get('message', '').lower())

    def test_03_read_user_filtered_by_center(self):
        """ Test reading a user profile while filtering explicitly via centerId """
        # Pre-create an target user manually in DB
        test_user = self.env['res.users'].sudo().create({
            'name': 'Target Reader',
            'login': 'read.me@odutech.com',
            'company_id': self.test_company.id,
            'center_id': self.center_id  # Assuming your schema supports center_id
        })

        # Build query parameters reflecting the dynamic filter rules
        payload = {
            "user_id": test_user.id,
            "center_id": self.center_id
        }

        response = self.url_open(
            f"{self.base_url}/read",
            data=json.dumps({"params": payload}),
            headers=self.headers
        )

        result = response.json().get('result', {})
        self.assertEqual(result.get('status'), 200)
        self.assertEqual(result.get('data', {}).get('email'), 'read.me@odutech.com')

    def test_04_update_user_fields(self):
        """ Test updating mutable details (name, phone) on an existing record """
        test_user = self.env['res.users'].sudo().create({
            'name': 'Old Name',
            'login': 'update.me@odutech.com',
            'company_id': self.test_company.id,
            'center_id': self.center_id
        })

        payload = {
            "user_id": test_user.id,
            "center_id": self.center_id,
            "name": "Completely New Name",
            "phone": "+1234567890"
        }

        response = self.url_open(
            f"{self.base_url}/update",
            data=json.dumps({"params": payload}),
            headers=self.headers
        )

        result = response.json().get('result', {})
        self.assertEqual(result.get('status'), 200)
        self.assertEqual(test_user.name, "Completely New Name")
        self.assertEqual(test_user.partner_id.phone, "+1234567890")

    def test_05_delete_user_safely(self):
        """ Test archiving/deactivating a user record under the center scope """
        test_user = self.env['res.users'].sudo().create({
            'name': 'Trash Target',
            'login': 'delete.me@odutech.com',
            'company_id': self.test_company.id,
            'center_id': self.center_id
        })

        payload = {
            "user_id": test_user.id,
            "center_id": self.center_id
        }

        response = self.url_open(
            f"{self.base_url}/delete",
            data=json.dumps({"params": payload}),
            headers=self.headers
        )

        result = response.json().get('result', {})
        self.assertEqual(result.get('status'), 200)
        # Soft delete validation: Odoo users are usually deactivated (active=False) rather than deleted outright
        self.assertFalse(test_user.active, "User should be deactivated successfully.")