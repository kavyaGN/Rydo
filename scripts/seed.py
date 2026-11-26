"""Seed demo data so the app is usable right after `docker compose up`.

Creates an admin, a rider and three approved, online drivers around Bengaluru
with different vehicle types. Safe to run repeatedly: existing users are skipped.

Run: python -m scripts.seed
"""

from __future__ import annotations

import os

from sqlalchemy import select

from app.database import SessionLocal
from app.infrastructure.database.models import DriverModel, UserModel, VehicleModel
from app.infrastructure.services.password_service import PasswordService

# Demo-only credentials, documented in the README. Override with DEMO_PASSWORD.
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "Demo@12345")
# On a public deployment set DEMO_ADMIN_PASSWORD to a secret, so visitors can try the
# rider and driver flows but cannot open the admin console (which lists all users).
DEMO_ADMIN_PASSWORD = os.getenv("DEMO_ADMIN_PASSWORD") or DEMO_PASSWORD

USERS = [
    {"email": "admin@rydo.dev", "phone_number": "+919000000001", "full_name": "Rydo Admin", "role": "admin"},
    {"email": "rider@rydo.dev", "phone_number": "+919000000002", "full_name": "Asha Rider", "role": "customer"},
]

# (name, email, phone, lat, lng, vehicle_type, make, model, color, registration, capacity)
DRIVERS = [
    ("Ravi Kumar", "driver.bike@rydo.dev", "+919000000011", 12.9116, 77.6474, "bike", "Honda", "Activa", "Black", "KA01AB1001", 1),
    ("Meena S", "driver.auto@rydo.dev", "+919000000012", 12.9352, 77.6245, "auto", "Bajaj", "RE", "Yellow", "KA01AB1002", 3),
    ("Arjun Rao", "driver.sedan@rydo.dev", "+919000000013", 12.9763, 77.5713, "sedan", "Hyundai", "Verna", "White", "KA01AB1003", 4),
]


def _get_or_create_user(db, passwords: PasswordService, *, email: str, phone_number: str, full_name: str, role: str) -> tuple[UserModel, bool]:
    user = db.scalar(select(UserModel).where(UserModel.email == email))
    if user:
        return user, False
    user = UserModel(
        email=email,
        phone_number=phone_number,
        full_name=full_name,
        role=role,
        status="active",
        is_email_verified=True,
        is_phone_verified=True,
        password_hash=passwords.hash_password(DEMO_ADMIN_PASSWORD if role == "admin" else DEMO_PASSWORD),
    )
    db.add(user)
    db.flush()
    return user, True


def seed() -> None:
    passwords = PasswordService()
    created: list[str] = []
    with SessionLocal() as db:
        for spec in USERS:
            _, is_new = _get_or_create_user(db, passwords, **spec)
            if is_new:
                created.append(spec["email"])

        for name, email, phone, lat, lng, vtype, make, model, color, reg, capacity in DRIVERS:
            user, is_new = _get_or_create_user(
                db, passwords, email=email, phone_number=phone, full_name=name, role="driver"
            )
            if not is_new:
                continue
            driver = DriverModel(
                user_id=user.id,
                approval_status="approved",
                availability_status="online",
                current_latitude=lat,
                current_longitude=lng,
                average_rating=4.8,
            )
            db.add(driver)
            db.flush()
            db.add(
                VehicleModel(
                    driver_id=driver.id,
                    vehicle_type=vtype,
                    make=make,
                    model=model,
                    color=color,
                    registration_number=reg,
                    capacity=capacity,
                    approval_status="approved",
                    is_active=True,
                )
            )
            created.append(email)
        db.commit()

    if created:
        print(f"Seeded {len(created)} demo accounts: {', '.join(created)}")
    else:
        print("Demo data already present; nothing to seed.")


if __name__ == "__main__":
    seed()
