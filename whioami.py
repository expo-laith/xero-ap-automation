import json, requests, sys

SECRETS_FILE = "xero_secrets.json"

with open(SECRETS_FILE, "r", encoding="utf-8") as f:
    s = json.load(f)

# 1) Refresh (Xero rotates refresh tokens every time)
tok = requests.post(
    "https://identity.xero.com/connect/token",
    data={
        "grant_type": "refresh_token",
        "refresh_token": s["refresh_token"],
        "client_id": s["client_id"],
        "client_secret": s["client_secret"],
    },
    timeout=20
)
tok.raise_for_status()
t = tok.json()
s["refresh_token"] = t["refresh_token"]  # save the rotated one!
with open(SECRETS_FILE, "w", encoding="utf-8") as f:
    json.dump(s, f, indent=2)

access_token = t["access_token"]

# 2) List connections (organisations the app is connected to)
resp = requests.get(
    "https://api.xero.com/connections",
    headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
    timeout=20
)
resp.raise_for_status()
conns = resp.json()

print("\nConnections:")
for c in conns:
    print(f"- {c['tenantName']} | tenantId={c['tenantId']}")

# 3) Quick check we're targeting the right org
expected = s["tenant_id"]
ok = any(c["tenantId"] == expected for c in conns)
print("\nTarget tenant_id:", expected)
print("Match in connections:", "YES ✅" if ok else "NO ❌")
if not ok:
    sys.exit(1)
