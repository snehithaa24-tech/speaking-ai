import pytest
import httpx


@pytest.mark.asyncio
async def test_get_categories(client: httpx.AsyncClient):
    res = await client.get("/api/v1/knowledge/categories")
    assert res.status_code == 200
    categories = res.json()
    assert "agriculture" in categories
    assert "government_schemes" in categories
    assert "transport" in categories
    assert "hospital_assistance" in categories


@pytest.mark.asyncio
async def test_create_and_search_document(client: httpx.AsyncClient):
    # 1. Create document
    doc_payload = {
        "title": "PM-KISAN Scheme Guide",
        "category": "government_schemes",
        "sourceUrl": "https://pmkisan.gov.in/",
        "content": "Income support of Rs 6000 per year for farmer families.",
        "language": "en-IN",
    }
    create_res = await client.post("/api/v1/knowledge", json=doc_payload)
    assert create_res.status_code == 201
    doc_id = create_res.json()["id"]

    # 2. Search for the document
    search_payload = {
        "query": "income support farmer",
        "category": "government_schemes",
        "language": "en-IN",
    }
    search_res = await client.post("/api/v1/knowledge/search", json=search_payload)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["totalResults"] >= 1
    assert any(d["id"] == doc_id for d in search_data["documents"])

    # 3. Get document by ID
    get_res = await client.get(f"/api/v1/knowledge/{doc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "PM-KISAN Scheme Guide"

    # 4. Delete document
    del_res = await client.delete(f"/api/v1/knowledge/{doc_id}")
    assert del_res.status_code == 204

    # 5. Verify deleted
    get_res2 = await client.get(f"/api/v1/knowledge/{doc_id}")
    assert get_res2.status_code == 404

