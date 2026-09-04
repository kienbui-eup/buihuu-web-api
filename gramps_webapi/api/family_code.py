"""Mã dòng họ: mở cây gia phả bằng họ tên của một người trong cây.

Mã là họ tên đầy đủ của bất kỳ người nào có trong cây, viết liền, không phân
biệt hoa thường. Máy chủ chuẩn hóa cả mã gõ vào lẫn tên trong cây theo cùng
một cách (bỏ dấu, bỏ khoảng trắng và dấu câu, chữ thường), nên "Bui Van A",
"bùivăna" hay "BÙI VĂN A" đều là một mã. Khớp thì cấp token cho tài khoản khách
chỉ xem đặt trong cấu hình FAMILY_CODE_USERNAME; người xem không cần biết mật
khẩu của tài khoản đó.

Tập mã của một cây tính từ mọi tên (tên chính và tên khác) của mọi người, kể
cả người được đánh dấu riêng tư, vì việc so khớp diễn ra ở máy chủ và không
lộ tên nào ra ngoài. Tập này được giữ trong bộ nhớ vài phút để mỗi lần đăng
nhập không phải duyệt lại cả cây.
"""

from __future__ import annotations

import re
import threading
import time
import unicodedata
from typing import Iterable

from gramps.gen.db import DbReadBase
from gramps.gen.lib import Name

from .util import close_db, get_db_outside_request

# Mã ngắn hơn ngưỡng này không nhận: tên một chữ hay tên trống ("?", "…")
# sau khi chuẩn hóa còn quá ít ký tự để làm mã.
MIN_CODE_LENGTH = 6
# Tên còn để trống hoặc chưa rõ trong sổ được ghi bằng các dấu này.
PLACEHOLDER_MARKS = ("?", "…", "...")
# Tập mã giữ trong bộ nhớ chừng này giây rồi mới duyệt lại cây.
CACHE_SECONDS = 300

_cache: dict[str, tuple[float, frozenset[str]]] = {}
_cache_lock = threading.Lock()


def normalize_code(text: str | None) -> str:
    """Chuẩn hóa mã hoặc tên: bỏ dấu, đ thành d, chữ thường, chỉ giữ chữ số."""
    decomposed = unicodedata.normalize("NFD", text or "")
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    # Đ/đ không tách được bằng NFD nên đổi riêng.
    without_marks = without_marks.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"[^0-9a-z]", "", without_marks.lower())


def _surname_text(name: Name) -> str:
    parts = []
    for surname in name.get_surname_list():
        for piece in (
            surname.get_prefix(),
            surname.get_surname(),
            surname.get_connector(),
        ):
            if piece and piece.strip():
                parts.append(piece.strip())
    return " ".join(parts)


def name_variants(name: Name) -> Iterable[str]:
    """Các cách viết họ tên đầy đủ của một tên: họ trước tên và tên trước họ."""
    given = (name.get_first_name() or "").strip()
    surname = _surname_text(name)
    if given and surname:
        yield f"{surname} {given}"
        yield f"{given} {surname}"
    elif given or surname:
        yield given or surname


def person_codes(db: DbReadBase) -> frozenset[str]:
    """Tập mã hợp lệ của một cây: mọi tên của mọi người, đã chuẩn hóa."""
    codes: set[str] = set()
    for person in db.iter_people():
        for name in (person.get_primary_name(), *person.get_alternate_names()):
            for full_name in name_variants(name):
                if any(mark in full_name for mark in PLACEHOLDER_MARKS):
                    continue
                code = normalize_code(full_name)
                if len(code) >= MIN_CODE_LENGTH:
                    codes.add(code)
    return frozenset(codes)


def tree_codes(tree: str, user_id: str) -> frozenset[str]:
    """Tập mã của một cây, lấy từ bộ nhớ nếu còn mới."""
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(tree)
        if cached and now - cached[0] < CACHE_SECONDS:
            return cached[1]
    db = get_db_outside_request(
        tree=tree, view_private=True, readonly=True, user_id=user_id
    )
    try:
        codes = person_codes(db)
    finally:
        close_db(db)
    with _cache_lock:
        _cache[tree] = (now, codes)
    return codes


def clear_cache() -> None:
    """Bỏ tập mã đã nhớ (dùng cho kiểm thử)."""
    with _cache_lock:
        _cache.clear()


def family_code_matches(tree: str, user_id: str, code: str) -> bool:
    """Mã gõ vào có là họ tên của một người trong cây không."""
    normalized = normalize_code(code)
    if len(normalized) < MIN_CODE_LENGTH:
        return False
    return normalized in tree_codes(tree, user_id)
