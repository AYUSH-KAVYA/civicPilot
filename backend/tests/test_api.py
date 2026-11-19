"""
API Happy Path and Integration Tests for CivicPilot REST API.
"""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_auth_login(client):
    # Valid login
    resp = await client.post("/api/auth/login", json={"password": "testpassword123"})
    assert resp.status_code == 200
    assert "token" in resp.json()

    # Invalid login
    bad_resp = await client.post("/api/auth/login", json={"password": "wrongpassword"})
    assert bad_resp.status_code == 401
    assert "error" in bad_resp.json()


@pytest.mark.asyncio
async def test_case_lifecycle_happy_path(client):
    # 1. Login as officer
    login_resp = await client.post("/api/auth/login", json={"password": "testpassword123"})
    officer_token = login_resp.json()["token"]
    officer_headers = {"Authorization": f"Bearer {officer_token}"}

    # 2. Citizen files grievance
    payload = {
        "text": "Water main pipe broke and is flooding 100 City Hall Plaza.",
        "contact": "citizen.alex@example.com",
        "lat": 37.750,
        "lng": -122.420,
        "address_text": "100 City Hall Plaza",
        "channel": "web",
    }
    create_resp = await client.post("/api/cases", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    case_id = created_data["case_id"]
    access_token = created_data["access_token"]
    citizen_headers = {"X-Case-Token": access_token}

    # 3. Fetch case with citizen token
    case_resp = await client.get(f"/api/cases/{case_id}", headers=citizen_headers)
    assert case_resp.status_code == 200
    case_state = case_resp.json()
    assert case_state["id"] == case_id
    assert case_state["citizen"]["contact_masked"] == "c***x@example.com"

    # 4. Officer lists cases
    list_resp = await client.get("/api/cases", headers=officer_headers)
    assert list_resp.status_code == 200
    cases_list = list_resp.json()
    assert any(c["id"] == case_id for c in cases_list)

    # 5. Citizen sends follow-up message
    msg_resp = await client.post(
        f"/api/cases/{case_id}/messages",
        json={"text": "Water level is rising near the entrance."},
        headers=citizen_headers,
    )
    assert msg_resp.status_code == 200

    # 6. Check audit events
    events_resp = await client.get(f"/api/cases/{case_id}/events", headers=citizen_headers)
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 1

    # 7. Citizen confirms repair
    confirm_resp = await client.post(
        f"/api/cases/{case_id}/confirm",
        json={"confirmed": True, "comment": "Water is stopped, thank you!"},
        headers=citizen_headers,
    )
    assert confirm_resp.status_code == 200

    # Check case status is now CLOSED
    updated_case_resp = await client.get(f"/api/cases/{case_id}", headers=officer_headers)
    assert updated_case_resp.json()["status"] == "CLOSED"


@pytest.mark.asyncio
async def test_sandbox_controls(client):
    # Create a demo scenario first to get a ticket
    demo_resp = await client.post("/api/demo/scenarios/happy/run")
    assert demo_resp.status_code == 200
    case_id = demo_resp.json()["case_id"]

    # Fetch case to find ticket_id
    case_resp = await client.get(f"/api/cases/{case_id}", headers={"X-Case-Token": demo_resp.json()["access_token"]})
    tickets = case_resp.json().get("tickets", [])
    if tickets:
        ticket_id = tickets[0]["id"]

        # Crew check-in
        checkin_resp = await client.post(
            f"/api/sandbox/tickets/{ticket_id}/crew-checkin",
            json={"lat": 37.750, "lng": -122.420, "notes": "Arrived at leak"},
        )
        assert checkin_resp.status_code == 200

        # Repair photo
        repair_resp = await client.post(
            f"/api/sandbox/tickets/{ticket_id}/repair-photo",
            json={"photo_url": "https://example.com/repair.jpg", "notes": "Leak sealed"},
        )
        assert repair_resp.status_code == 200


@pytest.mark.asyncio
async def test_metrics_summary(client):
    resp = await client.get("/api/metrics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_cases" in data
    assert "cases_by_status" in data
    assert "avg_time_to_first_action_sec" in data


@pytest.mark.asyncio
async def test_tick_endpoint(client):
    resp = await client.post("/api/tick")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "processed_count" in data
