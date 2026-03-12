from __future__ import annotations

import base64
import json
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request


class ServiceAccountTokenError(RuntimeError):
    pass


def fetch_service_account_token(service_account_json_b64: str, scope: str) -> str:
    if not service_account_json_b64:
        raise ServiceAccountTokenError("Missing service account JSON.")

    credentials = json.loads(base64.b64decode(service_account_json_b64).decode("utf-8"))
    header = _b64url_json({"alg": "RS256", "typ": "JWT"})
    now = int(time.time())
    payload = _b64url_json(
        {
            "iss": credentials["client_email"],
            "scope": scope,
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        }
    )
    signing_input = f"{header}.{payload}"
    signature = _sign_with_openssl(credentials["private_key"], signing_input.encode("utf-8"))
    assertion = f"{signing_input}.{signature}"

    body = urllib.parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8") or "{}")
    token = str(payload.get("access_token", "")).strip()
    if not token:
        raise ServiceAccountTokenError("Token exchange did not return an access token.")
    return token


def _b64url_json(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _sign_with_openssl(private_key: str, payload: bytes) -> str:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=True) as key_file:
        key_file.write(private_key)
        key_file.flush()
        process = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", key_file.name],
            input=payload,
            capture_output=True,
            check=False,
        )
    if process.returncode != 0:
        raise ServiceAccountTokenError(process.stderr.decode("utf-8", errors="ignore").strip() or "OpenSSL sign failed.")
    return base64.urlsafe_b64encode(process.stdout).decode("ascii").rstrip("=")
