import requests
import time

URL = "http://127.0.0.1:8000/ask"

def send_requests(n=50, pause=0.1):
    for i in range(n):
        try:
            resp = requests.post(URL, json={"question": "Explain cloud computing"}, timeout=10)
            print(i, resp.status_code, resp.text)
        except Exception as e:
            print(i, "error", e)
        time.sleep(pause)

if __name__ == "__main__":
    send_requests()
