#!/usr/bin/env python3
"""
교보문고 온라인 일간 베스트셀러 순위 트래커
완벽한 원시인 (자청) 순위를 매일 수집해 CSV에 누적 저장
"""

import requests
import json
import csv
import os
from datetime import date

# ── 설정 ──────────────────────────────────────────────
BOOK_TITLE   = "완벽한 원시인"
BOOK_AUTHOR  = "자청"
CSV_FILE     = "rank_history.csv"
MAX_PAGES    = 5        # TOP 100 탐색 (1페이지=20위)
PER_PAGE     = 20

API_URL = "https://store.kyobobook.co.kr/api/gw/best/best-seller/online"
PARAMS_BASE = {
    "per":              PER_PAGE,
    "period":           "001",   # 001=일간
    "dsplDvsnCode":     "000",   # 000=전체
    "dsplTrgtDvsnCode": "001",   # 001=온라인
}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://store.kyobobook.co.kr/bestseller/online/daily",
    "Accept":  "application/json, text/plain, */*",
}
# ──────────────────────────────────────────────────────


def fetch_page(page: int) -> dict:
    params = {**PARAMS_BASE, "page": page}
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def extract_items(data: dict) -> list:
    """응답 JSON에서 도서 목록을 꺼냄 — 가능한 모든 경로 시도"""
    candidates = [
        data.get("data", {}).get("list"),
        data.get("data", {}).get("bestSellerList"),
        data.get("data", {}).get("productList"),
        data.get("data", {}).get("items"),
        data.get("list"),
        data.get("items"),
        data.get("result", {}).get("list") if isinstance(data.get("result"), dict) else None,
    ]
    for c in candidates:
        if c and isinstance(c, list) and len(c) > 0:
            return c
    return []


def get_field(item: dict, *keys):
    """여러 후보 키 중 처음으로 값이 있는 것 반환"""
    for k in keys:
        v = item.get(k)
        if v is not None and v != "":
            return str(v)
    return ""


def find_rank() -> int | None:
    for page in range(1, MAX_PAGES + 1):
        try:
            data = fetch_page(page)
        except Exception as e:
            print(f"  ⚠ 페이지 {page} 요청 실패: {e}")
            break

        # 디버그: 첫 페이지에서 응답 구조 출력
        if page == 1:
            print(f"\n  [디버그] 응답 최상위 키: {list(data.keys())}")
            if "data" in data:
                print(f"  [디버그] data 하위 키: {list(data['data'].keys()) if isinstance(data['data'], dict) else type(data['data'])}")

        items = extract_items(data)

        if not items:
            print(f"  ℹ 페이지 {page}: 항목을 찾지 못했습니다")
            if page == 1:
                print(f"  [디버그] 전체 응답:\n{json.dumps(data, ensure_ascii=False, indent=2)[:1000]}")
            break

        print(f"  페이지 {page}: {len(items)}권 검색 중...")

        for item in items:
            # 가능한 모든 제목/저자/순위 필드명 시도
            title  = get_field(item, "cmdtName", "title", "bookName", "prodName", "itemName")
            author = get_field(item, "author", "wrterNm", "authorName", "writer")
            rank   = get_field(item, "ranking", "rank", "rankNo", "no", "rowNum")

            if BOOK_TITLE in title:
                print(f"\n  ✅ 발견! 제목: {title} / 저자: {author} / 순위: {rank}")
                try:
                    return int(rank)
                except:
                    # rank 필드가 없으면 페이지+위치로 계산
                    idx = items.index(item)
                    return (page - 1) * PER_PAGE + idx + 1

        print(f"  → '{BOOK_TITLE}' 미발견")

    return None


def load_existing() -> dict:
    records = {}
    if not os.path.exists(CSV_FILE):
        return records
    with open(CSV_FILE, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                r = int(row["rank"])
            except:
                r = -1
            records[row["date"]] = r
    return records


def save_csv(records: dict):
    fieldnames = ["date", "rank", "note"]
    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in sorted(records.keys()):
            r = records[d]
            note = "예약 1위" if r == 0 else "순위 없음" if r == -1 else ""
            writer.writerow({"date": d, "rank": r, "note": note})


def main():
    import sys
    today = date.today().isoformat()
    print(f"{'='*50}")
    print(f"  교보문고 순위 수집 — {today}")
    print(f"  대상: {BOOK_TITLE} / {BOOK_AUTHOR}")
    print(f"{'='*50}")

    records = load_existing()

    if today in records and "--force" not in sys.argv:
        print(f"  ✓ 오늘({today}) 기록 이미 존재: {records[today]}")
        print("  덮어쓰려면 --force 옵션 사용")
        return

    print(f"  API 조회 중...\n")
    rank = find_rank()

    if rank is not None:
        print(f"\n  결과: {rank}위")
        records[today] = rank
    else:
        print(f"\n  TOP {MAX_PAGES * PER_PAGE} 내 미발견 → '순위 없음' 기록")
        records[today] = -1

    save_csv(records)
    print(f"  💾 저장 완료: {CSV_FILE} ({len(records)}건)")


if __name__ == "__main__":
    main()
