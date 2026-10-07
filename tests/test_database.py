import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import Customer, Dealer, Product, Serial, User


def test_models_creation(db_session: Session) -> None:
    # 1. Create Dealer
    dealer = Dealer(name="Đại lý Test", phone="0901234567", address="Hà Nội")
    db_session.add(dealer)
    db_session.commit()
    assert dealer.id is not None

    # 2. Create User linked to Dealer
    user = User(
        email="dealer_test@example.com",
        password_hash="hashed_pw",
        role="dealer",
        dealer_id=dealer.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
    assert user.dealer.name == "Đại lý Test"

    # 3. Create Product
    product = Product(code="P-TEST", name="Sản phẩm Test", warranty_months=12)
    db_session.add(product)
    db_session.commit()
    assert product.id is not None

    # 4. Create Customer
    customer = Customer(name="Nguyễn Văn A", phone="0987654321", email="a@example.com")
    db_session.add(customer)
    db_session.commit()
    assert customer.id is not None

    # 5. Create Serial
    serial = Serial(
        serial_no="SN-TEST-001",
        product_id=product.id,
        dealer_id=dealer.id,
        customer_id=customer.id,
        status="in_stock",
    )
    db_session.add(serial)
    db_session.commit()
    assert serial.id is not None
    assert serial.product.code == "P-TEST"
    assert serial.dealer.name == "Đại lý Test"
    assert serial.customer.name == "Nguyễn Văn A"


def test_unique_serial_no_constraint(db_session: Session) -> None:
    prod = Product(code="P-1", name="Product 1", warranty_months=6)
    db_session.add(prod)
    db_session.commit()

    s1 = Serial(serial_no="SN-UNIQUE", product_id=prod.id, status="in_stock")
    db_session.add(s1)
    db_session.commit()

    s2 = Serial(serial_no="SN-UNIQUE", product_id=prod.id, status="in_stock")
    db_session.add(s2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unique_user_email_constraint(db_session: Session) -> None:
    u1 = User(email="test@example.com", password_hash="pw1", role="admin")
    db_session.add(u1)
    db_session.commit()

    u2 = User(email="test@example.com", password_hash="pw2", role="dealer")
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

