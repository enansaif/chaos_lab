import pytest


@pytest.mark.django_db
def test_api_schema(api_client):
    response = api_client.get("/api/schema/")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/vnd.oai.openapi")


@pytest.mark.django_db
def test_api_docs(api_client):
    response = api_client.get("/api/docs/")

    assert response.status_code == 200
    assert b"swagger" in response.content.lower()
