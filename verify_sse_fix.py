
import requests
import threading
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://localhost:5180/api/v1" 



def test_head_request():
    print("Testing HEAD request...")
    try:
        response = requests.head(f"{BASE_URL}/events", verify=False)
        print(f"HEAD request status: {response.status_code}")
        if response.status_code == 200:
            print("HEAD request SUCCESS")
        else:
            print("HEAD request FAILED")
    except Exception as e:
        print(f"HEAD request error: {e}")

def test_sse_connection(i):
    print(f"Starting SSE connection {i}...")
    try:
        with requests.get(f"{BASE_URL}/events", stream=True, timeout=5, verify=False) as response:
            print(f"Connection {i} status: {response.status_code}")
            if response.status_code == 200:
                print(f"Connection {i} SUCCESS")
                # Consume a bit of stream
                for line in response.iter_lines():
                    if line:
                        print(f"Connection {i} received data")
                        break
            else:
                 print(f"Connection {i} FAILED: {response.status_code}")
    except Exception as e:
         print(f"Connection {i} error: {e}")

def verify_fix():
    print("--- Verifying SSE Rate Limit Fix ---")
    
    # 1. Verify HEAD request
    test_head_request()
    
    # 2. Verify concurrent connections (try 5, which is > old limit of 3)
    threads = []
    for i in range(5):
        t = threading.Thread(target=test_sse_connection, args=(i,))
        threads.append(t)
        t.start()
        time.sleep(0.5) 
        
    for t in threads:
        t.join()

if __name__ == "__main__":
    verify_fix()
