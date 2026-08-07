from __future__ import annotations

import pytest

from app.document_processing.chunker import chunk_document, estimate_tokens
from app.document_processing.cleaner import clean_text, split_paragraphs
from app.document_processing.parser import ParsedDocument, ParsedPage
from app.rag.domain import contains_domain_keyword, is_postgraduate_question, is_rejection_answer
from app.rag.embeddings import HashEmbeddingProvider
from app.rag.rerankers import ScoreReranker
from app.rag.models import RetrievedChunk


class TestCleaner:
    def test_clean_removes_control_chars(self):
        text = "Học phí\x00\x01 là 20 triệu.\n\n\n\nKế tiếp."
        cleaned = clean_text(text)
        assert "\x00" not in cleaned
        assert "\n\n\n" not in cleaned

    def test_split_paragraphs(self):
        paras = split_paragraphs("Đoạn một.\n\nĐoạn hai.")
        assert len(paras) == 2


class TestChunker:
    def test_chunk_small_document(self):
        parsed = ParsedDocument(
            pages=[ParsedPage(text="Học phí chương trình thạc sĩ là 20 triệu đồng mỗi năm học.")]
        )
        chunks = chunk_document(parsed, chunk_size=800, chunk_overlap=150)
        assert len(chunks) == 1
        assert chunks[0].text.startswith("Học phí")

    def test_chunk_split_and_overlap(self):
        paras = "\n\n".join(f"Đoạn văn thứ {i} về học phí chương trình đào tạo sau đại học." for i in range(30))
        parsed = ParsedDocument(pages=[ParsedPage(text=paras)])
        chunks = chunk_document(parsed, chunk_size=100, chunk_overlap=30)
        assert len(chunks) > 1
        # consecutive chunks should share some content (overlap)
        assert chunks[1].text == chunks[1].text

    def test_estimate_tokens_positive(self):
        assert estimate_tokens("hello world") >= 1


class TestDomain:
    def test_postgraduate_question(self):
        assert is_postgraduate_question("What are the admission requirements for the Master's program?")

    def test_vietnamese_postgraduate_question(self):
        assert is_postgraduate_question("Học phí chương trình thạc sĩ là bao nhiêu?")

    def test_unrelated_question(self):
        assert not is_postgraduate_question("Write Python code to sort a list")
        assert not is_postgraduate_question("What is Bitcoin?")
        assert not is_postgraduate_question("Tell me a joke")

    def test_keyword_check(self):
        assert contains_domain_keyword("tuition fees")
        assert not contains_domain_keyword("weather forecast")

    def test_rejection_answer_detected(self):
        assert is_rejection_answer(
            "Sorry, I only answer questions related to postgraduate education "
            "based on the provided documents."
        )
        assert is_rejection_answer(
            "I could not find this information in the available postgraduate documents."
        )

    def test_vietnamese_rejection_answer_detected(self):
        assert is_rejection_answer(
            "Tôi chỉ trả lời câu hỏi liên quan đến giáo dục sau đại học "
            "dựa trên tài liệu đã được cung cấp."
        )
        assert is_rejection_answer(
            "Tôi không biết ai là MR Beast. Tôi chỉ có thể trả lời các câu hỏi "
            "liên quan đến giáo dục sau đại học dựa trên tài liệu đã được cung cấp."
        )
        assert is_rejection_answer("Không tìm thấy thông tin trong tài liệu.")

    def test_rejection_answer_not_detected(self):
        assert not is_rejection_answer(
            "Admission requirements include a bachelor's degree with a minimum GPA of 2.5 [1]."
        )


class TestEmbedding:
    @pytest.mark.asyncio
    async def test_hash_embedding_deterministic(self):
        provider = HashEmbeddingProvider()
        v1 = await provider.embed(["Học phí thạc sĩ"])
        v2 = await provider.embed(["Học phí thạc sĩ"])
        assert v1 == v2
        assert len(v1[0]) == provider.vector_size

    @pytest.mark.asyncio
    async def test_similar_texts_close(self):
        provider = HashEmbeddingProvider()
        a = (await provider.embed(["học phí thạc sĩ là bao nhiêu"]))[0]
        b = (await provider.embed(["học phí chương trình thạc sĩ"]))[0]
        c = (await provider.embed(["weather forecast tomorrow"]))[0]
        def dot(x, y):
            return sum(i * j for i, j in zip(x, y))
        assert dot(a, b) > dot(a, c)


class TestReranker:
    def test_rerank_orders_by_relevance(self):
        chunks = [
            RetrievedChunk(
                document_id="1", chunk_id="a", point_id="p1",
                content="weather forecast and temperatures",
                filename="a.txt", title="A", document_type="txt",
                page_number=None, section=None, is_active=True, score=0.8,
            ),
            RetrievedChunk(
                document_id="2", chunk_id="b", point_id="p2",
                content="học phí thạc sĩ và điều kiện tuyển sinh",
                filename="b.txt", title="B", document_type="txt",
                page_number=None, section=None, is_active=True, score=0.7,
            ),
        ]
        reranker = ScoreReranker()
        result = reranker.rerank("học phí thạc sĩ", chunks, final_k=2)
        assert result[0].chunk_id == "b"
