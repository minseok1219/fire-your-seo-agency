#!/usr/bin/env python3
"""
네이버 스마트플레이스 진단 스크립트 (SPO 레인)

공개 플레이스 페이지(m.place.naver.com)가 SSR로 내려주는 window.__APOLLO_STATE__를
읽어 "크롤러의 눈"으로 업체 정보 완성도·리뷰·소식·전환 경로를 점검한다.
로그인·API 키 불필요. 표준 라이브러리만 사용.

사용:
  python3 scripts/place-audit.py https://naver.me/xxxx
  python3 scripts/place-audit.py https://m.place.naver.com/place/1790538774/home
  python3 scripts/place-audit.py 1790538774 --json

주의: 네이버 마크업은 예고 없이 바뀐다. 필드가 비면 스크립트 문제인지 실제 누락인지
      브라우저로 한 번 교차 확인하라.
"""
import json
import re
import subprocess
import sys
from datetime import date, datetime

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")


def fetch(url):
    """curl로 받는다 — 스킬의 '크롤러의 눈' 기준과 동일하고, 파이썬 인증서 설정에 안 흔들린다."""
    marker = "\n__FINAL_URL__:"
    out = subprocess.run(
        ["curl", "-sL", "--max-time", "20", "-A", UA, "-w", marker + "%{url_effective}", url],
        capture_output=True, check=True,
    ).stdout.decode("utf-8", "replace")
    body, _, final = out.rpartition(marker)
    return final.strip(), body


def resolve_place_id(arg):
    if re.fullmatch(r"\d+", arg):
        return arg
    m = re.search(r"place/(\d+)", arg) or re.search(r"[?&]id=(\d+)", arg)
    if m:
        return m.group(1)
    final, _ = fetch(arg)
    m = re.search(r"place/(\d+)", final) or re.search(r"[?&](?:id|pinId)=(\d+)", final)
    if not m:
        sys.exit(f"플레이스 ID를 찾지 못했습니다: {final}")
    return m.group(1)


def apollo(html):
    m = re.search(r"window\.__APOLLO_STATE__\s*=\s*(\{.*?\});\s*(?:window\.|</script>)", html, re.S)
    return json.loads(m.group(1)) if m else {}


def first(ap, prefix):
    for k, v in ap.items():
        if k.startswith(prefix):
            return v
    return {}


def parse_date(s):
    if not s:
        return None
    s = re.sub(r"[^\d]", "", s)[:8]
    try:
        return datetime.strptime(s, "%Y%m%d").date()
    except ValueError:
        return None


def audit(place_id):
    base = f"https://m.place.naver.com/place/{place_id}"
    _, home_html = fetch(f"{base}/home")
    _, feed_html = fetch(f"{base}/feed")
    home, feed = apollo(home_html), apollo(feed_html)
    if not home:
        sys.exit("__APOLLO_STATE__를 찾지 못했습니다. 마크업이 바뀌었거나 차단된 요청입니다.")

    b = first(home, "PlaceDetailBase:")
    if not b.get("name"):
        sys.exit(f"플레이스 {place_id}의 업체 정보가 없습니다 — ID가 틀렸거나 폐업/비공개 처리된 업체입니다.")
    stats = first(home, "VisitorReviewStatsResult:").get("review", {}) or {}
    themes = (first(home, "VisitorReviewStatsResult:").get("analysis") or {}).get("themes") or []
    menus = [v for k, v in home.items() if k.startswith("Menu:")]
    photos = [v for k, v in home.items() if k.startswith("PlaceDetailTopPhotoItem:")]
    tabs = []
    for k, v in (home.get("ROOT_QUERY") or {}).items():
        if k.startswith("placeDetail(") and isinstance(v, dict):
            tabs = [t.get("tabId") for t in v.get("tabs", [])]

    feeds = [v for k, v in feed.items() if k.startswith("Feed:")]
    owner_feeds = [f for f in feeds if str(f.get("feedId", "")).isdigit() and f.get("blogId") in (None, "")]
    blog_feeds = [f for f in feeds if f.get("blogId")]
    feed_dates = sorted([d for d in (parse_date(f.get("createdString")) for f in owner_feeds) if d], reverse=True)
    today = date.today()
    recent_90 = [d for d in feed_dates if (today - d).days <= 90]

    missing = b.get("missingInfo") or {}
    og_title = re.search(r'property="og:title" content="([^"]*)"', home_html)
    title_tag = re.search(r"<title>([^<]*)</title>", home_html)

    data = {
        "place_id": place_id,
        "url": f"{base}/home",
        "name": b.get("name"),
        "og_title": re.sub(r"[\x00-\x1f]", "", og_title.group(1)) if og_title else None,
        "title_tag": title_tag.group(1) if title_tag else None,
        "json_ld_blocks": len(re.findall(r'application/ld\+json', home_html)),
        "category": b.get("category"),
        "category_codes": len(b.get("categoryCodeList") or []),
        "road_address": b.get("roadAddress"),
        "directions": b.get("road"),
        "phone": b.get("phone"),
        "virtual_phone": b.get("virtualPhone"),
        "opening_hours": b.get("openingHours"),
        # 소개글·대표키워드·홈페이지/SNS는 SSR에 실리지 않는다 (클라이언트 GraphQL로 후속 로드).
        # 실측 2026-09: 아폴로 캐시에 없음 → 스마트플레이스 센터에서 수동 확인 항목으로 둔다.
        "ssr_hidden_fields": ["소개글", "대표키워드", "홈페이지/SNS 링크"],
        "conveniences": b.get("conveniences") or [],
        "payment": b.get("paymentInfo") or [],
        "talktalk": b.get("talktalkUrl"),
        "naver_blog": (b.get("naverBlog") or {}).get("__ref"),
        "tabs": tabs,
        "missing_info_flags": {k: v for k, v in missing.items() if k.startswith("is") and v is True},
        "menus": [{"name": m.get("name"), "price": m.get("price")} for m in menus],
        "reviews": {
            "visitor_total": b.get("visitorReviewsTotal"),
            "visitor_text": b.get("visitorReviewsTextReviewTotal"),
            "visitor_with_image": stats.get("imageReviewCount"),
            "avg_rating": stats.get("avgRating"),
            "blog_cafe_total": b.get("cafeBlogReviewsTotal"),
            "themes": [(t.get("label"), t.get("count")) for t in themes[:5]],
        },
        "feed": {
            "owner_posts": len(owner_feeds),
            "blog_synced_posts": len(blog_feeds),
            "latest_owner_post": feed_dates[0].isoformat() if feed_dates else None,
            "owner_posts_last_90d": len(recent_90),
            "categories": sorted({f.get("category") for f in owner_feeds if f.get("category")}),
        },
        "media": {
            # 홈 상단 대표 영역(약 10칸)에 노출된 것만 센다 — 전체 수량은 사진 탭에서 수동 확인
            "top_area_slots": len(photos),
            "business_photos_in_top": sum(1 for p in photos if p.get("mediaSource") == "business"),
            "clips_in_top": sum(1 for p in photos if p.get("mediaSource") == "clip"),
        },
    }
    return data


def score(d):
    rows = []

    def row(lane, status, why):
        rows.append((lane, status, why))

    # 기본 정보
    flags = d["missing_info_flags"]
    if d["opening_hours"] is None or flags.get("isBizHourMissing"):
        row("기본정보", "❌", "영업시간 누락 (네이버가 missingInfo로 직접 플래그) — 순위·전환 모두 감점")
    elif flags:
        row("기본정보", "⚠️", f"네이버 누락 플래그: {', '.join(flags)}")
    else:
        row("기본정보", "✅", "영업시간·주소·찾아오는길·편의시설 채워짐")

    row("소개·키워드", "🔎", "SSR 미노출 — 센터 > 업체정보에서 소개글(지역+업종 자연 포함)·대표키워드 5개 채움 여부 수동 확인")

    # 상품/가격
    priced = [m for m in d["menus"] if m["price"]]
    if not d["menus"]:
        row("상품·가격", "❌", "가격표 없음 — '얼마예요' 질문에 답 못함")
    elif len(priced) < len(d["menus"]) / 2:
        row("상품·가격", "⚠️", f"상품 {len(d['menus'])}개 중 가격 표기 {len(priced)}개")
    else:
        row("상품·가격", "✅", f"상품 {len(d['menus'])}개, 가격 표기 {len(priced)}개")

    # 리뷰
    r = d["reviews"]
    vt = r["visitor_total"] or 0
    if vt < 10:
        row("리뷰", "❌", f"방문자 리뷰 {vt}건 — 신뢰 하한선 미달")
    elif vt < 50:
        row("리뷰", "⚠️", f"방문자 리뷰 {vt}건 · 블로그 {r['blog_cafe_total']}건")
    else:
        row("리뷰", "✅", f"방문자 {vt}건(사진 {r['visitor_with_image']}) · 블로그 {r['blog_cafe_total']}건 · 평점 {r['avg_rating']}")

    # 소식
    f = d["feed"]
    if f["owner_posts"] == 0:
        row("소식", "❌", "업체 소식 0건 — 신선도 신호 없음")
    elif f["owner_posts_last_90d"] < 3:
        row("소식", "⚠️", f"최근 90일 소식 {f['owner_posts_last_90d']}건 (최근 {f['latest_owner_post']}) — 월 2회 이상 권장")
    else:
        row("소식", "✅", f"최근 90일 소식 {f['owner_posts_last_90d']}건 · 블로그 연동 {f['blog_synced_posts']}건")

    # 전환 경로
    conv = []
    if d["talktalk"]:
        conv.append("톡톡")
    if "ticket" in d["tabs"] or "booking" in d["tabs"]:
        conv.append("예약")
    if d["virtual_phone"] or d["phone"]:
        conv.append("전화")
    if len(conv) >= 3:
        row("전환경로", "✅", " · ".join(conv))
    elif conv:
        row("전환경로", "⚠️", f"{' · '.join(conv)}만 있음 — 예약/톡톡/전화 셋 다 열어라")
    else:
        row("전환경로", "❌", "예약·톡톡·전화 모두 없음")

    # 사진/영상
    m = d["media"]
    bp, cl = m["business_photos_in_top"], m["clips_in_top"]
    if bp == 0:
        row("사진·영상", "❌", "홈 대표 영역에 업체 등록 사진 0장 — 방문자 사진만 노출 중")
    elif bp < 3:
        row("사진·영상", "⚠️", f"홈 대표 영역 업체 사진 {bp}장 · 클립 {cl}건 — 대표 영역이 방문자 사진에 밀림, 전체 수량은 사진 탭 확인")
    else:
        row("사진·영상", "✅", f"홈 대표 영역 업체 사진 {bp}장 · 클립 {cl}건 (전체 수량은 사진 탭에서 수동 확인)")

    # 외부 연결
    if d["naver_blog"]:
        row("외부연결", "✅", f"네이버 블로그 연동 {d['naver_blog'].split(':')[-1]} · 홈페이지/SNS는 SSR 미노출(수동 확인)")
    else:
        row("외부연결", "⚠️", "네이버 블로그 미연동 · 홈페이지/SNS는 SSR 미노출(수동 확인) — 엔티티 sameAs 근거 부족")

    return rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    d = audit(resolve_place_id(args[0]))
    if "--json" in sys.argv:
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return
    print(f"# {d['name']}  ({d['url']})")
    print(f"카테고리: {d['category']} · 주소: {d['road_address']} · 찾아오는길: {d['directions']}")
    print(f"<title>: {d['title_tag']!r} · og:title: {d['og_title']!r} · JSON-LD: {d['json_ld_blocks']}건")
    print(f"SSR 미노출(수동 확인 필요): {', '.join(d['ssr_hidden_fields'])}")
    print()
    print("범례: ✅ 충족 · ⚠️ 보완 · ❌ 누락 · 🔎 SSR로 확인 불가, 센터에서 수동 점검")
    print()
    print("| 항목 | 상태 | 근거 |")
    print("|---|---|---|")
    for lane, status, why in score(d):
        print(f"| {lane} | {status} | {why} |")
    print()
    print("상품:", "; ".join(f"{m['name']}={m['price'] or '문의'}" for m in d["menus"]) or "없음")
    print("리뷰 테마:", ", ".join(f"{l} {c}" for l, c in d["reviews"]["themes"]) or "없음")
    print("소식 카테고리:", ", ".join(d["feed"]["categories"]) or "없음")
    print("편의시설:", ", ".join(d["conveniences"]) or "없음")
    print("결제:", ", ".join(d["payment"]) or "없음")


if __name__ == "__main__":
    main()
