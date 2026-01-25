import requests
import json

BASE_URL = "http://localhost:5000"

def test_404():
    print("\n--- Testing 404 Not Found ---")
    url = f"{BASE_URL}/api/v1/non-existent-resource"
    response = requests.get(url)
    print(f"URL: {url}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_405():
    print("\n--- Testing 405 Method Not Allowed ---")
    # /api/v1/auth/login only allows POST
    url = f"{BASE_URL}/api/v1/auth/login"
    response = requests.get(url)
    print(f"URL: {url}")
    print(f"Method: GET")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_401_token_missing():
    print("\n--- Testing 401 Token Missing ---")
    # /api/v1/users/profile requires JWT
    url = f"{BASE_URL}/api/v1/users/profile"
    response = requests.get(url)
    print(f"URL: {url}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    try:
        test_404()
        test_405()
        test_401_token_missing()
    except Exception as e:
        print(f"Error connecting to server: {e}")
        print("Make sure the Flask server is running on http://localhost:5000")
