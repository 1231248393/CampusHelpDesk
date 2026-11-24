import json
import getpass
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:5000"

username = input("Admin username: ").strip()
password = getpass.getpass("Admin password: ")

payload = json.dumps({
    "username": username,
    "password": password
}).encode("utf-8")

request = urllib.request.Request(
    BASE + "/api/admin/login",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read())

    token = result.get("access_token")

    if not token:
        print("LOGIN FAILED: No access token returned.")
        raise SystemExit(1)

    print("\nADMIN LOGIN SUCCESSFUL")
    print("Admin:", result["admin"]["username"])
    print("JWT token received and kept hidden.")

    # Test protected profile
    profile_request = urllib.request.Request(
        BASE + "/api/admin/me",
        headers={"Authorization": "Bearer " + token}
    )

    with urllib.request.urlopen(profile_request) as response:
        profile = json.loads(response.read())
        print("\nPROFILE TEST:", response.status)
        print(profile["message"])

    # Test logout
    logout_request = urllib.request.Request(
        BASE + "/api/admin/logout",
        data=b"{}",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(logout_request) as response:
        print("\nLOGOUT TEST:", response.status)
        print(json.loads(response.read())["message"])

    # Verify revoked token cannot be reused
    try:
        urllib.request.urlopen(profile_request)
        print("WARNING: Revoked token was accepted.")
    except urllib.error.HTTPError as error:
        print("\nREVOKED TOKEN TEST:", error.code)

except urllib.error.HTTPError as error:
    print("\nLOGIN/API ERROR:", error.code)
    print(error.read().decode())

except urllib.error.URLError as error:
    print("\nCONNECTION ERROR:", error.reason)

finally:
    password = None
