import sys
from sqlalchemy import select
from app.core.config import settings
from app.core.security import get_password_hash
from app.db import SessionLocal
from app.models import Dealer, Product, User

# Ensure stdout and stderr support UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def seed() -> None:
    print("[INFO] Starting database seeding...")
    db = SessionLocal()
    try:
        # 1. Seed Admin User
        admin_user = db.scalar(select(User).where(User.email == settings.ADMIN_EMAIL))
        if not admin_user:
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                role="admin",
                dealer_id=None,
                is_active=True,
            )
            db.add(admin_user)
            print(f"[INFO] Created admin user: {settings.ADMIN_EMAIL}")
        else:
            print(f"[INFO] Admin user already exists: {settings.ADMIN_EMAIL}")

        # 2. Seed Sample Dealers
        dealer1 = db.scalar(select(Dealer).where(Dealer.name == "Đại lý Hà Nội"))
        if not dealer1:
            dealer1 = Dealer(
                name="Đại lý Hà Nội",
                phone="02431234567",
                address="123 Cầu Giấy, Hà Nội",
            )
            db.add(dealer1)
            db.flush()
            print("[INFO] Created dealer: Đại lý Hà Nội")

        dealer2 = db.scalar(select(Dealer).where(Dealer.name == "Đại lý TP.HCM"))
        if not dealer2:
            dealer2 = Dealer(
                name="Đại lý TP.HCM",
                phone="02831234567",
                address="456 Nguyễn Huệ, Quận 1, TP.HCM",
            )
            db.add(dealer2)
            db.flush()
            print("[INFO] Created dealer: Đại lý TP.HCM")

        # 3. Seed Sample Dealer User
        dealer_user = db.scalar(select(User).where(User.email == "dealer@example.com"))
        if not dealer_user and dealer1:
            dealer_user = User(
                email="dealer@example.com",
                password_hash=get_password_hash("DealerPassword123!"),
                role="dealer",
                dealer_id=dealer1.id,
                is_active=True,
            )
            db.add(dealer_user)
            print("[INFO] Created sample dealer user: dealer@example.com / DealerPassword123!")

        # 4. Seed Sample Products
        sample_products = [
            ("PROD-IP15", "iPhone 15 Pro 128GB", 12),
            ("PROD-MAC14", "MacBook Pro 14 M3", 24),
            ("PROD-AIRPODS", "AirPods Pro Gen 2", 12),
        ]
        for code, name, warranty_months in sample_products:
            prod = db.scalar(select(Product).where(Product.code == code))
            if not prod:
                prod = Product(
                    code=code,
                    name=name,
                    warranty_months=warranty_months,
                )
                db.add(prod)
                print(f"[INFO] Created product: {code} - {name} ({warranty_months} months)")

        db.commit()
        print("[SUCCESS] Database seeding completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seeding failed: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
