import hashlib
import hmac
import base64
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
REFS = ROOT / "reverse" / "references"
sys.path.insert(0, str(REFS))
sys.path.insert(0, str(ROOT))


class HttpLoginProbeTest(unittest.TestCase):
    def test_module_importable(self):
        import http_login_probe  # noqa: F401

    def test_md5_hex(self):
        from http_login_probe import md5_hex
        self.assertEqual(md5_hex("abc"), hashlib.md5(b"abc").hexdigest())

    def test_phone_secret(self):
        from http_login_probe import phone_secret
        phone = "13800138000"
        self.assertEqual(
            phone_secret("86", phone),
            hashlib.md5("8613800138000".encode()).hexdigest(),
        )

    def test_login_secret(self):
        from http_login_probe import login_secret
        phone = "13800138000"
        code = "123456"
        self.assertEqual(
            login_secret("86", phone, code),
            hashlib.md5("8613800138000#123456".encode()).hexdigest(),
        )

    def test_encrypt_phone_is_hex_and_pkcs1(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa

        from http_login_probe import encrypt_phone

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
        raw = encrypt_phone("86", "13800138000", key_pem)
        self.assertEqual(len(raw), 512)
        self.assertEqual(raw, raw.lower())
        int(raw, 16)
        decrypted = private_key.decrypt(bytes.fromhex(raw), padding.PKCS1v15())
        self.assertEqual(decrypted, b"8613800138000")

    def test_authorization_formula(self):
        from http_login_probe import authorization

        body = b"a=1"
        method = "POST"
        query = "sign_from=android&xid=1"
        ts = "123456789"
        expected_msg = "com.meelive.ingkee\n%s\nPOST\n123456789\n%s" % (
            base64.b64encode(hashlib.md5(body).digest()).decode().strip(),
            query,
        )
        expected = base64.b64encode(
            hmac.new(b"1ba5fb066d7e33d5", expected_msg.encode(), hashlib.sha1).digest()
        ).decode()
        self.assertEqual(
            authorization(body, method, query, ts),
            "InkeV1 OklL:" + expected,
        )

    def test_build_sms_body(self):
        from http_login_probe import build_sms_body

        body = build_sms_body({
            "phone": "ENCRYPTED",
            "region": "cn",
            "secret": "SECRET",
            "source": "login",
            "area_code": "86",
            "finger_list": {},
        })
        self.assertIn('"phone":"ENCRYPTED"', body)
        self.assertIn('"area_code":"86"', body)
        self.assertIn('"finger_list":{}', body)

    def test_build_login_body(self):
        from http_login_probe import build_login_body

        body = build_login_body({
            "request_id": "REQ",
            "phone": "ENCRYPTED",
            "code": "123456",
            "secret": "SECRET",
            "dev_name": "GooglePixel3",
            "finger_list": {},
            "link": 0,
            "visitor_uid": 0,
            "target_uid": 0,
        })
        self.assertIn('"request_id":"REQ"', body)
        self.assertIn('"code":"123456"', body)
        self.assertIn('"visitor_uid":0', body)

    def test_validate_login_result(self):
        from http_login_probe import md5_hex, validate_login_result

        uid = 12345678
        session = "TEST_SESSION_VALUE"
        secret = md5_hex(
            "IKLOGIN#RsDyXjH#%s#%s#MsJzKdY" % (session, uid)
        )
        self.assertTrue(validate_login_result({
            "uid": uid,
            "session": session,
            "secret": secret,
        }))
        self.assertFalse(validate_login_result({
            "uid": uid,
            "session": session,
            "secret": "bad",
        }))


if __name__ == "__main__":
    unittest.main()
