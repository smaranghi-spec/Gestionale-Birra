from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
checks = [
    ("/", 200),
    ("/ricette/html", 200),
    ("/acquisti", 200),
    ("/stili", 200),
]
for path, expected in checks:
    try:
        r = client.get(path)
        print(f"{path} -> {r.status_code} (expected {expected}) {'OK' if r.status_code == expected else 'FAIL'}")
    except Exception as e:
        print(f"{path} -> ERROR: {e}")
