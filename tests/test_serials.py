from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import get_password_hash
from app.models import Customer, Dealer, Product, Serial, User


@pytest.fixture
def serial_fixture(client: TestClient, db_session: Session) -> dict:
    # 1. Product
    prod = Product(code="PROD-TEST-PHONE", name="Phone 15", warranty_months=12)
    db_session.add(prod)

    # 2. Dealers
    dealer_a = Dealer(name="Đại lý A", phone="0111111111", address="Hà Nội")
    dealer_b = Dealer(name="Đại lý B", phone="0222222222", address="TP.HCM")
    db_session.add_all([dealer_a, dealer_b])
    db_session.commit()

    # 3. Users
    admin = User(
        email="admin_serial@test.com",
        password_hash=get_password_hash("AdminPass123!"),
        role="admin",
        dealer_id=None,
        is_active=True,
    )
    dealer_user_a = User(
        email="dealera@test.com",
        password_hash=get_password_hash("DealerPass123!"),
        role="dealer",
        dealer_id=dealer_a.id,
        is_active=True,
    )
    dealer_user_b = User(
        email="dealerb@test.com",
        password_hash=get_password_hash("DealerPass123!"),
        role="dealer",
        dealer_id=dealer_b.id,
        is_active=True,
    )
    db_session.add_all([admin, dealer_user_a, dealer_user_b])

    # 4. Customer
    customer = Customer(name="Khách Hàng 1", phone="0999888777", email="cust1@test.com")
    db_session.add(customer)
    db_session.commit()

    # Get tokens
    admin_token = client.post(
        "/auth/login", json={"email": "admin_serial@test.com", "password": "AdminPass123!"}
    ).json()["access_token"]
    dealer_a_token = client.post(
        "/auth/login", json={"email": "dealera@test.com", "password": "DealerPass123!"}
    ).json()["access_token"]
    dealer_b_token = client.post(
        "/auth/login", json={"email": "dealerb@test.com", "password": "DealerPass123!"}
    ).json()["access_token"]

    return {
        "admin_hdr": {"Authorization": f"Bearer {admin_token}"},
        "dealer_a_hdr": {"Authorization": f"Bearer {dealer_a_token}"},
        "dealer_b_hdr": {"Authorization": f"Bearer {dealer_b_token}"},
        "product_id": prod.id,
        "dealer_a_id": dealer_a.id,
        "dealer_b_id": dealer_b.id,
        "customer_id": customer.id,
    }


def test_create_single_serial(client: TestClient, serial_fixture: dict) -> None:
    admin_hdr = serial_fixture["admin_hdr"]
    dealer_hdr = serial_fixture["dealer_a_hdr"]
    prod_id = serial_fixture["product_id"]

    # 1. Dealer cannot create serial -> 403
    res_forbidden = client.post(
        "/serials", json={"product_id": prod_id, "serial_no": "SN-001"}, headers=dealer_hdr
    )
    assert res_forbidden.status_code == 403

    # 2. Admin creates serial -> 201 with status in_stock
    res_create = client.post(
        "/serials", json={"product_id": prod_id, "serial_no": "SN-001"}, headers=admin_hdr
    )
    assert res_create.status_code == 201
    data = res_create.json()
    assert data["serial_no"] == "SN-001"
    assert data["status"] == "in_stock"

    # 3. Duplicate serial_no -> 409
    res_dup = client.post(
        "/serials", json={"product_id": prod_id, "serial_no": "SN-001"}, headers=admin_hdr
    )
    assert res_dup.status_code == 409


def test_create_bulk_serials(client: TestClient, serial_fixture: dict) -> None:
    admin_hdr = serial_fixture["admin_hdr"]
    prod_id = serial_fixture["product_id"]

    # 1. More than 1000 -> 400
    res_limit = client.post(
        "/serials/bulk",
        json={"product_id": prod_id, "prefix": "BK-", "start_no": 1, "end_no": 1002},
        headers=admin_hdr,
    )
    assert res_limit.status_code == 400

    # 2. Create valid bulk serials (5 serials)
    res_bulk = client.post(
        "/serials/bulk",
        json={"product_id": prod_id, "prefix": "BK-", "start_no": 1, "end_no": 5, "padding_zeros": 4},
        headers=admin_hdr,
    )
    assert res_bulk.status_code == 201
    data = res_bulk.json()
    assert data["total_created"] == 5
    assert len(data["items"]) == 5
    assert data["items"][0]["serial_no"] == "BK-0001"
    assert data["items"][4]["serial_no"] == "BK-0005"

    # 3. Duplicate in bulk -> 409
    res_dup = client.post(
        "/serials/bulk",
        json={"product_id": prod_id, "prefix": "BK-", "start_no": 3, "end_no": 6, "padding_zeros": 4},
        headers=admin_hdr,
    )
    assert res_dup.status_code == 409


def test_lifecycle_state_machine_transitions(client: TestClient, serial_fixture: dict) -> None:
    admin_hdr = serial_fixture["admin_hdr"]
    dealer_a_hdr = serial_fixture["dealer_a_hdr"]
    prod_id = serial_fixture["product_id"]
    dealer_a_id = serial_fixture["dealer_a_id"]
    customer_id = serial_fixture["customer_id"]

    # Create serial: initial status is in_stock
    client.post(
        "/serials", json={"product_id": prod_id, "serial_no": "LIFE-01"}, headers=admin_hdr
    )

    # RULE: Can only activate serial that is shipped. Attempt to activate while in_stock -> 409
    res_bad_activate = client.post(
        "/serials/LIFE-01/activate",
        json={"customer_id": customer_id},
        headers=admin_hdr,
    )
    assert res_bad_activate.status_code == 409
    assert "expected 'shipped'" in res_bad_activate.json()["detail"].lower()

    # Step 1: Ship serial (in_stock -> shipped)
    res_ship = client.post(
        "/serials/LIFE-01/ship",
        json={"dealer_id": dealer_a_id},
        headers=admin_hdr,
    )
    assert res_ship.status_code == 200
    ship_data = res_ship.json()
    assert ship_data["status"] == "shipped"
    assert ship_data["dealer_id"] == dealer_a_id
    assert ship_data["shipped_at"] is not None

    # RULE: Cannot ship already shipped serial -> 409
    res_re_ship = client.post(
        "/serials/LIFE-01/ship",
        json={"dealer_id": dealer_a_id},
        headers=admin_hdr,
    )
    assert res_re_ship.status_code == 409

    # RULE: Activated date in future -> 400
    future_date = (date.today() + timedelta(days=2)).isoformat()
    res_future = client.post(
        "/serials/LIFE-01/activate",
        json={"customer_id": customer_id, "activated_at": future_date},
        headers=dealer_a_hdr,
    )
    assert res_future.status_code == 400
    assert "future" in res_future.json()["detail"].lower()

    # Step 2: Activate serial (shipped -> activated)
    res_activate = client.post(
        "/serials/LIFE-01/activate",
        json={"customer_id": customer_id},
        headers=dealer_a_hdr,
    )
    assert res_activate.status_code == 200
    act_data = res_activate.json()
    assert act_data["status"] == "activated"
    assert act_data["customer_id"] == customer_id
    assert act_data["activated_at"] == date.today().isoformat()
    assert act_data["warranty_end"] is not None

    # RULE: Cannot re-ship activated serial -> 409
    res_ship_again = client.post(
        "/serials/LIFE-01/ship",
        json={"dealer_id": dealer_a_id},
        headers=admin_hdr,
    )
    assert res_ship_again.status_code == 409

    # RULE: Cannot re-activate activated serial -> 409
    res_act_again = client.post(
        "/serials/LIFE-01/activate",
        json={"customer_id": customer_id},
        headers=dealer_a_hdr,
    )
    assert res_act_again.status_code == 409


def test_dealer_scoping_and_cross_dealer_permissions(
    client: TestClient, serial_fixture: dict
) -> None:
    admin_hdr = serial_fixture["admin_hdr"]
    dealer_a_hdr = serial_fixture["dealer_a_hdr"]
    dealer_b_hdr = serial_fixture["dealer_b_hdr"]
    prod_id = serial_fixture["product_id"]
    dealer_a_id = serial_fixture["dealer_a_id"]
    dealer_b_id = serial_fixture["dealer_b_id"]
    customer_id = serial_fixture["customer_id"]

    # Admin creates 2 serials and ships one to A, one to B
    client.post("/serials", json={"product_id": prod_id, "serial_no": "DEALER-A-01"}, headers=admin_hdr)
    client.post("/serials", json={"product_id": prod_id, "serial_no": "DEALER-B-01"}, headers=admin_hdr)

    client.post("/serials/DEALER-A-01/ship", json={"dealer_id": dealer_a_id}, headers=admin_hdr)
    client.post("/serials/DEALER-B-01/ship", json={"dealer_id": dealer_b_id}, headers=admin_hdr)

    # 1. Dealer A lists serials: only sees DEALER-A-01, does NOT see DEALER-B-01
    res_list_a = client.get("/serials", headers=dealer_a_hdr)
    assert res_list_a.status_code == 200
    items_a = res_list_a.json()["items"]
    serial_nos_a = [s["serial_no"] for s in items_a]
    assert "DEALER-A-01" in serial_nos_a
    assert "DEALER-B-01" not in serial_nos_a

    # 2. Dealer A views DEALER-B-01 detail: must return 404 (treated as non-existent)
    res_view_b = client.get("/serials/DEALER-B-01", headers=dealer_a_hdr)
    assert res_view_b.status_code == 404

    # 3. Dealer A attempts to activate Dealer B's serial: returns 403 (or 404)
    res_act_cross = client.post(
        "/serials/DEALER-B-01/activate",
        json={"customer_id": customer_id},
        headers=dealer_a_hdr,
    )
    assert res_act_cross.status_code == 403

    # 4. Dealer B activates their own serial: returns 200
    res_act_b = client.post(
        "/serials/DEALER-B-01/activate",
        json={"customer_id": customer_id},
        headers=dealer_b_hdr,
    )
    assert res_act_b.status_code == 200
    assert res_act_b.json()["status"] == "activated"

