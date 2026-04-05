"""
Tests for dashboard analytics endpoints.

Covers: summary, category breakdown, monthly trends, and recent activity.
All authenticated roles should have access.
"""

from tests.conftest import auth_header


class TestDashboardSummary:
    """Tests for GET /api/v1/dashboard/summary"""

    def test_admin_can_access_summary(self, client, admin_token):
        response = client.get("/api/v1/dashboard/summary",
                              headers=auth_header(admin_token))
        assert response.status_code == 200
        data = response.json()
        assert "total_income" in data
        assert "total_expenses" in data
        assert "net_balance" in data
        assert "total_records" in data

    def test_viewer_can_access_summary(self, client, viewer_token):
        response = client.get("/api/v1/dashboard/summary",
                              headers=auth_header(viewer_token))
        assert response.status_code == 200

    def test_analyst_can_access_summary(self, client, analyst_token):
        response = client.get("/api/v1/dashboard/summary",
                              headers=auth_header(analyst_token))
        assert response.status_code == 200

    def test_no_auth_blocked(self, client):
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 403

    def test_net_balance_calculation(self, client, admin_token):
        response = client.get("/api/v1/dashboard/summary",
                              headers=auth_header(admin_token))
        data = response.json()
        assert data["net_balance"] == round(data["total_income"] - data["total_expenses"], 2)


class TestCategorySummary:
    """Tests for GET /api/v1/dashboard/category-summary"""

    def test_category_summary(self, client, admin_token):
        response = client.get("/api/v1/dashboard/category-summary",
                              headers=auth_header(admin_token))
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        for cat in data["categories"]:
            assert "category" in cat
            assert "total_income" in cat
            assert "total_expense" in cat
            assert "net" in cat
            # Verify net calculation
            assert cat["net"] == round(cat["total_income"] - cat["total_expense"], 2)


class TestTrends:
    """Tests for GET /api/v1/dashboard/trends"""

    def test_trends_default(self, client, admin_token):
        response = client.get("/api/v1/dashboard/trends",
                              headers=auth_header(admin_token))
        assert response.status_code == 200
        data = response.json()
        assert "trends" in data
        for trend in data["trends"]:
            assert "month" in trend
            assert "income" in trend
            assert "expense" in trend
            assert "net" in trend

    def test_trends_custom_months(self, client, admin_token):
        response = client.get("/api/v1/dashboard/trends?months=6",
                              headers=auth_header(admin_token))
        assert response.status_code == 200


class TestRecentActivity:
    """Tests for GET /api/v1/dashboard/recent"""

    def test_recent_default(self, client, admin_token):
        response = client.get("/api/v1/dashboard/recent",
                              headers=auth_header(admin_token))
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10  # Default limit

    def test_recent_custom_limit(self, client, admin_token):
        response = client.get("/api/v1/dashboard/recent?limit=3",
                              headers=auth_header(admin_token))
        assert response.status_code == 200
        assert len(response.json()) <= 3

    def test_recent_ordered_by_date(self, client, admin_token):
        response = client.get("/api/v1/dashboard/recent",
                              headers=auth_header(admin_token))
        data = response.json()
        if len(data) > 1:
            dates = [r["date"] for r in data]
            assert dates == sorted(dates, reverse=True)
