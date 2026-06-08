from pathlib import Path

import pytest

import main


def test_to_real_acres_converts_guntes():
    assert main._to_real_acres(2.30) == 2.75
    assert main._to_real_acres(0.20) == 0.5
    assert main._to_real_acres(None) == 0.0


def test_crops_area_uses_latest_year_only(client):
    response = client.get("/api/chart/crops-area")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["year"] == "2024-2025"
    assert payload["years"] == ["2024-2025"]
    assert sum(payload["values"]) == pytest.approx(4.25)


def test_paid_by_year_uses_latest_four_years(client):
    response = client.get("/api/chart/paid-by-year")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["labels"] == ["2021-2022", "2022-2023", "2023-2024", "2024-2025"]
    assert payload["values"] == [200.0, 300.0, 400.0, 750.0]


def test_share_count_uses_latest_year_only(client):
    response = client.get("/api/chart/share-count")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["year"] == "2024-2025"
    assert payload["values"] == [1, 1]


def test_bylist_renders_existing_template(client):
    response = client.get("/bylist")

    assert response.status_code == 200
    assert b"Farmer" in response.data


def test_shared_nav_has_bilingual_menu_labels(client):
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'data-en="Member List"' in html
    assert 'data-kn="ಸದಸ್ಯರ ಪಟ್ಟಿ"' in html
    assert 'data-en="Login"' in html
    assert 'data-kn="ಲಾಗಿನ್"' in html


def test_all_html_templates_parse(app):
    template_dir = Path(app.template_folder)
    failures = []
    for path in sorted(template_dir.glob("*.html")):
        try:
            app.jinja_env.get_template(path.name)
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")

    assert failures == []
