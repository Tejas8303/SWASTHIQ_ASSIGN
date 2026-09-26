from fastapi.testclient import TestClient
from app.main import app

def test_api_health_and_endpoints():
    with TestClient(app) as client:
        # 1. Health check
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok", "service": "SwasthiQ EOD Billing API"}

        # 2. Days listing
        res_days = client.get("/api/days")
        assert res_days.status_code == 200
        days_data = res_days.json()
        assert len(days_data) >= 2
        dates = [d["date"] for d in days_data]
        assert "2026-07-27" in dates
        assert "2026-07-25" in dates

        # 3. EOD Bundle for July 27
        res_bundle = client.get("/api/reports/eod-bundle?date=2026-07-27")
        assert res_bundle.status_code == 200
        bundle = res_bundle.json()
        assert bundle["clinic_id"] == "CLN-KNP-014"
        assert bundle["reconciliation"]["total_visits"] == 18
        assert bundle["reconciliation"]["total_billed_paise"] == 319000
        assert bundle["reconciliation"]["total_collected_paise"] == 317200
        assert bundle["reconciliation"]["total_outstanding_paise"] == 1800
        assert bundle["narrative"]["zero_invented_numbers"] is True
        assert len(bundle["narrative"]["traced_figures"]) > 0

        # 4. Ingestion audit check for July 27
        audit_res = client.get("/api/ingest/audit/latest?date=2026-07-27")
        assert audit_res.status_code == 200
        audit = audit_res.json()
        assert audit["total_rows"] == 19
        assert audit["valid_count"] == 18
        assert audit["rejected_count"] == 1
        assert len(audit["errors"]) == 1
        assert audit["errors"][0]["field"] == "payment_mode"
