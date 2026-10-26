import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
import registration_api as api


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(api, "engine", engine)
    with TestClient(api.app) as client:
        yield client


def add(client, name="Ade", age=25):
    return client.post("/profiles", json={"username": name, "age": age})


def test_crud(client):
    result = add(client)
    assert result.status_code == 201
    profile_id = result.json()["id"]
    assert client.get(f"/profiles/{profile_id}").json()["username"] == "Ade"
    result = client.patch(f"/profiles/{profile_id}", json={"age": 26})
    assert result.status_code == 200 and result.json()["age"] == 26
    result = client.delete(f"/profiles/{profile_id}")
    assert result.status_code == 204 and result.content == b""
    assert client.get(f"/profiles/{profile_id}").status_code == 404


def test_filter_pagination(client):
    add(client)
    add(client, "Bola", 30)
    assert [p["username"] for p in client.get("/profiles?min_age=30").json()["profiles"]] == ["Bola"]
    assert client.get("/profiles?min_age=40").json() == {"profiles": []}
    assert client.get("/profiles?limit=1&offset=1").json()["profiles"][0]["username"] == "Bola"


@pytest.mark.parametrize("query", ["min_age=-1", "min_age=120", "min_age=abc", "limit=0", "limit=101", "offset=-1"])
def test_query_validation(client, query):
    assert client.get(f"/profiles?{query}").status_code == 422


@pytest.mark.parametrize("body", [{"username": " Ad ", "age": 25}, {"username": "Ade", "age": 0}, {"username": "Ade", "age": 120}, {"username": "Ade", "age": "oops"}, {"username": "Ade", "age": 25, "password": "unused"}])
def test_create_validation(client, body):
    assert client.post("/profiles", json=body).status_code == 422


def test_duplicate_create(client):
    assert add(client, " Ade ").json()["username"] == "Ade"
    assert add(client, "ade").status_code == 409
    assert len(client.get("/profiles").json()["profiles"]) == 1


def test_duplicate_update_rollback(client):
    add(client)
    bola_id = add(client, "Bola", 30).json()["id"]
    assert client.patch(f"/profiles/{bola_id}", json={"username": " ADE "}).status_code == 409
    assert client.get(f"/profiles/{bola_id}").json()["username"] == "Bola"


@pytest.mark.parametrize("body", [{}, {"age": None}, {"username": None}, {"age": 0}])
def test_patch_validation(client, body):
    profile_id = add(client).json()["id"]
    assert client.patch(f"/profiles/{profile_id}", json=body).status_code == 422


def test_missing_and_path_validation(client):
    for method in ("get", "delete"):
        assert getattr(client, method)("/profiles/999").status_code == 404
    assert client.patch("/profiles/999", json={"age": 26}).status_code == 404
    assert client.get("/profiles/abc").status_code == 422
    assert client.get("/profiles/0").status_code == 422


def test_docs(client):
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert sum(len(methods) for methods in paths.values()) == 5


def test_persistence(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'persistent.db'}"
    monkeypatch.setattr(api, "engine", create_engine(url, connect_args={"check_same_thread": False}))
    with TestClient(api.app) as first:
        profile_id = add(first).json()["id"]
    monkeypatch.setattr(api, "engine", create_engine(url, connect_args={"check_same_thread": False}))
    with TestClient(api.app) as second:
        assert second.get(f"/profiles/{profile_id}").json()["username"] == "Ade"
