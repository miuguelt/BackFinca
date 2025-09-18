"""
Test script for the new Route Administration API
"""

import requests
import json
import sys
import os

# Force remote DB connection for testing
os.environ['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://fincau:fincac@isladigital.xyz:3311/finca'

BASE_URL = "https://127.0.0.1:8081/api/v1"

# Disable SSL warnings for self-signed certificates
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_route_administration_api():
    """Test the route administration API endpoints"""
    
    print("=== TESTING ROUTE ADMINISTRATION API ===")
    
    # First, login to get JWT token
    print("1. Logging in...")
    login_data = {
        "identification": 99999999,
        "password": "admin123"
    }
    
    try:
        login_response = requests.post(
            f"{BASE_URL}/auth/login",
            json=login_data,
            verify=False,
            timeout=10
        )
        
        if login_response.status_code == 200:
            print("✓ Login successful")
            # Get token from cookies or response
            token = None
            if 'access_token_cookie' in login_response.cookies:
                cookies = login_response.cookies
            else:
                login_data = login_response.json()
                token = login_data.get('access_token')
        else:
            print(f"✗ Login failed: {login_response.status_code} - {login_response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Login error: {e}")
        return False
    
    # Prepare headers
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Use cookies if available, otherwise use token in header
    if 'cookies' in locals():
        print("Using cookie authentication")
        auth_cookies = cookies
        auth_headers = headers
    else:
        print("Using header authentication")
        auth_headers = {**headers, 'Authorization': f'Bearer {token}'}
        auth_cookies = None
    
    # Test 1: Get all route administrations
    print("\n2. Testing GET /route-administrations...")
    try:
        response = requests.get(
            f"{BASE_URL}/route-administrations",
            headers=auth_headers,
            cookies=auth_cookies,
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            payload = response.json()
            routes = payload.get('data') or payload
            # If APIResponse paginated list, extract items
            if isinstance(routes, dict) and 'items' in routes:
                items = routes.get('items', [])
            else:
                items = routes
            print(f"✓ Found {len(items)} route administrations")
            for route in items:
                print(f"  - ID: {route.get('id')}, Name: {route.get('name')}")
        else:
            print(f"✗ Failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 2: Get active route administrations
    print("\n3. Testing GET /route-administrations/active...")
    try:
        response = requests.get(
            f"{BASE_URL}/route-administrations/active",
            headers=auth_headers,
            cookies=auth_cookies,
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            active_routes = response.json()
            print(f"✓ Found {len(active_routes)} active route administrations")
        else:
            print(f"✗ Failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 3: Create new route administration
    print("\n4. Testing POST /route-administrations...")
    new_route_data = {
        "name": "Subcutánea",
        "description": "Administración subcutánea para pruebas",
        "status": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/route-administrations",
            json=new_route_data,
            headers=auth_headers,
            cookies=auth_cookies,
            verify=False,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            created_payload = response.json()
            created_route = created_payload.get('data') or created_payload
            # If wrapper returns dict with 'id'
            if isinstance(created_route, dict) and 'id' in created_route:
                created_id = created_route.get('id')
            else:
                created_id = None
            print(f"✓ Created route administration ID: {created_id}")
        else:
            print(f"✗ Failed: {response.status_code} - {response.text}")
            created_id = None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        created_id = None
    
    # Test 4: Get medications with route administration
    print("\n5. Testing GET /medications/with-route-administration...")
    try:
        response = requests.get(
            f"{BASE_URL}/medications/with-route-administration",
            headers=auth_headers,
            cookies=auth_cookies,
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            medications = response.json()
            print(f"✓ Found {len(medications)} medications with route info")
            if medications:
                med = medications[0]
                print(f"  - Sample: {med.get('name')} - Route: {med.get('route_administration_rel', {}).get('name', 'N/A')}")
        else:
            print(f"✗ Failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 5: Search route administrations
    print("\n6. Testing GET /route-administrations/search?q=oral...")
    try:
        response = requests.get(
            f"{BASE_URL}/route-administrations/search?q=oral",
            headers=auth_headers,
            cookies=auth_cookies,
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            search_results = response.json()
            print(f"✓ Search returned {len(search_results)} results")
        else:
            print(f"✗ Failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Clean up: Delete created route if it exists
    if created_id:
        print(f"\n7. Cleaning up - deleting route ID {created_id}...")
        try:
            response = requests.delete(
                f"{BASE_URL}/route-administrations/{created_id}",
                headers=auth_headers,
                cookies=auth_cookies,
                verify=False,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                print("✓ Cleanup successful")
            else:
                print(f"✗ Cleanup failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"✗ Cleanup error: {e}")
    
    print("\n=== ROUTE ADMINISTRATION API TESTS COMPLETED ===")

if __name__ == "__main__":
    test_route_administration_api()
