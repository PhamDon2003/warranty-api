from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Customer, Dealer, Product, Serial


def test_warranty_lookup_public_cases(client: TestClient, db_session: Session) -> None:
    # Setup test data
    prod = Product(code="PROD-WARRANTY-TEST", name="Tivi OLED 55 inch", warranty_months=12)
    dealer = Dealer(name="Đại lý Điện Máy", phone="0123456789", address="Hà Nội")
    customer = Customer(name="Nguyễn Văn Bảo Mật", phone="0988776655", email="secret@test.com")
    db_session.add_all([prod, dealer, customer])
    db_session.commit()

    today = date.today()

    # 1. Serial not found -> 404
    res_404 = client.get("/warranty/NON-EXISTENT-SN")
    assert res_404.status_code == 404
    assert res_404.json()["detail"] == "Serial not found"

    # 2. Serial in_stock -> is_valid = False
    s_stock = Serial(serial_no="SN-STOCK", product_id=prod.id, status="in_stock")
    db_session.add(s_stock)
    db_session.commit()

    res_stock = client.get("/warranty/SN-STOCK")
    assert res_stock.status_code == 200
    data_stock = res_stock.json()
    assert data_stock["product_name"] == "Tivi OLED 55 inch"
    assert data_stock["status"] == "in_stock"
    assert data_stock["is_valid"] is False
    assert data_stock["activated_at"] is None
    assert data_stock["warranty_end"] is None

    # 3. Serial shipped -> is_valid = False
    s_shipped = Serial(
        serial_no="SN-SHIPPED",
        product_id=prod.id,
        dealer_id=dealer.id,
        status="shipped",
    )
    db_session.add(s_shipped)
    db_session.commit()

    res_shipped = client.get("/warranty/SN-SHIPPED")
    assert res_shipped.status_code == 200
    data_shipped = res_shipped.json()
    assert data_shipped["status"] == "shipped"
    assert data_shipped["is_valid"] is False

    # 4. Serial activated, still within warranty -> is_valid = True
    s_active = Serial(
        serial_no="SN-ACTIVE-VALID",
        product_id=prod.id,
        dealer_id=dealer.id,
        customer_id=customer.id,
        status="activated",
        activated_at=today - timedelta(days=30),
        warranty_end=today + timedelta(days=335),
    )
    db_session.add(s_active)
    db_session.commit()

    res_active = client.get("/warranty/SN-ACTIVE-VALID")
    assert res_active.status_code == 200
    data_active = res_active.json()
    assert data_active["product_name"] == "Tivi OLED 55 inch"
    assert data_active["status"] == "activated"
    assert data_active["is_valid"] is True
    assert data_active["activated_at"] == (today - timedelta(days=30)).isoformat()
    assert data_active["warranty_end"] == (today + timedelta(days=335)).isoformat()

    # 5. Serial activated, but expired -> is_valid = False
    s_expired = Serial(
        serial_no="SN-EXPIRED",
        product_id=prod.id,
        dealer_id=dealer.id,
        customer_id=customer.id,
        status="activated",
        activated_at=today - timedelta(days=400),
        warranty_end=today - timedelta(days=35),
    )
    db_session.add(s_expired)
    db_session.commit()

    res_expired = client.get("/warranty/SN-EXPIRED")
    assert res_expired.status_code == 200
    data_expired = res_expired.json()
    assert data_expired["status"] == "activated"
    assert data_expired["is_valid"] is False

    # 6. Privacy verification: ensure customer personal info is NOT returned
    for key in ["customer", "customer_id", "customer_name", "phone", "email", "address"]:
        assert key not in data_active
        assert key not in data_expired


def test_warranty_not_found(client: TestClient) -> None:
    res = client.get("/warranty/DOES-NOT-EXIST-AT-ALL")
    assert res.status_code == 404
    assert res.json() == {"detail": "Serial not found"}


