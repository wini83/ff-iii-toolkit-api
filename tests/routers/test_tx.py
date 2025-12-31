def test_tx_screening_empty(client):
    response = client.get("/api/tx/screening?year=2024&month=1")
    assert response.status_code == 204


def test_tx_apply_category(client):
    response = client.post("/api/tx/1/category/2")
    assert response.status_code == 204


def test_tx_apply_tag(client):
    response = client.post("/api/tx/1/tag/?tag=blik_done")
    assert response.status_code == 204
