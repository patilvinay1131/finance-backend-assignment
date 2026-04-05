"""
Tests for financial records endpoints.

Covers: CRUD operations, access control, filtering, pagination,
soft delete, and input validation.
"""

from tests.conftest import auth_header


class TestCreateRecord:
    """Tests for POST /api/v1/records/"""

    def test_admin_can_create_record(self, client, admin_token):
        response = client.post("/api/v1/records/", json={
            "amount": 5000,
            "type": "income",
            "category": "Salary",
            "date": "2024-01-15",
            "notes": "January salary",
        }, headers=auth_header(admin_token))
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == 5000
        assert data["type"] == "income"
        assert data["category"] == "Salary"

    def test_viewer_cannot_create_record(self, client, viewer_token):
        response = client.post("/api/v1/records/", json={
            "amount": 100,
            "type": "income",
            "category": "Test",
            "date": "2024-01-01",
        }, headers=auth_header(viewer_token))
        assert response.status_code == 403

    def test_analyst_cannot_create_record(self, client, analyst_token):
        response = client.post("/api/v1/records/", json={
            "amount": 100,
            "type": "income",
            "category": "Test",
            "date": "2024-01-01",
        }, headers=auth_header(analyst_token))
        assert response.status_code == 403

    def test_create_record_negative_amount(self, client, admin_token):
        response = client.post("/api/v1/records/", json={
            "amount": -100,
            "type": "income",
            "category": "Test",
            "date": "2024-01-01",
        }, headers=auth_header(admin_token))
        assert response.status_code == 422

    def test_create_record_zero_amount(self, client, admin_token):
        response = client.post("/api/v1/records/", json={
            "amount": 0,
            "type": "income",
            "category": "Test",
            "date": "2024-01-01",
        }, headers=auth_header(admin_token))
        assert response.status_code == 422

    def test_create_record_invalid_type(self, client, admin_token):
        response = client.post("/api/v1/records/", json={
            "amount": 100,
            "type": "transfer",
            "category": "Test",
            "date": "2024-01-01",
        }, headers=auth_header(admin_token))
        assert response.status_code == 422

    def test_create_record_blank_category(self, client, admin_token):
        response = client.post("/api/v1/records/", json={
            "amount": 100,
            "type": "income",
            "category": "   ",
            "date": "2024-01-01",
        }, headers=auth_header(admin_token))
        assert response.status_code == 422

    def test_create_record_no_auth(self, client):
        response = client.post("/api/v1/records/", json={
            "amount": 100,
            "type": "income",
            "category": "Test",
            "date": "2024-01-01",
        })
        assert response.status_code == 403


class TestListRecords:
    """Tests for GET /api/v1/records/"""

    def test_admin_can_list_records(self, client, admin_token):
        response = client.get("/api/v1/records/", headers=auth_header(admin_token))
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert "total" in data
        assert "page" in data

    def test_viewer_can_list_records(self, client, viewer_token):
        response = client.get("/api/v1/records/", headers=auth_header(viewer_token))
        assert response.status_code == 200

    def test_analyst_can_list_records(self, client, analyst_token):
        response = client.get("/api/v1/records/", headers=auth_header(analyst_token))
        assert response.status_code == 200

    def test_filter_by_type(self, client, admin_token):
        response = client.get("/api/v1/records/?type=income", headers=auth_header(admin_token))
        assert response.status_code == 200
        for record in response.json()["records"]:
            assert record["type"] == "income"

    def test_filter_by_invalid_type(self, client, admin_token):
        response = client.get("/api/v1/records/?type=invalid", headers=auth_header(admin_token))
        assert response.status_code == 400

    def test_pagination(self, client, admin_token):
        # Create multiple records
        for i in range(5):
            client.post("/api/v1/records/", json={
                "amount": 100 + i,
                "type": "expense",
                "category": "PaginationTest",
                "date": f"2024-02-{10 + i:02d}",
            }, headers=auth_header(admin_token))

        response = client.get("/api/v1/records/?per_page=2&page=1",
                              headers=auth_header(admin_token))
        data = response.json()
        assert len(data["records"]) <= 2
        assert data["per_page"] == 2


class TestGetRecord:
    """Tests for GET /api/v1/records/{record_id}"""

    def test_get_existing_record(self, client, admin_token):
        # Create a record first
        create_resp = client.post("/api/v1/records/", json={
            "amount": 999,
            "type": "income",
            "category": "GetTest",
            "date": "2024-03-01",
        }, headers=auth_header(admin_token))
        record_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/records/{record_id}",
                              headers=auth_header(admin_token))
        assert response.status_code == 200
        assert response.json()["amount"] == 999

    def test_get_nonexistent_record(self, client, admin_token):
        response = client.get("/api/v1/records/99999",
                              headers=auth_header(admin_token))
        assert response.status_code == 404


class TestUpdateRecord:
    """Tests for PUT /api/v1/records/{record_id}"""

    def test_admin_can_update_record(self, client, admin_token):
        # Create
        create_resp = client.post("/api/v1/records/", json={
            "amount": 1000,
            "type": "income",
            "category": "UpdateTest",
            "date": "2024-04-01",
        }, headers=auth_header(admin_token))
        record_id = create_resp.json()["id"]

        # Update
        response = client.put(f"/api/v1/records/{record_id}", json={
            "amount": 1500,
            "notes": "Updated amount",
        }, headers=auth_header(admin_token))
        assert response.status_code == 200
        assert response.json()["amount"] == 1500

    def test_viewer_cannot_update_record(self, client, admin_token, viewer_token):
        create_resp = client.post("/api/v1/records/", json={
            "amount": 100,
            "type": "expense",
            "category": "ViewerUpdateTest",
            "date": "2024-04-02",
        }, headers=auth_header(admin_token))
        record_id = create_resp.json()["id"]

        response = client.put(f"/api/v1/records/{record_id}", json={
            "amount": 200,
        }, headers=auth_header(viewer_token))
        assert response.status_code == 403


class TestDeleteRecord:
    """Tests for DELETE /api/v1/records/{record_id}"""

    def test_soft_delete_record(self, client, admin_token):
        # Create
        create_resp = client.post("/api/v1/records/", json={
            "amount": 500,
            "type": "expense",
            "category": "DeleteTest",
            "date": "2024-05-01",
        }, headers=auth_header(admin_token))
        record_id = create_resp.json()["id"]

        # Delete
        response = client.delete(f"/api/v1/records/{record_id}",
                                 headers=auth_header(admin_token))
        assert response.status_code == 200

        # Verify hidden from queries
        get_resp = client.get(f"/api/v1/records/{record_id}",
                              headers=auth_header(admin_token))
        assert get_resp.status_code == 404

    def test_viewer_cannot_delete(self, client, admin_token, viewer_token):
        create_resp = client.post("/api/v1/records/", json={
            "amount": 100,
            "type": "expense",
            "category": "ViewerDeleteTest",
            "date": "2024-05-02",
        }, headers=auth_header(admin_token))
        record_id = create_resp.json()["id"]

        response = client.delete(f"/api/v1/records/{record_id}",
                                 headers=auth_header(viewer_token))
        assert response.status_code == 403
