from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.document_processing.parser import ParsedDocument
from app.llm.base import ChatMessage, LLMUnavailableError
from app.schemas.document import MetadataExtractionResult, MetadataField
from app.services import settings_service
from app.services.llm_gateway import LLMGateway

logger = get_logger(__name__)

VIETNAMESE_SPECIFIC = (
    "ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộơớờởỡợ"
    "úùủũụưứừửữự"
)

_VI_STOPWORDS = {
    "và", "của", "cho", "được", "các", "trong", "không", "này", "để",
    "theo", "với", "đến", "một", "nhà", "trường", "tại", "năm", "sẽ",
    "đã", "về", "có", "việc", "thuộc", "học", "đào", "tạo",
}
_EN_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "has",
    "are", "was", "were", "which", "not", "into", "about", "within",
    "under", "shall", "will", "may", "must", "all", "any", "each",
}

_BOILERPLATE = {
    "cộng hòa xã hội chủ nghĩa việt nam",
    "cộng hoà xã hội chủ nghĩa việt nam",
    "socialist republic of viet nam",
    "socialist republic of vietnam",
}

_TITLE_KEYWORDS = (
    "quy định", "quyết định", "thông báo", "chương trình", "hướng dẫn", "thông tư",
    "nghị định", "chỉ thị", "kế hoạch", "công văn", "giấy mời", "biên bản", "đề án",
    "quy chế", "tiêu chí", "điều lệ", "regulation", "decision", "notice", "announcement",
    "curriculum", "guideline", "circular", "policy", "procedure", "programme", "program",
    "admission", "tuition", "scholarship", "syllabus", "syllabi",
)

_GENERIC_LABELS = {
    "quyết định", "quy định", "thông báo", "thông tư", "công văn", "quy chế",
    "chương trình", "hướng dẫn", "kế hoạch", "giấy mời", "biên bản", "đề án",
    "chỉ thị", "nghị định", "decision", "regulation", "notice", "announcement",
    "circular", "guideline", "policy", "procedure",
}

_YEAR_CONTEXT = (
    "năm học", "ban hành", "hiệu lực", "quyết định", "issued", "effective", "adopted",
    "publication", "xuất bản", "phát hành", "ký ngày", "từ ngày", "đến ngày", "số",
)

_ACADEMIC_RANGE_RE = re.compile(r"(20\d{2})\s*[-–—/]\s*(20\d{2})")

_VERSION_PATTERNS = (
    (re.compile(r"(?i)\bversion\s*[:.]?\s*([0-9]+(?:\.[0-9]+)*)\b"), 0.85, "version"),
    (re.compile(r"(?i)\bphiên\s*bản\s*[:.]?\s*([0-9]+(?:\.[0-9]+)*)\b"), 0.85, "version"),
    (re.compile(r"(?i)\brev(?:ision)?\s*[:.]?\s*([0-9]{1,3}(?:\.[0-9]+)*)\b"), 0.7, "revision"),
    (re.compile(r"(?i)\blần\s*ban\s*hành\s*[:.]?\s*([0-9]+)\b"), 0.7, "issuance"),
    (re.compile(r"(?i)\bbản\s*([0-9]+\.[0-9]+)\b"), 0.5, "version"),
    (re.compile(r"(?i)\bver\s*[:.]?\s*([0-9]+\.[0-9]+)\b"), 0.6, "version"),
)

_PROGRAM_PREFIX = re.compile(r"(?i)\b(?:thạc sĩ|tiến sĩ|master of|doctor of|ph\.?d\.?|mba|emba)\b")
_PROGRAM_STOP_SET = {
    "của", "tại", "trong", "giai", "đoạn", "năm", "theo", "and", "of", "in",
    "for", "và", "được", "cho", "the", "from", "to", "with", "kèm", "này", "số",
    "theo", "ban", "hành", "đại", "học", "trường", "quyết", "định", "quy", "chế",
}

_ENTITY_PREFIX_RE = re.compile(
    r"(Khoa|Phòng|Viện|Trung tâm|Trường|Department|Faculty|School|Institute|Office|Center|Centre)"
    r"\s+[A-Za-zÀ-ỹĐđ][^\n,;.]{0,60}"
)

_LLM_EXCERPT_MAX = 4000

_TITLE_MAX_LEN = 150


class _LLMOutput(BaseModel):
    title: str | None = None
    category: str | None = None
    year: int | str | None = None
    version: str | None = None
    department: str | None = None
    program: str | None = None
    language: str | None = None
    description: str | None = None


# --------------------------------------------------------------------------- #
# Low level helpers
# --------------------------------------------------------------------------- #


def _filename_stem(filename: str) -> str:
    return Path(filename or "document").stem


def _is_independence_line(line: str) -> bool:
    lowered = line.lower()
    return ("độc lập" in lowered and "tự do" in lowered) or "independence" in lowered


def _lines(parsed: ParsedDocument, max_pages: int = 3) -> list[str]:
    out: list[str] = []
    for page in parsed.pages[:max_pages]:
        for line in page.text.splitlines():
            line = line.strip()
            if line:
                out.append(line)
    return out


def _round_conf(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 2)


# --------------------------------------------------------------------------- #
# Language detection
# --------------------------------------------------------------------------- #


def detect_language(text: str) -> tuple[str, float]:
    """Return (code, confidence) with code in {vi, en, bilingual}."""
    if not text or not text.strip():
        return "vi", 0.2
    lower = text.lower()
    words = re.findall(r"[a-zà-ỹđ]+", lower)
    vi_specific_count = sum(1 for ch in lower if ch in VIETNAMESE_SPECIFIC)
    vi_stop = sum(1 for w in words if w in _VI_STOPWORDS)
    en_stop = sum(1 for w in words if w in _EN_STOPWORDS)
    letters = sum(1 for ch in lower if ch.isalpha())
    if letters == 0:
        return "vi", 0.3
    vi_ratio = vi_specific_count / letters

    if vi_stop >= 3 and en_stop >= 3 and vi_ratio > 0.004:
        return "bilingual", 0.6
    if vi_stop >= 2 or vi_ratio > 0.004:
        confidence = min(0.95, 0.45 + vi_ratio * 2.0 + vi_stop * 0.02)
        return "vi", confidence
    if en_stop >= 2:
        return "en", min(0.9, 0.5 + en_stop * 0.05)
    if vi_ratio > 0.001:
        return "vi", 0.45
    return "en", 0.4


# --------------------------------------------------------------------------- #
# Filename parsing
# --------------------------------------------------------------------------- #


def parse_filename(filename: str) -> dict:
    stem = _filename_stem(filename)
    info: dict = {}
    years = re.findall(r"20\d{2}", stem)
    if len(years) >= 2:
        info["year"] = int(years[0])
        info["year_method"] = "academic_range_filename"
    elif years:
        info["year"] = int(years[0])
        info["year_method"] = "filename"
    for pattern in (
        re.compile(r"(?i)\bversion[\s_.-]*([0-9]+(?:\.[0-9]+)*)\b"),
        re.compile(r"(?i)\brev[\s_.-]*([0-9]+(?:\.[0-9]+)*)\b"),
        re.compile(r"(?i)\bver[\s_.-]*([0-9]+(?:\.[0-9]+)*)\b"),
    ):
        match = pattern.search(stem)
        if match:
            info["version"] = match.group(1)
            break
    lower_stem = stem.lower()
    if re.search(r"(?<![a-z])en(?![a-z])", lower_stem):
        info["lang_hint"] = "en"
    elif "tieng_anh" in lower_stem or "tieng-anh" in lower_stem or "tieng anh" in lower_stem:
        info["lang_hint"] = "en"
    elif re.search(r"(?<![a-z])vi(?![a-z])", lower_stem):
        info["lang_hint"] = "vi"
    return info


# --------------------------------------------------------------------------- #
# Title detection
# --------------------------------------------------------------------------- #


def _file_metadata_title(file_path: str | None, extension: str | None) -> str | None:
    if not file_path or not extension:
        return None
    try:
        if extension == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            meta = reader.metadata or {}
            title = meta.get("/Title")
        elif extension == ".docx":
            import docx

            title = docx.Document(file_path).core_properties.title
        else:
            return None
    except Exception as exc:
        logger.warning("file_metadata_title_failed ext=%s error=%s", extension, exc)
        return None
    if not title:
        return None
    title = " ".join(str(title).split())
    return title if 3 <= len(title) <= _TITLE_MAX_LEN else None


def _score_title(line: str, index: int, lines: list[str]) -> float:
    lowered = line.lower().strip()
    if lowered in _BOILERPLATE:
        return -100.0
    if _is_independence_line(line):
        return -80.0
    if len(line) < 6 or len(line) > 120:
        return -50.0
    if re.fullmatch(r"[\d\s.,\-/:()%]+", line):
        return -90.0
    if line.startswith(("http://", "https://", "www.")):
        return -90.0
    if re.search(r"(ngày\s+\d{1,2}\s+tháng|\bhà nội\b.*\bngày\b)", lowered):
        return -60.0

    score = 0.0
    keyword_hits = sum(1 for keyword in _TITLE_KEYWORDS if keyword in lowered)
    if keyword_hits:
        score += min(8.0, 3.0 + keyword_hits * 2.0)
    if 10 <= len(line) <= 90:
        score += 2.0
    if index < 3:
        score += 4.0
    elif index < 8:
        score += 3.0
    elif index < 15:
        score += 2.0
    elif index < 30:
        score += 1.0
    if line.isupper():
        score += 1.5
    if lowered in _GENERIC_LABELS and len(line) < 20:
        score -= 8.0
    if lowered.startswith(("về việc", "về ", "ban hành", "hướng dẫn")):
        score += 2.0
    if lowered.startswith(("trường đại học", "đại học", "viện", "khoa ", "phòng ")) and keyword_hits == 0 and len(line) < 50:
        score -= 3.0
    if index >= 1 and (_is_independence_line(lines[index - 1]) or lines[index - 1].lower().startswith(
        ("trường đại học", "đại học", "socialist republic")
    )):
        score += 3.0
    if index >= 1 and lines[index - 1].strip().lower() in _GENERIC_LABELS:
        score += 4.0
    return score


def _detect_title(
    parsed: ParsedDocument,
    filename: str,
    file_meta_title: str | None,
) -> tuple[str | None, float, str]:
    if file_meta_title:
        return file_meta_title, 0.9, "file_metadata"

    lines = _lines(parsed, max_pages=2)
    best: str | None = None
    best_score = float("-inf")
    for index, line in enumerate(lines[:40]):
        score = _score_title(line, index, lines)
        if score > best_score:
            best, best_score = line, score
    if best and best_score >= 6:
        confidence = min(0.9, 0.4 + best_score * 0.06)
        return best, confidence, "heading"

    stem = re.sub(r"[\-_]+", " ", _filename_stem(filename)).strip()
    title = re.sub(r"\s+", " ", stem).strip()
    if title:
        return title[: _TITLE_MAX_LEN], 0.35, "filename"
    return None, 0.0, "none"


# --------------------------------------------------------------------------- #
# Category detection
# --------------------------------------------------------------------------- #


def _detect_category(
    lines: list[str],
    categories: list[object],
) -> tuple[str | None, float, str]:
    text = " ".join(lines[:60]).lower()
    best_name: str | None = None
    best_count = 0
    second_count = 0
    for category in categories:
        name = getattr(category, "name", None) or (category.get("name") if isinstance(category, dict) else None)
        keywords = getattr(category, "keywords", None)
        if keywords is None and isinstance(category, dict):
            keywords = category.get("keywords", [])
        if not name or not keywords:
            continue
        count = sum(text.count(str(kw).lower()) for kw in keywords)
        if count > best_count:
            second_count = best_count
            best_count = count
            best_name = name
        elif count > second_count:
            second_count = count
    if best_name is None or best_count == 0:
        return None, 0.0, "needs_review"
    if best_count <= 1 and second_count and best_count - second_count <= 1:
        return best_name, 0.3, "ambiguous"
    confidence = min(0.92, 0.35 + best_count * 0.15)
    return best_name, confidence, "keyword"


# --------------------------------------------------------------------------- #
# Year detection
# --------------------------------------------------------------------------- #


def _context_years(lines: list[str]) -> list[tuple[float, int, int]]:
    hits: list[tuple[float, int, int]] = []
    for index, line in enumerate(lines[:80]):
        for match in re.finditer(r"20\d{2}", line):
            year = int(match.group(0))
            window = line[max(0, match.start() - 40) : match.end() + 40].lower()
            score = 1.0
            if "năm học" in window:
                score += 4.0
            if any(k in window for k in ("ban hành", "hiệu lực", "issued", "effective")):
                score += 4.0
            elif any(k in window for k in ("quyết định", "ngày", "ký", "adopted", "publication", "xuất bản")):
                score += 2.0
            hits.append((score, year, index))
    hits.sort(key=lambda item: (item[0], -item[2]), reverse=True)
    return hits


def _detect_year(
    parsed: ParsedDocument,
    filename_info: dict,
    lines: list[str],
    filename: str,
) -> tuple[int | None, float, str]:
    stem = _filename_stem(filename)
    match = _ACADEMIC_RANGE_RE.search(stem)
    if match:
        return int(match.group(1)), 0.85, "academic_range_filename"

    for index, line in enumerate(lines[:80]):
        match = _ACADEMIC_RANGE_RE.search(line)
        if match:
            confidence = 0.75 if "năm học" in line.lower() else 0.6
            return int(match.group(1)), confidence, "academic_range_text"

    if filename_info.get("year") is not None:
        return filename_info["year"], 0.6, filename_info.get("year_method", "filename")

    hits = _context_years(lines)
    if hits and hits[0][0] >= 3:
        score, year, _index = hits[0]
        confidence = min(0.85, 0.4 + score * 0.08)
        return year, confidence, "context"

    for line in lines[:30]:
        match = re.search(r"\b20\d{2}\b", line)
        if match:
            return int(match.group(0)), 0.4, "first_page"
    return None, 0.0, "none"


# --------------------------------------------------------------------------- #
# Version / department / program detection
# --------------------------------------------------------------------------- #


def _detect_version(lines: list[str]) -> tuple[str | None, float, str]:
    for pattern, confidence, method in _VERSION_PATTERNS:
        for line in lines[:80]:
            match = pattern.search(line)
            if match:
                return match.group(1).strip("."), confidence, method
    return None, 0.0, "none"


def _expand_entity(line: str, phrase: str) -> str:
    low = line.lower()
    index = low.find(phrase.lower())
    if index < 0:
        return phrase
    match = _ENTITY_PREFIX_RE.search(line[max(0, index - 40) : index + 90])
    if match:
        return re.sub(r"\s+", " ", match.group(0)).strip(" -")
    return line[max(0, index - 2) : index + 90].strip(" -:,")


def _detect_department(
    lines: list[str],
    departments: list[str],
) -> tuple[str | None, float, str]:
    hits: list[tuple[int, str]] = []
    for department in departments:
        if not department:
            continue
        for index, line in enumerate(lines[:80]):
            if department.lower() in line.lower():
                hits.append((index, _expand_entity(line, department)))
    if not hits:
        return None, 0.0, "none"
    hits.sort(key=lambda item: item[0])
    index, name = hits[0]
    confidence = min(0.8, 0.4 + max(0, 20 - index) * 0.02)
    return name, confidence, "keyword"


def _detect_program(
    lines: list[str],
    programs: list[str],
) -> tuple[str | None, float, str]:
    found: list[tuple[int, str]] = []
    seen: set[str] = set()
    for index, line in enumerate(lines[:80]):
        for match in _PROGRAM_PREFIX.finditer(line):
            prefix = match.group(0).strip()
            after = line[match.end() : match.end() + 80]
            tokens = [token.strip(" ,;:.") for token in re.split(r"\s+", after) if token.strip()]
            kept: list[str] = []
            for token in tokens:
                low = token.lower()
                if re.fullmatch(r"[\d\-–—/]+", token) or low in _PROGRAM_STOP_SET:
                    break
                kept.append(token)
                if len(kept) >= 4:
                    break
            chunk = (prefix + (" " + " ".join(kept) if kept else "")).strip()
            key = chunk.lower()
            if len(chunk) < 3 or key in seen:
                continue
            seen.add(key)
            found.append((index, chunk))
    joined = " ".join(lines[:40]).lower()
    for program in programs:
        if program and program.lower() in joined and program.lower() not in seen:
            seen.add(program.lower())
            found.append((0, program))
    if not found:
        return None, 0.0, "none"
    found.sort(key=lambda item: item[0])
    names = list(dict.fromkeys(name for _, name in found))[:3]
    value = "; ".join(names)
    confidence = min(0.8, 0.35 + max(0, 20 - found[0][0]) * 0.02 + 0.1 * min(3, len(names)))
    return value, confidence, "keyword"


# --------------------------------------------------------------------------- #
# Description detection
# --------------------------------------------------------------------------- #


def _detect_description(
    lines: list[str],
    title: str | None,
) -> tuple[str | None, float, str]:
    start = 0
    for index, line in enumerate(lines[:60]):
        lowered = line.lower()
        if lowered in _BOILERPLATE or _is_independence_line(line) or lowered.startswith(
            ("trường đại học", "đại học", "viện", "socialist republic")
        ):
            start = index + 1
        else:
            break
    if title:
        for index, line in enumerate(lines[start : start + 60]):
            if line.strip() == title.strip():
                start = start + index + 1
                break

    text = "\n".join(lines[start : start + 60])
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    picked: list[str] = []
    total = 0
    for sentence in sentences:
        if len(sentence) < 12:
            continue
        lowered = sentence.lower()
        if lowered in _BOILERPLATE or _is_independence_line(sentence):
            continue
        if re.fullmatch(r"[\d\s.,\-/:()%]+", sentence):
            continue
        picked.append(sentence)
        total += len(sentence) + 1
        if total > 320 or len(picked) >= 3:
            break
    if picked:
        return " ".join(picked), 0.6, "content"
    return None, 0.0, "none"


# --------------------------------------------------------------------------- #
# Optional LLM fallback
# --------------------------------------------------------------------------- #


def _parse_llm_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response")
    return json.loads(raw[start : end + 1])


def _coerce_year(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        years = re.findall(r"20\d{2}", str(value))
        return int(years[0]) if years else int(float(str(value)))
    except (TypeError, ValueError):
        return None


async def _llm_extract(
    db: AsyncSession,
    filename: str,
    lines: list[str],
    title: str | None,
) -> dict:
    headings = [ln for ln in lines[:40] if len(ln.strip()) <= 100][:12]
    excerpt = "\n".join(lines[:80])[:_LLM_EXCERPT_MAX]
    prompt = (
        "Extract document metadata from the excerpt below. Return a single JSON object "
        "with these keys: title, category, year, version, department, program, "
        'language ("vi" | "en" | "bilingual"), description (1-3 sentences). '
        "Never invent information. Leave a field empty (null) when the excerpt does not "
        "contain it.\n\n"
        f"Filename: {filename}\n"
        f"First-page headings:\n{chr(10).join(headings)}\n\n"
        f"Excerpt:\n{excerpt}\n\n"
        "Respond with JSON only."
    )
    gateway = LLMGateway(db)
    _provider, _model, raw = await gateway.generate(
        [
            ChatMessage(
                role="system",
                content=(
                    "You are a precise document metadata extraction assistant for a "
                    "university document archive. Only use information present in the "
                    "excerpt. If a field is unknown, return null."
                ),
            ),
            ChatMessage(role="user", content=prompt),
        ],
        temperature=0.0,
        max_tokens=600,
    )
    data = _parse_llm_json(raw)
    validated = _LLMOutput.model_validate(data).model_dump()
    validated["year"] = _coerce_year(validated.get("year"))
    if validated.get("language") not in ("vi", "en", "bilingual", None):
        validated["language"] = None
    for key in ("title", "category", "version", "department", "program", "description"):
        value = validated.get(key)
        if isinstance(value, str):
            validated[key] = re.sub(r"\s+", " ", value).strip() or None
    return validated


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


async def extract_metadata(
    db: AsyncSession,
    *,
    filename: str,
    parsed: ParsedDocument,
    file_path: str | None = None,
    extension: str | None = None,
    use_llm: bool = False,
) -> MetadataExtractionResult:
    lines = _lines(parsed, max_pages=3)
    filename_info = parse_filename(filename)
    file_meta_title = _file_metadata_title(file_path, extension)

    title, title_conf, title_method = _detect_title(parsed, filename, file_meta_title)

    settings = await settings_service.load_metadata(db)
    categories = list(settings.categories)
    departments = list(settings.departments)
    programs = list(settings.programs)

    category, cat_conf, cat_method = _detect_category(lines, categories)
    year, year_conf, year_method = _detect_year(parsed, filename_info, lines, filename)
    version, ver_conf, ver_method = _detect_version(lines)
    department, dept_conf, dept_method = _detect_department(lines, departments)
    program, prog_conf, prog_method = _detect_program(lines, programs)
    language, lang_conf = detect_language(" ".join(lines[:30]))
    lang_method = "text"
    description, desc_conf, desc_method = _detect_description(lines, title)

    lang_hint = filename_info.get("lang_hint")
    if lang_hint and lang_hint in ("vi", "en") and lang_hint != language:
        language, lang_conf, lang_method = lang_hint, 0.5, "filename"

    if use_llm:
        llm_result: dict | None = None
        try:
            llm_result = await _llm_extract(db, filename, lines, title)
        except LLMUnavailableError:
            logger.info("metadata_llm_skipped_no_provider filename=%s", filename)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("metadata_llm_invalid filename=%s error=%s", filename, exc)
        except Exception as exc:
            logger.exception("metadata_llm_failed filename=%s error=%s", filename, exc)
        if llm_result:
            if title is None and llm_result.get("title"):
                title, title_conf, title_method = llm_result["title"], 0.6, "llm"
            if category is None and llm_result.get("category"):
                category, cat_conf, cat_method = llm_result["category"], 0.5, "llm"
            if year is None and llm_result.get("year") is not None:
                year, year_conf, year_method = llm_result["year"], 0.5, "llm"
            if version is None and llm_result.get("version"):
                version, ver_conf, ver_method = llm_result["version"], 0.5, "llm"
            if department is None and llm_result.get("department"):
                department, dept_conf, dept_method = llm_result["department"], 0.5, "llm"
            if program is None and llm_result.get("program"):
                program, prog_conf, prog_method = llm_result["program"], 0.5, "llm"
            if llm_result.get("language") in ("vi", "en", "bilingual"):
                language, lang_conf, lang_method = llm_result["language"], 0.5, "llm"
            if description is None and llm_result.get("description"):
                description, desc_conf, desc_method = llm_result["description"], 0.5, "llm"

    return MetadataExtractionResult(
        filename=filename,
        title=MetadataField(value=title, confidence=_round_conf(title_conf), method=title_method),
        category=MetadataField(value=category, confidence=_round_conf(cat_conf), method=cat_method),
        year=MetadataField(value=year, confidence=_round_conf(year_conf), method=year_method),
        version=MetadataField(value=version, confidence=_round_conf(ver_conf), method=ver_method),
        department=MetadataField(value=department, confidence=_round_conf(dept_conf), method=dept_method),
        program=MetadataField(value=program, confidence=_round_conf(prog_conf), method=prog_method),
        language=MetadataField(value=language, confidence=_round_conf(lang_conf), method=lang_method),
        description=MetadataField(value=description, confidence=_round_conf(desc_conf), method=desc_method),
    )
