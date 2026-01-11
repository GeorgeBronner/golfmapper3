"""
Test the actual /auth/token endpoint
"""
import requests

API_URL = "http://localhost:8005"

def test_login():
    print("Testing login endpoint...")
    print(f"URL: {API_URL}/auth/token")
    print()

    # Login credentials
    credentials = {
        "username": "george",
        "password": "newpassword123"
    }

    try:
        response = requests.post(
            f"{API_URL}/auth/token",
            data=credentials  # OAuth2 uses form data, not JSON
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        print()

        if response.status_code == 200:
            print("[SUCCESS] Login worked!")
            data = response.json()
            print(f"Access Token: {data.get('access_token', 'N/A')[:50]}...")
            print(f"Token Type: {data.get('token_type', 'N/A')}")
        else:
            print("[FAIL] Login failed")

    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to backend server at", API_URL)
        print("Make sure the server is running:")
        print("  cd backend")
        print("  uv run uvicorn app.main:app --host 0.0.0.0 --port 8005")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    test_login()
