import base64
import json
import os
import secrets
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import requests

AUTHORIZE_URL = "https://login.xero.com/identity/connect/authorize"
TOKEN_URL = "https://identity.xero.com/connect/token"
CONNECTIONS_URL = "https://api.xero.com/connections"
SECRETS_FILE = "xero_secrets.json"


def _env(*names: str) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return None


def load_config() -> Dict[str, object]:
    client_id = _env("client_id", "CLIENT_ID", "XERO_CLIENT_ID")
    client_secret = _env("client_secret", "CLIENT_SECRET", "XERO_CLIENT_SECRET")
    redirect_uri = _env("redirect_uri", "REDIRECT_URI", "XERO_REDIRECT_URI")
    scopes_raw = _env("scopes", "SCOPES", "XERO_SCOPES")

    missing = []
    if not client_id:
        missing.append("client_id")
    if not client_secret:
        missing.append("client_secret")
    if not redirect_uri:
        missing.append("redirect_uri")
    if not scopes_raw:
        missing.append("scopes")
    if missing:
        print("Missing required environment variables:", ", ".join(missing))
        print("Set at least these env vars: client_id, client_secret, redirect_uri, scopes")
        sys.exit(1)

    # Support space-separated scopes (Xero format), and tolerate commas.
    scopes = [s for s in scopes_raw.replace(",", " ").split() if s]
    if "offline_access" not in scopes:
        scopes.append("offline_access")
        print("[info] Added required scope: offline_access")

    parsed = urlparse(redirect_uri)
    if parsed.scheme.lower() != "http":
        print("This script starts a minimal HTTP listener, so redirect_uri must use http://")
        print(f"Current redirect_uri: {redirect_uri}")
        sys.exit(1)
    if not parsed.hostname:
        print(f"Invalid redirect_uri (missing hostname): {redirect_uri}")
        sys.exit(1)

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "scopes": scopes,
    }


def build_authorize_url(client_id: str, redirect_uri: str, scopes: List[str], state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed_req = urlparse(self.path)
        expected_path = getattr(self.server, "expected_path", "/")

        if parsed_req.path != expected_path:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Not found.")
            return

        query = parse_qs(parsed_req.query)
        self.server.oauth_result = {
            "code": (query.get("code") or [None])[0],
            "state": (query.get("state") or [None])[0],
            "error": (query.get("error") or [None])[0],
            "error_description": (query.get("error_description") or [None])[0],
        }

        ok = self.server.oauth_result.get("code") and not self.server.oauth_result.get("error")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if ok:
            body = (
                "<html><body><h3>Xero auth received.</h3>"
                "<p>You can close this tab and return to the terminal.</p></body></html>"
            )
        else:
            body = (
                "<html><body><h3>Xero auth returned an error.</h3>"
                "<p>You can close this tab and check the terminal for details.</p></body></html>"
            )
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args) -> None:
        # Silence default request logging.
        return


def wait_for_callback(redirect_uri: str, timeout_seconds: int = 300) -> Dict[str, Optional[str]]:
    parsed = urlparse(redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 80
    path = parsed.path or "/"

    server = HTTPServer((host, port), OAuthCallbackHandler)
    server.timeout = 1
    server.expected_path = path
    server.oauth_result = None

    print(f"[info] Listening for OAuth callback on http://{host}:{port}{path}")

    deadline = time.time() + timeout_seconds
    try:
        while time.time() < deadline:
            server.handle_request()
            if server.oauth_result is not None:
                return server.oauth_result
    finally:
        server.server_close()

    raise TimeoutError(f"Timed out waiting for callback after {timeout_seconds} seconds.")


def exchange_code_for_tokens(client_id: str, client_secret: str, redirect_uri: str, code: str) -> requests.Response:
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    return requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)


def print_token_failure_help(config: Dict[str, object], response: requests.Response) -> None:
    print("\nToken request failed.")
    print(f"HTTP {response.status_code}")
    print("Response body:")
    print(response.text[:4000] or "<empty>")
    print("\nChecklist:")
    print(f"- redirect_uri must match Xero app settings exactly: {config['redirect_uri']}")
    print("- The authorization code is single-use and expires quickly; restart the script for a fresh code.")
    print("- Scopes must include offline_access so Xero returns a refresh token.")
    print(f"- Current scopes: {' '.join(config['scopes'])}")
    print("- Ensure you are using the same Xero app/client_id that generated the auth URL.")


def fetch_tenant_id(access_token: str) -> Optional[str]:
    r = requests.get(
        CONNECTIONS_URL,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=20,
    )
    r.raise_for_status()
    connections = r.json()

    if not connections:
        print("\nNo Xero tenant connection found for this authorization.")
        print("Open Xero and complete the app connection to an organisation, then run this script again.")
        return None

    if len(connections) > 1:
        print("\nMultiple tenant connections found; using the first returned by Xero:")
        for c in connections:
            print(f"- {c.get('tenantName', '<unknown>')} | {c.get('tenantId')}")

    tenant_id = connections[0].get("tenantId")
    print(f"\nSelected tenant_id: {tenant_id}")
    return tenant_id


def save_secrets_file(payload: Dict[str, object]) -> None:
    existing: Dict[str, object] = {}
    if os.path.exists(SECRETS_FILE):
        try:
            with open(SECRETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    existing = data
        except Exception:
            existing = {}

    existing.update(payload)
    with open(SECRETS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def main() -> None:
    config = load_config()
    client_id = str(config["client_id"])
    client_secret = str(config["client_secret"])
    redirect_uri = str(config["redirect_uri"])
    scopes = list(config["scopes"])

    print("Important:")
    print(f"- Ensure redirect_uri matches Xero app settings exactly: {redirect_uri}")
    print("- Ensure scopes include offline_access so refresh tokens are granted.")

    state = secrets.token_urlsafe(24)
    auth_url = build_authorize_url(client_id, redirect_uri, scopes, state)

    print("\nOpen this URL to authorize the app:")
    print(auth_url)
    try:
        opened = webbrowser.open(auth_url, new=1)
        if opened:
            print("[info] Opened browser automatically.")
    except Exception:
        pass

    try:
        callback = wait_for_callback(redirect_uri)
    except OSError as e:
        print("\nFailed to start local HTTP listener.")
        print(f"Error: {e}")
        print("Check that the redirect_uri host/port is local and not already in use.")
        sys.exit(1)
    except TimeoutError as e:
        print(f"\n{e}")
        sys.exit(1)

    if callback.get("error"):
        print("\nAuthorization failed in browser callback:")
        print(f"error={callback.get('error')}")
        if callback.get("error_description"):
            print(f"description={callback.get('error_description')}")
        sys.exit(1)

    code = callback.get("code")
    returned_state = callback.get("state")
    if not code:
        print("\nNo authorization code found in callback.")
        sys.exit(1)
    if returned_state != state:
        print("\nState mismatch in callback. Aborting.")
        sys.exit(1)

    resp = exchange_code_for_tokens(client_id, client_secret, redirect_uri, code)
    if resp.status_code >= 400:
        print_token_failure_help(config, resp)
        sys.exit(1)

    token_data = resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    if not access_token:
        print("\nToken response did not include access_token.")
        print(token_data)
        sys.exit(1)
    if not refresh_token:
        print("\nToken response did not include refresh_token.")
        print("This usually means offline_access was not granted.")
        print(f"Scopes sent: {' '.join(scopes)}")
        sys.exit(1)

    try:
        tenant_id = fetch_tenant_id(access_token)
    except requests.RequestException as e:
        print("\nFailed to fetch Xero tenant connections.")
        print(f"Error: {e}")
        print("Tokens were received, but tenant_id could not be resolved.")
        tenant_id = None

    now = int(time.time())
    expires_in = token_data.get("expires_in")
    payload: Dict[str, object] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "scopes": scopes,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "tenant_id": tenant_id,
        "token_type": token_data.get("token_type"),
        "expires_in": expires_in,
        "obtained_at": now,
    }
    if isinstance(expires_in, int):
        payload["expires_at"] = now + expires_in

    save_secrets_file(payload)

    print(f"\nSaved tokens and tenant_id to {SECRETS_FILE}")
    if tenant_id is None:
        print("tenant_id is null; connect the app to an organisation and run again if needed.")


if __name__ == "__main__":
    main()
