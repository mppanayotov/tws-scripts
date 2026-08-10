from vwce_buy.runtime import api_diagnostics

def test_runtime_diagnostics_reports_the_imported_official_api():
    values = api_diagnostics()
    assert values["ibapi_version"] == "10.49.2" and "site-packages" in values["ibapi_path"]
