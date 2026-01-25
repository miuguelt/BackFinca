import sys
import os
import json

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app import create_app
from flask_jwt_extended import create_access_token
from datetime import timedelta

app = create_app('development')

def test_expired_token():
    with app.test_client() as client:
        with app.app_context():
            # Create an expired token
            expires = timedelta(hours=-1)
            # Create a dummy token for identity '1'
            
            # Prepare payload for logging
            identity_val = "1"
            additional_claims_val = {'id': 1, 'role': 'admin'}
            jwt_payload = {'identity': identity_val, 'additional_claims': additional_claims_val}
            token_type = additional_claims_val.get('type', 'access') # Assuming 'type' might be in additional_claims
            logger.warning(f"DEBUG: Token Type: {token_type} | Payload: {json.dumps(jwt_payload)}")
            
            token = create_access_token(identity=identity_val, additional_claims=additional_claims_val, expires_delta=expires)
            
            # Debug: decode token
            from flask_jwt_extended import decode_token
            decoded = decode_token(token, allow_expired=True)
            print(f"Decoded Token Payload: {json.dumps(decoded, indent=2)}")
            
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            print(f"Testing /api/v1/auth/me with expired token...")
            response = client.get('/api/v1/auth/me', headers=headers)
            
            print(f"Status Code: {response.status_code}")
            print("Response Body:")
            print(json.dumps(response.get_json(), indent=2))

if __name__ == "__main__":
    test_expired_token()
