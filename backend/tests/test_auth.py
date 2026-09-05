"""Registration, session and authorisation behaviour."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User

VALID_PASSWORD = "correct-horse-battery"


def register_payload(email: str = "dev@example.com") -> dict[str, str]:
    return {"email": email, "name": "Test Developer", "password": VALID_PASSWORD}


class TestRegister:
    def test_creates_account_and_starts_session(self, client: TestClient) -> None:
        response = client.post("/api/auth/register", json=register_payload())

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "dev@example.com"
        assert "password" not in body
        assert "password_hash" not in body
        assert client.cookies.get("flowforge_session")

    def test_email_is_case_insensitive_and_unique(self, client: TestClient) -> None:
        client.post("/api/auth/register", json=register_payload("Dev@Example.com"))
        response = client.post("/api/auth/register", json=register_payload("dev@example.com"))

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "conflict"

    def test_rejects_short_password(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/register",
            json={**register_payload(), "password": "short"},
        )

        assert response.status_code == 422

    def test_rejects_invalid_email(self, client: TestClient) -> None:
        response = client.post("/api/auth/register", json=register_payload("not-an-email"))

        assert response.status_code == 422


class TestLogin:
    def test_returns_session_for_valid_credentials(self, client: TestClient) -> None:
        client.post("/api/auth/register", json=register_payload())
        client.cookies.clear()

        response = client.post(
            "/api/auth/login",
            json={"email": "DEV@example.com", "password": VALID_PASSWORD},
        )

        assert response.status_code == 200
        assert client.cookies.get("flowforge_session")

    def test_wrong_password_and_unknown_email_are_indistinguishable(
        self, client: TestClient
    ) -> None:
        client.post("/api/auth/register", json=register_payload())
        client.cookies.clear()

        wrong_password = client.post(
            "/api/auth/login", json={"email": "dev@example.com", "password": "wrong-password"}
        )
        unknown_email = client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": VALID_PASSWORD}
        )

        assert wrong_password.status_code == unknown_email.status_code == 401
        assert wrong_password.json() == unknown_email.json()

    def test_password_is_not_stored_in_plain_text(
        self, client: TestClient, session: Session
    ) -> None:
        client.post("/api/auth/register", json=register_payload())

        user = session.scalar(select(User).where(User.email == "dev@example.com"))

        assert user is not None
        assert VALID_PASSWORD not in user.password_hash
        assert user.password_hash.startswith("$argon2")


class TestSession:
    def test_me_returns_the_signed_in_account(self, client: TestClient) -> None:
        client.post("/api/auth/register", json=register_payload())

        response = client.get("/api/auth/me")

        assert response.status_code == 200
        assert response.json()["email"] == "dev@example.com"

    def test_me_requires_authentication(self, client: TestClient) -> None:
        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "unauthenticated"

    def test_logout_clears_the_session(self, client: TestClient) -> None:
        client.post("/api/auth/register", json=register_payload())

        assert client.post("/api/auth/logout").status_code == 204
        assert client.get("/api/auth/me").status_code == 401

    def test_tampered_token_is_rejected(self, client: TestClient) -> None:
        client.post("/api/auth/register", json=register_payload())
        client.cookies.set("flowforge_session", "not.a.valid.token")

        assert client.get("/api/auth/me").status_code == 401


class TestHealth:
    def test_liveness(self, client: TestClient) -> None:
        assert client.get("/api/health").json() == {"status": "ok"}

    def test_readiness_checks_the_database(self, client: TestClient) -> None:
        assert client.get("/api/health/ready").json() == {"status": "ok", "database": "ok"}
