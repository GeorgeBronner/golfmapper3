from fastapi import status
from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)


def test_return_health_check():
    response = client.get("/healthy")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "I'm healthy"}


def test_csp_is_static_with_no_script_exceptions():
    csp = client.get("/healthy").headers["Content-Security-Policy"]
    directives = dict(d.strip().split(" ", 1) for d in csp.split(";"))
    # No nonces, inline scripts, or third-party script hosts — maps are
    # rendered by the bundled app now, not injected HTML.
    assert directives["script-src"] == "'self'"
    assert "https://tile.openstreetmap.org" in directives["img-src"]
    assert "https://server.arcgisonline.com" in directives["img-src"]


def test_spa_shell_is_served_unmodified_and_uncached(monkeypatch):
    # No built frontend in the test environment; stand one in.
    shell = "<html><head></head><body></body></html>"
    monkeypatch.setattr(main, "_INDEX_HTML", shell)
    response = client.get("/some/client/route")
    assert response.text == shell
    assert response.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
