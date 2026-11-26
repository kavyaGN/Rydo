"""End-to-end smoke test against a running stack (e.g. `docker compose up`).

Walks a full ride lifecycle through the public API using the seeded demo accounts:
rider finds nearby vehicles -> books a sedan -> driver accepts, starts, completes
-> rider pays and rates. Exits non-zero on the first failure.

Run: python -m scripts.smoke_test [--base-url http://localhost:8000]
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

PASSWORD = os.getenv("DEMO_PASSWORD", "Demo@12345")
PICKUP = {"pickup_address": "MG Road, Bengaluru", "pickup_latitude": 12.9757, "pickup_longitude": 77.6050}
DROPOFF = {"dropoff_address": "Indiranagar, Bengaluru", "dropoff_latitude": 12.9784, "dropoff_longitude": 77.6408}


def step(name: str, response: httpx.Response, expected: tuple[int, ...] = (200, 201)) -> dict:
    if response.status_code not in expected:
        print(f"FAIL  {name}: HTTP {response.status_code} {response.text[:300]}")
        sys.exit(1)
    print(f"ok    {name}")
    return response.json() if response.content else {}


def login(client: httpx.Client, email: str) -> dict[str, str]:
    data = step(f"login {email}", client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}))
    token = data.get("access_token") or data.get("tokens", {}).get("access_token")
    if not token:
        print(f"FAIL  login {email}: no access token in response")
        sys.exit(1)
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("API_BASE_URL", "http://localhost:8000"))
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=20) as client:
        step("readiness", client.get("/ready"))
        rider = login(client, "rider@rydo.dev")
        driver = login(client, "driver.sedan@rydo.dev")

        nearby = step(
            "nearby vehicles",
            client.get(
                "/api/v1/rides/nearby-vehicles",
                params={"pickup_latitude": PICKUP["pickup_latitude"], "pickup_longitude": PICKUP["pickup_longitude"], "ride_type": "sedan"},
                headers=rider,
            ),
        )
        print(f"      {len(nearby) if isinstance(nearby, list) else nearby.get('total', '?')} sedan(s) nearby")

        ride = step("book ride", client.post("/api/v1/rides", json={"ride_type": "sedan", **PICKUP, **DROPOFF}, headers=rider))
        ride_id = ride.get("id") or ride.get("ride", {}).get("id")
        print(f"      ride {ride_id}, status={ride.get('status')}, fare={ride.get('estimated_fare') or ride.get('fare')}")

        step("driver accepts", client.post(f"/api/v1/rides/{ride_id}/accept", headers=driver))
        step("driver starts", client.post(f"/api/v1/rides/{ride_id}/start", headers=driver))
        done = step("driver completes", client.post(f"/api/v1/rides/{ride_id}/complete", headers=driver))
        print(f"      final status={done.get('status')}, final fare={done.get('final_fare') or done.get('fare')}")

        step("rider pays", client.post(f"/api/v1/rides/{ride_id}/payments", json={"payment_method": "upi"}, headers=rider))
        step("rider rates", client.post(f"/api/v1/rides/{ride_id}/ratings", json={"rating": 5, "comment": "Smooth ride"}, headers=rider))
        history = step("ride history", client.get("/api/v1/customers/rides", headers=rider))
        count = len(history) if isinstance(history, list) else len(history.get("items", []))
        print(f"      rider has {count} ride(s) in history")

    print("\nSmoke test passed: full ride lifecycle works end to end.")


if __name__ == "__main__":
    main()
