import httpx

def test_connection():
    try:
        response = httpx.get('https://www.google.com')
        print("Connection successful, status code:", response.status_code)
    except httpx.ConnectError as e:
        print("Connection failed:", e)

if __name__ == "__main__":
    test_connection()
