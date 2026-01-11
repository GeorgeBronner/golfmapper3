"""
Test the /garmin_courses/readall endpoint to see what data is returned
"""
import requests

API_URL = "http://localhost:8005"

def test_readall():
    print("Testing /garmin_courses/readall endpoint...")
    print(f"URL: {API_URL}/garmin_courses/readall")
    print()

    # First login to get token
    credentials = {
        "username": "george",
        "password": "newpassword123"
    }

    try:
        # Login
        login_response = requests.post(
            f"{API_URL}/auth/token",
            data=credentials
        )

        if login_response.status_code != 200:
            print(f"[FAIL] Login failed: {login_response.text}")
            return

        token = login_response.json()["access_token"]
        print(f"[SUCCESS] Login successful")
        print()

        # Call readall endpoint
        response = requests.get(
            f"{API_URL}/garmin_courses/readall",
            headers={"Authorization": f"Bearer {token}"}
        )

        print(f"Status Code: {response.status_code}")
        print()

        if response.status_code == 200:
            data = response.json()
            print(f"Data type: {type(data)}")
            print(f"Data: {data}")
            print()

            if isinstance(data, list):
                print(f"[SUCCESS] Got {len(data)} courses")
                print()

                # Show first 3 courses
                print("First 3 courses:")
                for i, course in enumerate(data[:3]):
                    print(f"\nCourse {i+1}:")
                    print(f"  ID: {course.get('id')}")
                    print(f"  display_name: {course.get('display_name')}")
                    print(f"  club_name: {course.get('club_name')}")
                    print(f"  course_name: {course.get('course_name')}")
                    print(f"  city: {course.get('city')}")
                    print(f"  state: {course.get('state')}")
            else:
                print(f"[INFO] Response is not a list, it's a {type(data)}")
                print(f"Keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
        else:
            print(f"[FAIL] Request failed: {response.text}")

    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to backend server at", API_URL)
        print("Make sure the server is running:")
        print("  cd backend")
        print("  uv run uvicorn app.main:app --host 0.0.0.0 --port 8005")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_readall()
