from __future__ import annotations

import io

import pytest

from app.document_processing.parser import ParsedDocument, ParsedPage
from app.services.metadata_extractor import detect_language, extract_metadata, parse_filename

VIETNAMESE_DOC = """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
TRƯỜNG ĐẠI HỌC CÔNG NGHỆ
Số: 123/QĐ-ĐHCN ngày 15/01/2026
QUYẾT ĐỊNH
Về việc ban hành Quy chế đào tạo trình độ thạc sĩ của Trường Đại học Công nghệ giai đoạn 2025 - 2026
Căn cứ Nghị định số 99/2019/NĐ-CP ngày 30/12/2019 của Chính phủ quy định chi tiết và hướng dẫn thi hành một số điều của Luật Giáo dục đại học.
Điều 1. Ban hành kèm theo Quyết định này Quy chế đào tạo trình độ thạc sĩ của Trường Đại học Công nghệ.
Điều 2. Quy chế này có hiệu lực kể từ ngày 01/03/2026.
Quy chế đào tạo trình độ thạc sĩ được xây dựng nhằm đảm bảo chất lượng đào tạo và được áp dụng cho các chương trình thạc sĩ của nhà trường."""

ENGLISH_DOC = """SOCIALIST REPUBLIC OF VIET NAM
Independence - Freedom - Happiness
HANOI UNIVERSITY OF TECHNOLOGY
No. 45/HTU/QD dated 15/01/2026
DECISION
On issuing the Tuition Regulation for Master's programs of Hanoi University of Technology for the academic year 2025-2026
Pursuant to the Government's Decree No. 99/2019/ND-CP dated 30/12/2019 detailing the Law on Higher Education.
Article 1. The Tuition Regulation for Master's programs of Hanoi University of Technology is issued herewith.
Article 2. This Regulation takes effect from 01/03/2026."""


def test_detect_language_vietnamese():
    code, confidence = detect_language("Đây là văn bản quy định về học phí của trường đại học công nghệ.")
    assert code == "vi"
    assert confidence > 0.5


def test_detect_language_english():
    code, confidence = detect_language("This is the official admission regulation for the graduate school of the university.")
    assert code == "en"
    assert confidence > 0.5


def test_parse_filename_year_and_version():
    info = parse_filename("QD-2025-ver1.2.pdf")
    assert info["year"] == 2025
    assert info["version"] == "1.2"


def test_parse_filename_academic_range():
    info = parse_filename("CTDT-thac-si-2025-2026.pdf")
    assert info["year"] == 2025
    assert info["year_method"] == "academic_range_filename"


@pytest.mark.asyncio
async def test_extract_metadata_deterministic(db):
    parsed = ParsedDocument(pages=[ParsedPage(text=VIETNAMESE_DOC, page_number=1)])
    result = await extract_metadata(
        db,
        filename="Quyet-dinh-quy-che-dao-tao-thac-si-2025.txt",
        parsed=parsed,
        use_llm=False,
    )
    assert result.title.value is not None
    assert "quy chế" in result.title.value.lower() or "ban hành" in result.title.value.lower()
    assert result.title.confidence > 0.5
    assert result.category.value == "Training Regulation"
    assert result.category.confidence > 0.4
    assert result.year.value == 2025
    assert result.year.confidence > 0.5
    assert result.language.value == "vi"
    assert result.description.value is not None
    assert result.description.value
    assert result.version.value is None


@pytest.mark.asyncio
async def test_extract_metadata_english(db):
    parsed = ParsedDocument(pages=[ParsedPage(text=ENGLISH_DOC, page_number=1)])
    result = await extract_metadata(
        db,
        filename="tuition-regulation-2025.txt",
        parsed=parsed,
        use_llm=False,
    )
    assert result.title.value is not None
    assert "tuition" in result.title.value.lower()
    assert result.language.value == "en"
    assert result.year.value == 2025


async def _auth(client):
    response = await client.post(
        "/api/admin/auth/login", json={"username": "admin", "password": "admin12345"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_extract_metadata_endpoint(client):
    await _auth(client)
    response = await client.post(
        "/api/admin/documents/extract-metadata",
        files={"file": ("quyche.md", io.BytesIO(VIETNAMESE_DOC.encode("utf-8")), "text/markdown")},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["filename"] == "quyche.md"
    assert data["title"]["value"]
    assert data["category"]["value"] == "Training Regulation"
    assert data["year"]["value"] == 2025
    assert data["language"]["value"] == "vi"
    assert data["description"]["value"]
    assert "confidence" in data["title"]


@pytest.mark.asyncio
async def test_extract_metadata_endpoint_rejects_bad_extension(client):
    await _auth(client)
    response = await client.post(
        "/api/admin/documents/extract-metadata",
        files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_without_auto_index_saves_draft(client):
    await _auth(client)
    response = await client.post(
        "/api/admin/documents",
        files={"file": ("draft.md", io.BytesIO(b"# Draft\ncontent"), "text/markdown")},
        data={"auto_index": "false", "title": "Draft Doc"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["document"]["status"] == "DRAFT"
    assert data["document"]["title"] == "Draft Doc"


@pytest.mark.asyncio
async def test_upload_default_auto_indexes(client):
    await _auth(client)
    response = await client.post(
        "/api/admin/documents",
        files={"file": ("note.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["document"]["status"] == "UPLOADING"


@pytest.mark.asyncio
async def test_re_extract_metadata_endpoint(client):
    await _auth(client)
    response = await client.post(
        "/api/admin/documents",
        files={"file": ("quyche.txt", io.BytesIO(VIETNAMESE_DOC.encode("utf-8")), "text/plain")},
        data={"auto_index": "false"},
    )
    assert response.status_code == 200, response.text
    doc_id = response.json()["document"]["id"]

    re_extract = await client.post(f"/api/admin/documents/{doc_id}/re-extract-metadata")
    assert re_extract.status_code == 200, re_extract.text
    data = re_extract.json()
    assert data["filename"] == "quyche.txt"
    assert data["title"]["value"]
    assert data["category"]["value"] == "Training Regulation"
    assert data["year"]["value"] == 2025
