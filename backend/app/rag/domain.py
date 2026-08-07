from __future__ import annotations

import re

DOMAIN_KEYWORDS = [
    # English
    "master", "phd", "doctorate", "postgraduate", "graduate", "admission", "applicant",
    "application", "enroll", "enrolment", "tuition", "scholarship", "grant", "fellowship",
    "program", "course", "curriculum", "semester", "credit", "thesis", "dissertation",
    "regulation", "requirement", "deadline", "graduation", "transcript", "diploma",
    "degree", "department", "faculty", "study", "training", "syllabus", "exam", "test",
    "document", "prerequisite", "gpa", "defense", "advisor", "registration", "fee",
    "language", "toefl", "ielts", "academic", "research", "university", "college",
    # Vietnamese
    "thạc sĩ", "tiến sĩ", "sau đại học", "tuyển sinh", "nhập học", "học phí", "học bổng",
    "chương trình", "môn học", "mã ngành", "tín chỉ", "luận văn", "luận án", "quy chế",
    "quy định", "điều kiện", "hạn nộp", "tốt nghiệp", "bảng điểm", "bằng tốt nghiệp",
    "ngành", "khoa", "đào tạo", "đề cương", "thi", "hồ sơ", "điểm", "hướng dẫn",
    "đăng ký", "bảo vệ", "học kỳ", "niên khóa", "đồ án", "khóa luận",
]

_WORD_RE = re.compile(r"[a-z0-9à-ỹ]+", re.IGNORECASE)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def contains_domain_keyword(text: str) -> bool:
    norm = _normalize(text)
    for keyword in DOMAIN_KEYWORDS:
        if keyword in norm:
            return True
    # Multi-word keyword check against tokens
    words = set(_WORD_RE.findall(norm))
    single = {"master", "phd", "tuition", "scholarship", "thesis", "deadline", "graduation", "course"}
    if words & single:
        return True
    return False


def is_postgraduate_question(question: str, history_text: str = "") -> bool:
    """Lightweight, cheap domain gate. Accepts when the question (or recent
    conversation context) mentions postgraduate-related concepts."""
    if contains_domain_keyword(question):
        return True
    if history_text and contains_domain_keyword(history_text):
        return True
    # Follow-up style questions (short, references) inside an existing
    # postgraduate conversation are allowed.
    if history_text and len(question.split()) <= 6:
        return True
    return False


DOMAIN_REJECTION_MESSAGE = (
    "Sorry, I can only assist with postgraduate education information "
    "contained in the available documents."
)

NO_INFO_MESSAGE = (
    "I could not find relevant information in the available postgraduate documents. "
    "Try asking about admission requirements, tuition, programs, regulations, "
    "or other information contained in the uploaded documents."
)

# Phrases that indicate the assistant declined to answer or could not find
# an answer. When the answer matches these, sources should not be shown.
REJECTION_PHRASES = [
    "only answer questions related to postgraduate education",
    "only assist with postgraduate education",
    "only answer questions about postgraduate education",
    "can only assist with postgraduate education",
    "could not find this information",
    "could not find relevant information",
    "could not find the answer",
    "cannot answer",
    "can't answer",
    "not able to answer",
    "does not contain the answer",
    "do not contain the answer",
    "outside the scope",
    "not related to postgraduate",
    # Vietnamese
    "tôi chỉ trả lời câu hỏi liên quan đến giáo dục sau đại học",
    "chỉ trả lời câu hỏi liên quan đến giáo dục sau đại học",
    "chỉ trả lời câu hỏi về giáo dục sau đại học",
    "chỉ có thể trả lời câu hỏi liên quan đến giáo dục sau đại học",
    "chỉ có thể trả lời các câu hỏi liên quan đến giáo dục sau đại học",
    "chỉ trả lời các câu hỏi liên quan đến giáo dục sau đại học",
    "trả lời các câu hỏi liên quan đến giáo dục sau đại học",
    "chỉ hỗ trợ thông tin giáo dục sau đại học",
    "chỉ hỗ trợ giáo dục sau đại học",
    "không tìm thấy thông tin",
    "không tìm thấy câu trả lời",
    "không thể trả lời",
    "không có thông tin trong tài liệu",
    "tài liệu không chứa thông tin",
    "ngoài phạm vi",
    "không liên quan đến giáo dục sau đại học",
]


def is_rejection_answer(answer: str) -> bool:
    norm = _normalize(answer)
    return any(phrase in norm for phrase in REJECTION_PHRASES)
