from __future__ import annotations

import io
import uuid

import pytest
from sqlalchemy import select

from app.models.document import Document


async def _auth(client):
    response = await client.post(
        "/api/admin/auth/login", json={"username": "admin", "password": "admin12345"}
    )
    assert response.status_code == 200
    return {}


@pytest.mark.asyncio
async def test_upload_requires_auth(client):
    response = await client.post(
        "/api/admin/documents",
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_rejects_bad_extension(client):
    await _auth(client)
    response = await client.post(
        "/api/admin/documents",
        files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_txt(client):
    await _auth(client)
    response = await client.post(
        "/api/admin/documents",
        files={"file": ("guide.txt", io.BytesIO("Học phí thạc sĩ là 20 triệu".encode("utf-8")), "text/plain")},
        data={"title": "Hướng dẫn tuyển sinh"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["document"]
    assert data["status"] == "UPLOADING"
    assert data["document_type"] == "txt"
    assert data["title"] == "Hướng dẫn tuyển sinh"


@pytest.mark.asyncio
async def test_upload_rejects_oversized(client):
    await _auth(client)
    big = b"x" * (30 * 1024 * 1024)
    response = await client.post(
        "/api/admin/documents",
        files={"file": ("big.pdf", io.BytesIO(big), "application/pdf")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_document_crud(client, db):
    await _auth(client)
    response = await client.post(
        "/api/admin/documents",
        files={"file": ("regulations.md", io.BytesIO("# Quy chế\nĐiều 1. Học phí...".encode("utf-8")), "text/markdown")},
        data={"category": "regulation", "year": "2026"},
    )
    assert response.status_code == 200
    doc_id = response.json()["document"]["id"]

    listing = await client.get("/api/admin/documents")
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    fetched = await client.get(f"/api/admin/documents/{doc_id}")
    assert fetched.status_code == 200
    assert fetched.json()["filename"] == "regulations.md"

    updated = await client.put(
        f"/api/admin/documents/{doc_id}",
        json={"title": "New Title", "year": 2025},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "New Title"
    assert updated.json()["year"] == 2025

    deleted = await client.delete(f"/api/admin/documents/{doc_id}")
    assert deleted.status_code == 200

    gone = await client.get(f"/api/admin/documents/{doc_id}")
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_document_download_and_view(client, db):
    await _auth(client)
    response = await client.post(
        "/api/admin/documents",
        files={"file": ("sample.txt", io.BytesIO("nội dung tài liệu".encode("utf-8")), "text/plain")},
    )
    doc_id = response.json()["document"]["id"]

    download = await client.get(f"/api/documents/{doc_id}/download")
    assert download.status_code == 200
    assert "sample.txt" in download.headers.get("content-disposition", "")

    view = await client.get(f"/api/documents/{doc_id}/view")
    assert view.status_code == 200
