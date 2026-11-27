import unittest

from fastapi import HTTPException

from config import ADMIN_TOKEN
from main import _parse_remote_url, _safe_upload_path, app, require_admin


class SecurityTests(unittest.TestCase):
    def test_admin_token_dependency(self):
        with self.assertRaises(HTTPException):
            require_admin(None)
        self.assertIsNone(require_admin(ADMIN_TOKEN))

    def test_quick_update_routes_require_admin_token(self):
        protected_paths = {
            "/api/anime/{anime_id}/status",
            "/api/anime/{anime_id}/progress",
        }
        routes = {route.path: route for route in app.routes if hasattr(route, "dependant")}
        for path in protected_paths:
            dependencies = {dependency.call for dependency in routes[path].dependant.dependencies}
            self.assertIn(require_admin, dependencies)

    def test_upload_traversal_is_rejected(self):
        with self.assertRaises(HTTPException):
            _safe_upload_path("../admin_token.txt")

    def test_application_does_not_force_a_single_proxy_prefix(self):
        self.assertEqual(app.root_path, "")


class ProxySecurityTests(unittest.TestCase):
    def test_loopback_proxy_target_is_rejected(self):
        with self.assertRaises(HTTPException):
            _parse_remote_url("http://127.0.0.1/private.png")

    def test_non_http_proxy_target_is_rejected(self):
        with self.assertRaises(HTTPException):
            _parse_remote_url("file:///etc/passwd")


if __name__ == "__main__":
    unittest.main()
