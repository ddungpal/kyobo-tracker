#!/usr/bin/env python3
"""
교보문고 온라인 일간 베스트셀러 순위 트래커
완벽한 원시인 (자청) 순위를 매일 수집해 CSV에 누적 저장
"""

import requests
import json
import csv
import os
from datetime import datetime, date

# ── 설정 ──────────────────────────────────────────────
BOOK_TITLE   = "완벽한 원시인"   # 찾을 책 제목 (부분 일치)
BOOK_AUTHOR  = "자청"            # 저자 (중복 제목 방지용)
CSV_FILE     = "rank_history.csv"
MAX_PAGES    = 5                 # 최대 탐색 페이지 (1페이지 = 20위)
PER_PAGE     = 20

API_URL = "https://store.kyobobook.co.kr/api/gw/best/best-seller/online"
PARAMS_BASE = {
    "per":              PER_PAGE,
    "period":           "001",   # 001=일간, 002=주간, 003=월간
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


def find_rank() -> int | None:
    """
    MAX_PAGES 페이지까지 검색 후 해당 책의 순위 반환.
    없으면 None.
    """
    for page in range(1, MAX_PAGES + 1):
        try:
            data = fetch_page(page)
        except Exception as e:
            print(f"  ⚠ 페이지 {page} 요청 실패: {e}")
            break

        # 응답 구조 탐색 (data.data.list 또는 data.list 등 사이트마다 다름)
        items = (
            data.get("data", {}).get("list")
            or data.get("data", {}).get("bestSellerList")
            or data.get("list")
            or []
        )

        if not items:
            print(f"  ℹ 페이지 {page}: 항목 없음, 검색 종료")
            break

        for item in items:
            title  = item.get("cmdtName", "") or item.get("title", "")
            author = item.get("author", "")   or item.get("wrterNm", "")
            rank   = item.get("ranking")      or item.get("rank")

            if BOOK_TITLE in title and BOOK_AUTHOR in author:
                return int(rank)

        print(f"  페이지 {page} 검색 완료 ({len(items)}권), 미발견")

    return None  # TOP {MAX_PAGES*PER_PAGE} 밖이거나 리스트 없음


def load_existing() -> dict[str, int]:
    """CSV에서 기존 날짜→순위 맵 로드"""
    records = {}
    if not os.path.exists(CSV_FILE):
        return records
    with open(CSV_FILE, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            records[row["date"]] = int(row["rank"]) if row["rank"] not in ("", "None") else -1
    return records


def save_csv(records: dict[str, int]):
    """날짜 오름차순으로 CSV 저장"""
    fieldnames = ["date", "rank", "note"]
    sorted_dates = sorted(records.keys())
    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in sorted_dates:
            r = records[d]
            note = ""
            if r == 0:
                note = "예약 1위"
            elif r == -1:
                note = "순위 없음"
            writer.writerow({"date": d, "rank": r, "note": note})


def main():
    today = date.today().isoformat()
    print(f"{'='*50}")
    print(f"  교보문고 순위 수집 — {today}")
    print(f"  대상: {BOOK_TITLE} / {BOOK_AUTHOR}")
    print(f"{'='*50}")

    records = load_existing()

    if today in records:
        print(f"  ✓ 오늘({today}) 기록 이미 존재: {records[today]}위")
        print("  덮어쓰려면 --force 옵션 사용")
        import sys
        if "--force" not in sys.argv:
            return

    print(f"  API 조회 중...")
    rank = find_rank()

    if rank is not None:
        print(f"\n  ✅ 순위 발견: {rank}위")
        records[today] = rank
    else:
        print(f"\n  ❌ TOP {MAX_PAGES * PER_PAGE} 내 미발견 → '순위 없음' 기록")
        records[today] = -1

    save_csv(records)
    print(f"  💾 저장 완료: {CSV_FILE} ({len(records)}건)")


if __name__ == "__main__":
    main()
