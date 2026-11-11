"""Tests for Sprint S23 inventory and manager endpoints."""

import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.main import app
import db
import init_db

client = TestClient(app)

def setup_module():
    """Ensure database has seed items."""
    init_db.init_db()

def test_inventory_returns_list():
    """GET /api/inventory returns 200 and items list with correct structure."""
    r = client.get("/api/inventory?tenant_id=Tenant_A")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) > 0
    item = data["items"][0]
    assert "name" in item
    assert "quantity" in item
    assert "status" in item
    assert "supplier" in item

def test_inventory_filters_tenant():
    """GET /api/inventory filters strictly by tenant_id."""
    r_a = client.get("/api/inventory?tenant_id=Tenant_A")
    assert r_a.status_code == 200
    items_a = r_a.json()["items"]
    assert any(i["name"] == "Widget-A" for i in items_a)
    assert not any(i["name"] == "Organic Cotton Yarn" for i in items_a)

    r_b = client.get("/api/inventory?tenant_id=Tenant_B")
    assert r_b.status_code == 200
    items_b = r_b.json()["items"]
    assert any(i["name"] == "Organic Cotton Yarn" for i in items_b)
    assert not any(i["name"] == "Widget-A" for i in items_b)

def test_inventory_status_logic():
    """Verify status logic: quantity == 0 -> stockout, < 100 -> low, else ok."""
    r = client.get("/api/inventory?tenant_id=Tenant_A")
    assert r.status_code == 200
    items = {i["name"]: i for i in r.json()["items"]}

    # Microcontrollers 32-bit has qty 0
    assert items["Microcontrollers 32-bit"]["quantity"] == 0
    assert items["Microcontrollers 32-bit"]["status"] == "stockout"

    # Widget-A has qty 50 (< 100)
    assert items["Widget-A"]["quantity"] == 50
    assert items["Widget-A"]["status"] == "low"

    # Semiconductors has qty 500 (>= 100)
    assert items["Semiconductors"]["quantity"] == 500
    assert items["Semiconductors"]["status"] == "ok"

def test_manager_pending_and_actions():
    """Test /api/manager/pending, /api/manager/approve, /api/manager/reject."""
    # Seed a pending request into admin_requests
    db.execute_mutation(
        "INSERT INTO admin_requests (tenant_id, action, item_name, quantity, transit_time, spot_rate, supplier_id, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("Tenant_A", "RESTOCK", "Microcontrollers 32-bit", 500, 10, 95.0, "SUP_014", "PENDING")
    )

    r = client.get("/api/manager/pending")
    assert r.status_code == 200
    pending = r.json()
    assert isinstance(pending, list)
    matching = [req for req in pending if req["item_name"] == "Microcontrollers 32-bit" and req["status"] == "PENDING"]
    assert len(matching) > 0
    req_id = matching[0]["id"]

    # Test approve
    r_approve = client.post("/api/manager/approve", json={"request_id": req_id})
    assert r_approve.status_code == 200
    assert r_approve.json()["status"] == "APPROVED"

    # Seed another pending request for reject
    db.execute_mutation(
        "INSERT INTO admin_requests (tenant_id, action, item_name, quantity, transit_time, spot_rate, supplier_id, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("Tenant_A", "CANCEL", "Hydraulic Actuators", 100, 15, 1450.0, "SUP_015", "PENDING")
    )
    r2 = client.get("/api/manager/pending")
    req2_id = [req for req in r2.json() if req["item_name"] == "Hydraulic Actuators" and req["status"] == "PENDING"][0]["id"]

    r_reject = client.post("/api/manager/reject", json={"request_id": req2_id})
    assert r_reject.status_code == 200
    assert r_reject.json()["status"] == "REJECTED"
