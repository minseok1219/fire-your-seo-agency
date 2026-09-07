#!/usr/bin/env python3
"""
카카오맵 진단 스크립트 (KMO 레인)

카카오맵 공개 검색 엔드포인트와 플레이스 패널 API(로그인·키 불필요)를 읽어
"크롤러의 눈"으로 업체 정보·가격·리뷰·소식·전환 경로를 점검하고,
--naver 를 주면 네이버 스마트플레이스 진단 결과와 필드별로 대조한다(NAP 일관성).
표준 라이브러리 + curl만 사용.

사용:
  python3 scripts/kakao-audit.py --name "크로스핏 에이블 거여"          # 이름으로 검색 → 첫 결과 진단
  python3 scripts/kakao-audit.py https://place.map.kakao.com/641759795
  python3 scripts/kakao-audit.py 641759795 --naver https://naver.me/xxxx  # 네이버와 대조
  python3 scripts/kakao-audit.py 641759795 --json

주의: 카카오 엔드포인트는 비공식이다(웹 지도가 쓰는 것). 헤더가 바뀌면 깨질 수 있다 —
      406/404가 나오면 place.map.kakao.com 페이지를 브라우저 개발자도구로 열어 요청 헤더를 다시 맞춰라.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import date, datetime

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
DAYS = ["월", "화", "수", "목", "금", "토", "일"]


def curl_json(url, headers):
    cmd = ["curl", "-s", "--max-time", "20", "-A", UA]
    for h in headers:
        cmd += ["-H", h]
    cmd.append(url)
    out = subprocess.run(cmd, capture_output=True, check=True).stdout.decode("utf-8", "replace")
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        sys.exit(f"JSON이 아닌 응답: {url}\n{out[:300]}")


def search(name):
    q = urllib.parse.quote(name)
    d = curl_json(f"https://search.map.kakao.com/mapsearch/map.daum?q={q}&msFlag=A&sort=0",
                  ["Referer: https://map.kakao.com/"])
    return [{"id": p.get("confirmid"), "name": p.get("name"), "address": p.get("address")}
            for p in d.get("place") or []]


def resolve_id(arg):
    if re.fullmatch(r"\d+", arg):
        return arg
    m = re.search(r"kakao\.com/(\d+)", arg) or re.search(r"[?&](?:itemId|confirmid)=(\d+)", arg)
    if not m:
        sys.exit(f"카카오 플레이스 ID를 찾지 못했습니다: {arg}")
    return m.group(1)


def panel(place_id):
    return curl_json(f"https://place-api.map.kakao.com/places/panel3/{place_id}",
                     ["Accept: application/json", "Referer: https://place.map.kakao.com/",
                      "Origin: https://place.map.kakao.com", "pf: web"])


def parse_date(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def audit(place_id):
    d = panel(place_id)
    s = d.get("summary") or {}
    if not s.get("name"):
        sys.exit(f"카카오 플레이스 {place_id}의 업체 정보가 없습니다 — ID가 틀렸거나 비공개 업체입니다.")

    # 영업시간: 기본 영업시간 periods[0].days + all_days_off_info
    oh = d.get("open_hours") or {}
    hours = {}
    for p in (oh.get("all") or {}).get("periods") or []:
        for day in p.get("days") or []:
            hours[day.get("day_of_the_week")] = (day.get("on_days") or {}).get("start_end_time_desc") or day.get("off_days_desc")
    days_off = (oh.get("all") or {}).get("all_days_off_info") or ""
    days_filled = sum(1 for day in DAYS if hours.get(day) or (day in days_off))

    menus = ((d.get("menu") or {}).get("menus") or {})
    items = [{"name": m.get("name"), "price": m.get("price"), "photo": bool(m.get("photo_url"))}
             for m in menus.get("items") or []]
    menu_updated = parse_date(menus.get("items_updated_at"))

    kr = d.get("kakaomap_review") or {}
    br = d.get("blog_review") or {}
    notice = d.get("my_store_notice") or {}
    photos = (d.get("photos") or {}).get("counts") or {}
    tickets = list(dict.fromkeys(t.get("name") for st in (d.get("available_tickets") or {}).get("stores") or []
                                 for t in st.get("tickets") or []))
    talk = d.get("talk_channel") or {}
    addr = s.get("address") or {}
    fw = (d.get("find_way") or {}).get("subway") or {}
    links = s.get("homepages") or []

    return {
        "place_id": place_id,
        "url": f"https://place.map.kakao.com/{place_id}",
        "name": s.get("name"),
        "category": ((s.get("category") or {}).get("name")),
        "category_path": " > ".join(x for x in [(s.get("category") or {}).get("name1"), (s.get("category") or {}).get("name2")] if x),
        "road_address": addr.get("road"),
        "jibun_address": addr.get("jibun"),
        "directions": f"{fw.get('station_simple_name')} {fw.get('exit_num')}번 출구 {fw.get('to_exit_distance')}m" if fw.get("station_simple_name") else None,
        "phone": [p.get("tel") for p in s.get("phone_numbers") or []],
        "links": links,
        "instagram": next((u for u in links if "instagram.com" in u), None),
        "naver_blog": next((u for u in links if "blog.naver.com" in u), None),
        "homepage": next((u for u in links if "instagram.com" not in u and "blog.naver.com" not in u), None),
        "payments": [p.get("image_keyword") for p in s.get("payments") or []],
        "tags": ((d.get("place_add_info") or {}).get("tags")) or [],
        "parking": ((d.get("place_add_info") or {}).get("facilities") or {}).get("is_parking"),
        "info_updated_at": (s.get("meta") or {}).get("updated_at"),
        "business_hours": {"status": (oh.get("headline") or {}).get("display_text"),
                           "days": {day: hours.get(day) for day in DAYS},
                           "days_off": days_off, "days_filled": days_filled},
        "menus": items,
        "menu_updated_at": menu_updated.isoformat() if menu_updated else None,
        "reviews": {"kakaomap_count": kr.get("score_set", {}).get("review_count", 0),
                    "kakaomap_avg": kr.get("score_set", {}).get("average_score"),
                    "blog_count": br.get("review_count", 0),
                    "blog_last_at": (br.get("last_registered_at") or "")[:10] or None},
        "notice": {"store_registered": notice.get("status") == "REGISTERED",
                   "count": notice.get("notice_count", 0)},
        "conversion": {"talk_channel": talk.get("channel_home_web_link"),
                       "talk_friends": talk.get("friend_count"),
                       "booking": bool((d.get("reservation") or {}).get("booking_web_view_url")),
                       "tickets": tickets, "phone": bool(s.get("phone_numbers"))},
        "photos": {"total": photos.get("total", 0), "owner": photos.get("mystore", 0),
                   "indoor": photos.get("indoor", 0), "outdoor": photos.get("outdoor", 0),
                   "menu": photos.get("menu", 0)},
    }


def score(d):
    rows = []
    row = lambda lane, st, why: rows.append((lane, st, why))
    h = d["business_hours"]
    if h["days_filled"] == 0:
        row("기본정보", "❌", "영업시간 미등록")
    elif h["days_filled"] < 7:
        row("기본정보", "⚠️", f"영업시간 {h['days_filled']}/7일 — 빈 요일은 휴무로 명시")
    else:
        row("기본정보", "✅", f"영업시간 7/7일 · 휴무 '{h['days_off']}' · 현재 '{h['status']}' · 주소·찾아오는길 있음")
    if not d["notice"]["store_registered"]:
        row("매장관리", "❌", "카카오 매장관리 미등록 — 정보 수정·소식·예약 전부 불가. 여기부터")
    else:
        row("매장관리", "✅", f"매장관리 등록됨 · 정보 갱신 {d['info_updated_at']}")

    priced = [m for m in d["menus"] if m["price"]]
    age = (date.today() - parse_date(d["menu_updated_at"])).days if d["menu_updated_at"] else None
    if not d["menus"]:
        row("상품·가격", "❌", "가격표 없음")
    else:
        stale = f" · 마지막 갱신 {d['menu_updated_at']} ({age}일 전)" if age is not None else ""
        st = "⚠️" if (age or 0) > 365 or len(priced) < len(d["menus"]) / 2 else "✅"
        row("상품·가격", st, f"상품 {len(d['menus'])}개, 가격 표기 {len(priced)}개{stale}")

    r = d["reviews"]
    if r["kakaomap_count"] == 0:
        row("리뷰", "❌", f"카카오맵 리뷰 0건 (블로그 {r['blog_count']}건) — 채널이 비어 있음, 후기 요청 QR에 카카오맵 추가")
    elif r["kakaomap_count"] < 10:
        row("리뷰", "⚠️", f"카카오맵 리뷰 {r['kakaomap_count']}건 · 블로그 {r['blog_count']}건")
    else:
        row("리뷰", "✅", f"카카오맵 리뷰 {r['kakaomap_count']}건(평점 {r['kakaomap_avg']}) · 블로그 {r['blog_count']}건")

    n = d["notice"]["count"]
    row("소식", "❌" if n == 0 else "✅", f"매장 소식 {n}건" + (" — 네이버 소식을 그대로 복제 발행하라" if n == 0 else ""))

    c = d["conversion"]
    paths = [x for x, ok in (("톡채널", bool(c["talk_channel"])), ("예약", c["booking"]), ("전화", c["phone"])) if ok]
    row("전환경로", "✅" if len(paths) == 3 else ("⚠️" if paths else "❌"),
        " · ".join(paths) + (f" · 톡채널 친구 {c['talk_friends']}" if c["talk_friends"] is not None else "")
        + (f" · 예약상품 {', '.join(c['tickets'])}" if c["tickets"] else ""))

    p = d["photos"]
    row("사진", "❌" if p["owner"] == 0 else ("⚠️" if p["owner"] < 5 else "✅"),
        f"매장주 사진 {p['owner']}장 / 전체 {p['total']}장 (실내 {p['indoor']} · 실외 {p['outdoor']})")

    lk = [x for x, v in (("홈페이지", d["homepage"]), ("인스타그램", d["instagram"]), ("네이버 블로그", d["naver_blog"])) if v]
    row("외부연결", "✅" if len(lk) >= 2 else ("⚠️" if lk else "❌"), " · ".join(lk) or "링크 없음")
    return rows


def load_naver(arg):
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("place_audit", os.path.join(here, "place-audit.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.audit(mod.resolve_place_id(arg))


def norm(s):
    return re.sub(r"\s+", "", str(s or "")).lower()


def compare(k, n):
    """카카오 vs 네이버 — 같아야 하는 필드를 대조한다."""
    out = []

    def cmp(field, kv, nv, same=None, note="", warn=False):
        same = (norm(kv) == norm(nv)) if same is None else same
        out.append((field, kv, nv, "✅" if same else ("⚠️" if warn else "❌"), note))

    # 업체명은 띄어쓰기까지 글자 그대로 비교한다 — "크로스핏에이블" vs "크로스핏 에이블"은 다른 표기다
    exact = (k["name"] or "").strip() == (n["name"] or "").strip()
    cmp("업체명", k["name"], n["name"], same=exact,
        note="" if exact else ("띄어쓰기만 다름 — 한쪽에 맞춰라" if norm(k["name"]) == norm(n["name"]) else "표기 자체가 다름"))
    core = lambda a: (re.search(r"^(.*?(?:로|길)\s*\d+(?:-\d+)?)", a or "") or [None, ""])[1]
    kc, nc = core(k["road_address"]), core(n["road_address"])
    if norm(kc) == norm(nc) and kc:
        detail_same = norm(k["road_address"]) == norm(n["road_address"])
        cmp("도로명 주소", k["road_address"], n["road_address"], same=detail_same, warn=True,
            note="" if detail_same else "도로명+번지는 같고 건물명·층 표기만 다름 — 통일 권장")
    else:
        cmp("도로명 주소", k["road_address"], n["road_address"], same=False, note="도로명·번지 자체가 다름 — 즉시 확인")
    nd = {x["day"]: (x["hours"] or x.get("note") or "") for x in n["business_hours"].get("days", [])}
    for day in DAYS:
        kv = k["business_hours"]["days"].get(day) or ("휴무" if day in k["business_hours"]["days_off"] else None)
        nv = nd.get(day)
        kn, nn = norm(kv).replace("~", "-"), norm(nv).replace("~", "-")
        same = (kn == nn) or ("휴무" in kn and "휴무" in nn)
        cmp(f"영업시간 {day}", kv, nv, same=same)
    k_off, n_free = k["business_hours"]["days_off"], (n["business_hours"].get("free_text") or "")
    conflict = "공휴일" in k_off and "공휴일" in n_free and "휴무" not in n_free
    cmp("공휴일 정책", k_off, n_free or "(자유문구 없음)", same=not conflict,
        note="카카오 '공휴일 휴무' vs 네이버 '공휴일 영업은 인스타로 확인' 같은 충돌 감지")
    nprices = {norm(m["name"]): m["price"] for m in n["menus"]}
    for m in k["menus"]:
        key = next((kk for kk in nprices if norm(m["name"]) in kk or kk in norm(m["name"])), None)
        nv = nprices.get(key) if key else None
        cmp(f"가격 {m['name']}", m["price"], nv, same=(str(m["price"]) == str(nv)))
    only_naver = [m["name"] for m in n["menus"] if not any(norm(m["name"]) in norm(km["name"]) or norm(km["name"]) in norm(m["name"]) for km in k["menus"])]
    if only_naver:
        out.append(("네이버에만 있는 상품", "—", ", ".join(only_naver), "⚠️", "카카오 가격표에도 추가"))
    cmp("리뷰 수", f"카카오맵 {k['reviews']['kakaomap_count']}", f"네이버 방문자 {n['reviews']['visitor_total']}",
        same=k["reviews"]["kakaomap_count"] >= max(1, (n["reviews"]["visitor_total"] or 0) // 10), note="카카오가 네이버의 1/10 미만이면 채널 방치")
    return out


def main():
    argv = sys.argv[1:]
    if not argv:
        sys.exit(__doc__)
    name = argv[argv.index("--name") + 1] if "--name" in argv else None
    naver = argv[argv.index("--naver") + 1] if "--naver" in argv else None
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] not in ("--name", "--naver"))]

    if name:
        hits = search(name)
        if not hits:
            sys.exit(f"카카오맵 검색 결과 없음: {name}")
        if len(hits) > 1:
            print(f"검색 결과 {len(hits)}건 — 첫 번째로 진단합니다. 다른 업체면 ID로 다시 실행:")
            for h in hits[:5]:
                print(f"  {h['id']}  {h['name']}  {h['address']}")
            print()
        place_id = hits[0]["id"]
    else:
        place_id = resolve_id(pos[0])

    d = audit(place_id)
    if "--json" in argv:
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return

    print(f"# {d['name']}  ({d['url']})")
    print(f"카테고리: {d['category_path']} · 주소: {d['road_address']} · 찾아오는길: {d['directions']} · 전화: {', '.join(d['phone']) or '없음'}")
    print(f"정보 갱신: {d['info_updated_at']} · 태그: {', '.join(d['tags']) or '없음'} · 주차: {d['parking']}")
    print()
    print("| 항목 | 상태 | 근거 |")
    print("|---|---|---|")
    for lane, st, why in score(d):
        print(f"| {lane} | {st} | {why} |")
    print()
    h = d["business_hours"]
    print("영업시간:", " · ".join(f"{day} {h['days'].get(day) or ('휴무' if day in h['days_off'] else '미입력')}" for day in DAYS), f"| 휴무: {h['days_off'] or '없음'}")
    print("상품:", "; ".join(f"{m['name']}={m['price'] or '문의'}" for m in d["menus"]) or "없음")
    print("링크:", ", ".join(d["links"]) or "없음")

    if naver:
        n = load_naver(naver)
        print()
        print(f"## 네이버 대조 — {n['name']} ({n['url']})")
        print()
        print("| 필드 | 카카오맵 | 네이버 | 일치 | 비고 |")
        print("|---|---|---|---|---|")
        mism = 0
        for field, kv, nv, st, note in compare(d, n):
            mism += st != "✅"
            print(f"| {field} | {kv} | {nv} | {st} | {note} |")
        print()
        print(f"불일치 {mism}건 — NAP 일관성은 글자 단위로 맞춰야 한 엔티티로 인식된다. 정본을 하나 정하고(보통 네이버) 나머지를 그에 맞춰라.")


if __name__ == "__main__":
    main()
