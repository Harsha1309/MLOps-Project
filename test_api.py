"""
test_api.py
-----------
Quick smoke test for the API using FastAPI's TestClient (no server needed).

Run:
    python test_api.py
"""

from fastapi.testclient import TestClient
from main import app


def run():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200 and r.json()["model_loaded"], r.text
        print("health OK:", r.json())

        r = client.get("/months")
        assert r.status_code == 200 and len(r.json()["months"]) == 12
        print("months OK")

        r = client.get("/places", params={"category": "Beach"})
        assert r.status_code == 200 and r.json()["count"] > 0
        print(f"places OK: {r.json()['count']} beach destinations")

        r = client.post("/predict", json={"place": "Goa", "month": "December"})
        assert r.status_code == 200
        print("predict OK:", r.json())

        r = client.post(
            "/recommend",
            json={
                "month": "May",
                "category": "Hill Station",
                "min_temp_c": 5,
                "max_temp_c": 25,
                "top_n": 3,
            },
        )
        assert r.status_code == 200 and r.json()["count"] > 0
        print("recommend OK:", [rec["place"] for rec in r.json()["recommendations"]])

        # invalid month should 400
        r = client.post("/predict", json={"place": "Goa", "month": "Smarch"})
        assert r.status_code == 400
        print("invalid-month validation OK")

        # unknown place should 404
        r = client.post("/predict", json={"place": "Atlantis", "month": "June"})
        assert r.status_code == 404
        print("unknown-place validation OK")

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    run()
