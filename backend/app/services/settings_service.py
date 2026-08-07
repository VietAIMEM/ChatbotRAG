from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.rag import AppSetting
from app.rag.prompts import DEFAULT_WELCOME_MESSAGE
from app.schemas.settings import (
    GeneralSettingsUpdate,
    MetadataCategorySettings,
    MetadataSettingsUpdate,
    SecuritySettingsUpdate,
)

GENERAL_KEYS = ("site_name", "chatbot_name", "welcome_message")
SECURITY_KEYS = ("chat_rate_limit_per_minute", "max_upload_size_mb")
METADATA_KEYS = ("metadata_categories", "metadata_departments", "metadata_programs")

_DEFAULT_GENERAL = {
    "site_name": "Postgraduate Information Assistant",
    "chatbot_name": "Postgraduate Information Assistant",
    "welcome_message": DEFAULT_WELCOME_MESSAGE,
}

_DEFAULT_SECURITY = {
    "chat_rate_limit_per_minute": settings.CHAT_RATE_LIMIT_PER_MINUTE,
    "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
}

_DEFAULT_METADATA = {
    "metadata_categories": [
        {"name": "Admission", "keywords": ["tuyển sinh", "xét tuyển", "thí sinh", "chỉ tiêu", "đăng ký dự tuyển", "hồ sơ dự tuyển", "admission", "applicant", "enrollment", "enrolment"]},
        {"name": "Tuition", "keywords": ["học phí", "lệ phí", "kinh phí", "biểu phí", "tuition", "fee", "fees"]},
        {"name": "Training Regulation", "keywords": ["quy chế đào tạo", "quy định đào tạo", "đào tạo trình độ", "tổ chức đào tạo", "training regulation"]},
        {"name": "Scholarship", "keywords": ["học bổng", "hỗ trợ tài chính", "trợ cấp", "scholarship", "financial aid", "fellowship"]},
        {"name": "Curriculum", "keywords": ["chương trình đào tạo", "khung chương trình", "môn học", "học phần", "đề cương", "curriculum", "syllabus", "course"]},
        {"name": "Academic Regulation", "keywords": ["quy chế học vụ", "quy định học tập", "học vụ", "xếp loại", "kiểm tra", "thi", "đánh giá", "academic regulation", "grading", "thesis", "luận văn"]},
        {"name": "Application Procedure", "keywords": ["quy trình nộp hồ sơ", "thủ tục", "nộp hồ sơ", "hồ sơ", "giấy tờ", "application procedure", "procedures", "documents required"]},
        {"name": "Program Information", "keywords": ["thông tin chương trình", "giới thiệu chương trình", "ngành đào tạo", "mã ngành", "chuẩn đầu ra", "program information", "programme information"]},
        {"name": "Graduation", "keywords": ["tốt nghiệp", "điều kiện tốt nghiệp", "bằng tốt nghiệp", "đồ án tốt nghiệp", "luận văn tốt nghiệp", "graduation", "degree"]},
    ],
    "metadata_departments": [
        "Phòng Đào tạo",
        "Phòng Đào tạo Sau đại học",
        "Phòng Khảo thí & Đảm bảo chất lượng",
        "Phòng Công tác sinh viên",
        "Phòng Tài chính - Kế toán",
        "Viện Đào tạo Sau đại học",
        "Viện Nghiên cứu",
        "Trung tâm Đào tạo Quốc tế",
        "Faculty of Information Technology",
        "Faculty of Postgraduate Studies",
        "Graduate School",
        "Department of Academic Affairs",
    ],
    "metadata_programs": [
        "Thạc sĩ Công nghệ thông tin",
        "Thạc sĩ Quản trị kinh doanh",
        "Thạc sĩ Kinh tế",
        "Thạc sĩ Tài chính - Ngân hàng",
        "Tiến sĩ Công nghệ thông tin",
        "Master of Computer Science",
        "Master of Business Administration",
        "MBA",
        "PhD in Computer Science",
    ],
}


async def _load_keys(db: AsyncSession, keys: tuple[str, ...]) -> dict:
    result = await db.execute(select(AppSetting).where(AppSetting.key.in_(keys)))
    return {row.key: row.value for row in result.scalars().all()}


async def load_general(db: AsyncSession) -> GeneralSettingsUpdate:
    values = await _load_keys(db, GENERAL_KEYS)
    return GeneralSettingsUpdate(
        site_name=values.get("site_name", _DEFAULT_GENERAL["site_name"]),
        chatbot_name=values.get("chatbot_name", _DEFAULT_GENERAL["chatbot_name"]),
        welcome_message=values.get("welcome_message", _DEFAULT_GENERAL["welcome_message"]),
    )


async def load_security(db: AsyncSession) -> SecuritySettingsUpdate:
    values = await _load_keys(db, SECURITY_KEYS)
    return SecuritySettingsUpdate(
        chat_rate_limit_per_minute=values.get(
            "chat_rate_limit_per_minute", _DEFAULT_SECURITY["chat_rate_limit_per_minute"]
        ),
        max_upload_size_mb=values.get("max_upload_size_mb", _DEFAULT_SECURITY["max_upload_size_mb"]),
    )


async def load_public_settings(db: AsyncSession) -> dict:
    general = await load_general(db)
    return {
        "site_name": general.site_name,
        "chatbot_name": general.chatbot_name,
        "welcome_message": general.welcome_message,
    }


async def save_general(db: AsyncSession, values: dict) -> GeneralSettingsUpdate:
    merged = {**_DEFAULT_GENERAL, **values}
    for key, value in merged.items():
        if key not in GENERAL_KEYS:
            continue
        row = await db.get(AppSetting, key)
        if row is None:
            db.add(AppSetting(key=key, value=value))
        else:
            row.value = value
    await db.commit()
    return await load_general(db)


async def save_security(db: AsyncSession, values: dict) -> SecuritySettingsUpdate:
    merged = {**_DEFAULT_SECURITY, **values}
    for key, value in merged.items():
        if key not in SECURITY_KEYS:
            continue
        row = await db.get(AppSetting, key)
        if row is None:
            db.add(AppSetting(key=key, value=value))
        else:
            row.value = value
    await db.commit()
    return await load_security(db)


async def load_metadata(db: AsyncSession) -> MetadataSettingsUpdate:
    values = await _load_keys(db, METADATA_KEYS)
    categories = values.get("metadata_categories") or _DEFAULT_METADATA["metadata_categories"]
    departments = values.get("metadata_departments") or _DEFAULT_METADATA["metadata_departments"]
    programs = values.get("metadata_programs") or _DEFAULT_METADATA["metadata_programs"]
    return MetadataSettingsUpdate(
        categories=[
            MetadataCategorySettings(**item) if isinstance(item, dict) else item
            for item in categories
        ],
        departments=[str(item) for item in departments],
        programs=[str(item) for item in programs],
    )


async def _upsert_setting(db: AsyncSession, key: str, value: object) -> None:
    row = await db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value


async def save_metadata(db: AsyncSession, values: dict) -> MetadataSettingsUpdate:
    categories = values.get("categories")
    if categories is not None:
        cleaned = [
            {"name": str(item["name"]), "keywords": [str(k) for k in item.get("keywords", [])]}
            for item in categories
        ]
        await _upsert_setting(db, "metadata_categories", cleaned)
    departments = values.get("departments")
    if departments is not None:
        await _upsert_setting(db, "metadata_departments", [str(item) for item in departments])
    programs = values.get("programs")
    if programs is not None:
        await _upsert_setting(db, "metadata_programs", [str(item) for item in programs])
    await db.commit()
    return await load_metadata(db)
