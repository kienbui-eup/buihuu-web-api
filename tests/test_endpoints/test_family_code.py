"""Kiểm thử mã dòng họ: POST /api/token/family-code/ và hàm chuẩn hóa."""

import unittest
from unittest.mock import patch

from flask_jwt_extended.utils import decode_token

from gramps_webapi.api.family_code import (
    MIN_CODE_LENGTH,
    clear_cache,
    normalize_code,
)
from gramps_webapi.auth import get_guid
from gramps_webapi.auth.const import ROLE_GUEST, ROLE_OWNER

from . import BASE_URL, TEST_USERS, get_test_client
from .util import fetch_header

URL = BASE_URL + "/token/family-code/"


class TestNormalizeCode(unittest.TestCase):
    """Chuẩn hóa mã: bỏ dấu, bỏ khoảng trắng, chữ thường. Tên trong đây là bịa."""

    def test_vietnamese_marks(self):
        self.assertEqual(normalize_code("Trần Văn Ví Dụ"), "tranvanvidu")
        self.assertEqual(normalize_code("Đặng Thị Ươm"), "dangthiuom")

    def test_case_spaces_punctuation(self):
        self.assertEqual(normalize_code("TRẦN  văn-Ví dụ "), "tranvanvidu")
        self.assertEqual(normalize_code("tranvanvidu"), "tranvanvidu")

    def test_empty(self):
        self.assertEqual(normalize_code(""), "")
        self.assertEqual(normalize_code(None), "")
        self.assertEqual(normalize_code(" ?… "), "")


class TestTokenFamilyCode(unittest.TestCase):
    """Cấp token khách khi mã là họ tên một người trong cây mẫu."""

    @classmethod
    def setUpClass(cls):
        cls.client = get_test_client()
        cls.app = cls.client.application
        cls.app.config["FAMILY_CODE_USERNAME"] = TEST_USERS[ROLE_GUEST]["name"]
        # Lấy họ tên một người bất kỳ trong cây mẫu qua API, không ghi cứng.
        headers = fetch_header(cls.client)
        rv = cls.client.get(BASE_URL + "/people/?page=1&pagesize=20", headers=headers)
        assert rv.status_code == 200
        for person in rv.json:
            name = person["primary_name"]
            surname = " ".join(
                s["surname"] for s in name["surname_list"] if s.get("surname")
            )
            full_name = f"{surname} {name['first_name']}".strip()
            if len(normalize_code(full_name)) >= MIN_CODE_LENGTH:
                cls.full_name = full_name
                break
        else:
            raise AssertionError("Không tìm được tên đủ dài trong cây mẫu")

    def setUp(self):
        clear_cache()

    def test_missing_body(self):
        rv = self.client.post(URL)
        self.assertEqual(rv.status_code, 422)

    def test_wrong_code(self):
        rv = self.client.post(URL, json={"code": "khongcoaitenthenay"})
        self.assertEqual(rv.status_code, 403)

    def test_too_short_code(self):
        rv = self.client.post(URL, json={"code": "a"})
        self.assertEqual(rv.status_code, 403)

    def test_correct_code_gives_guest_tokens(self):
        rv = self.client.post(URL, json={"code": self.full_name})
        self.assertEqual(rv.status_code, 200)
        self.assertIn("access_token", rv.json)
        self.assertIn("refresh_token", rv.json)
        with self.app.app_context():
            claims = decode_token(rv.json["access_token"])
            self.assertEqual(
                claims["sub"], str(get_guid(TEST_USERS[ROLE_GUEST]["name"]))
            )
            self.assertIn("tree", claims)
            self.assertNotIn("EditObject", claims["permissions"])

    def test_code_ignores_case_marks_and_spaces(self):
        joined = normalize_code(self.full_name).upper()
        rv = self.client.post(URL, json={"code": f"  {joined} "})
        self.assertEqual(rv.status_code, 200)
        given_first = " ".join(reversed(self.full_name.split(" ", 1)))
        rv = self.client.post(URL, json={"code": given_first})
        self.assertEqual(rv.status_code, 200)

    def test_disabled_when_no_username(self):
        with patch.dict(self.app.config, {"FAMILY_CODE_USERNAME": ""}):
            rv = self.client.post(URL, json={"code": self.full_name})
        self.assertEqual(rv.status_code, 404)

    def test_refuses_editing_account(self):
        owner = TEST_USERS[ROLE_OWNER]["name"]
        with patch.dict(self.app.config, {"FAMILY_CODE_USERNAME": owner}):
            rv = self.client.post(URL, json={"code": self.full_name})
        self.assertEqual(rv.status_code, 503)

    def test_missing_account(self):
        with patch.dict(self.app.config, {"FAMILY_CODE_USERNAME": "khongco"}):
            rv = self.client.post(URL, json={"code": self.full_name})
        self.assertEqual(rv.status_code, 503)
