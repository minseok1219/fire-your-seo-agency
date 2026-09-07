# KMO — Kakao Map Optimization (Kakao Map · KakaoTalk search · Talk Channel conversion)

Kakao Map is Korea's second map channel, and most businesses **register once and abandon it**.
So the substance of KMO is not building something new — it is **matching Naver Smart Place
character for character**. A customer who arrives via Kakao and sees different hours, prices or
closures than on Naver trusts neither. Three goals: ① NAP parity with Naver (name · address ·
phone · hours · prices) ② filling the empty Kakao Map reviews and news ③ converting through
Talk Channel and Kakao Booking.

> Kakao's ranking logic is private. This lane never promises "fix this and rank higher".
> Instead it fills **every signal measurable from real fields in the public API** and drives
> the Naver mismatch count to zero.

## 0. Crawler-eye audit — run the script first

The search endpoint and place panel API used by Kakao Map's own web client return JSON with no
login and no key:

```bash
python3 scripts/kakao-audit.py --name "business name"                   # search → audit first hit
python3 scripts/kakao-audit.py https://place.map.kakao.com/641759795   # URL or numeric ID
python3 scripts/kakao-audit.py 641759795 --naver https://naver.me/xxxx # field-by-field Naver comparison ★
python3 scripts/kakao-audit.py 641759795 --json                        # every raw field
```

What the script reads (observed 2026-09, `place-api.map.kakao.com/places/panel3/{id}`):

| Field | What it tells you |
|---|---|
| `summary.name` / `address` / `phone_numbers` / `homepages` | NAP + external links (homepage · Instagram · blog in one array) |
| `summary.meta.updated_at` | last business-info update |
| `open_hours.all.periods` / `all_days_off_info` | per-day hours · regular closures · **holiday policy** |
| `menu.menus.items` / `items_updated_at` | products & prices + **price list update date** (⚠️ if > 1 year) |
| `kakaomap_review.score_set` | Kakao Map's own review count & rating (a separate channel from Naver) |
| `blog_review.review_count` | blog review count |
| `my_store_notice` | store-management registration · news count |
| `talk_channel` / `reservation` / `available_tickets` | Talk Channel (friend count) · Kakao Booking · booking products |
| `photos.counts` | owner photos / total / indoor · outdoor |
| `place_add_info.tags` / `facilities` | tags · parking |
| `find_way.subway` | directions (station · exit · distance) |

⚠️ Unofficial endpoint. Without the `pf: web`, `Origin` and `Referer` headers it returns 406.
If it breaks, open place.map.kakao.com in browser devtools and copy the real request headers.

## 1. Compare with Naver — the core of KMO

Run `--naver` and drive **mismatches to zero**. Pick one source of truth (usually Naver, the
side with more reviews). Mismatch types observed in practice:

- [ ] **Spacing in the business name**: "크로스핏에이블 거여" (Kakao) vs "크로스핏 에이블 거여"
      (Naver). Search engines and models treat these as different entities. Unify to the sign
- [ ] **Minute-level hour differences**: 06:30 vs 06:15. Find out which is true and fix the
      other — one side is a stale value
- [ ] **Holiday policy conflict**: Kakao "closed on public holidays" vs Naver "check Instagram
      for holiday hours". Customers from Kakao assume you're closed. Put the real policy on both
      in the same sentence
- [ ] **Missing price-list items**: entry products on Naver (free trial · consultation · group
      discount) absent on Kakao. Kakao's `items_updated_at` is often frozen for over a year
- [ ] **Address detail**: same street and number but different building/floor wording → ⚠️.
      Unify
- [ ] **Category**: Kakao "sports facility" vs Naver "gym" — the taxonomies differ, so exact
      parity is impossible. Pick the narrowest accurate category on each (not a mismatch)

## 2. Store-management registration (prerequisite)

- [ ] Is `my_store_notice.status == REGISTERED`? If not, editing info, news, booking and Talk
      Channel linking are all impossible — start with business verification in Kakao Map store
      management. Needs the user's account; walk them through it
- [ ] If registered, check `summary.meta.updated_at` — untouched for 6+ months means abandoned

## 3. Reviews — Kakao Map reviews are a separate channel

Most businesses have 100 Naver visitor reviews and 0 Kakao Map reviews. Someone searching in
the Kakao Map app never sees the Naver reviews.

- [ ] **Add Kakao Map to the review QR**: a Kakao Map review QR next to the Naver one. A
      post-payment request is fine; discounts or gifts for reviews are abuse
- [ ] **Reply to reviews**: Kakao Map supports owner replies. Same rules as Naver — no
      copy-paste, reference the review
- [ ] `kakaomap_review.strength_description` (price · expertise · kindness…) is the set of
      strengths Kakao asks about for this category. Make description and news answer them
- [ ] Blog reviews (`blog_review`) are Naver blog posts Kakao collected — NEO's blog track
      works here too

## 4. News — replicate Naver news

- [ ] `my_store_notice.notice_count == 0` is ❌. Post every Naver Smart Place news item **to
      Kakao store management the same day**. Not new writing — replication. Temporary closures,
      events and price changes especially go to both (one side only shows up as a mismatch in
      section 1)
- [ ] News body in [question → direct answer] form (same as SPO section 5)

## 5. Conversion paths — Talk Channel is the point

Kakao's differentiator is **conversion that never leaves KakaoTalk**: map → Talk Channel →
chat → booking without switching apps.

- [ ] **Talk Channel linked** (`talk_channel`): friend count is your re-visit push audience.
      Grow it with a real benefit at first visit ("add the channel for timetable and closure
      alerts"), not a discount-for-follow
- [ ] **Kakao Booking** (`reservation` + `available_tickets`): free trial and consultation as
      booking products. Same product set as Naver Booking (a product on one side only = mismatch)
- [ ] **Phone**: Kakao lists the landline (02-…), Naver lists SmartCall (0507-…). Different
      numbers are normal — just confirm both ring the same place
- [ ] Talk Channel auto-reply first line: hours · location · free trial

## 6. Photos · tags

- [ ] Fewer than 10 owner photos (`photos.counts.mystore`) → add more. Kakao counts indoor and
      outdoor separately — **0 outdoor (storefront) photos** means map users can't find the
      building
- [ ] `place_add_info.tags`: auto-assigned by Kakao (diet · crossfit · culture-expense deduction…).
      Limited direct editing, but words used in the description and product names feed the tags
- [ ] Culture-expense-deduction merchants show automatically under `events` — worth registering
      for sports facilities

## 7. Entity consistency — link to your own domain

- [ ] Does `summary.homepages` hold homepage, Instagram and Naver blog? Kakao puts all three in
      one array, so the `sameAs` evidence is easier to build than on Naver
- [ ] Add the Kakao Map URL (`https://place.map.kakao.com/{id}`) to your domain's
      `LocalBusiness` JSON-LD `sameAs` — the declaration that Naver, Kakao, Instagram and the
      blog are one entity
- [ ] Talk Channel name (`talk_channel.name`) identical to the business name too —
      "크로스핏에이블거여" with yet another spacing makes three spellings

## 8. Don'ts

- ❌ Buying Kakao Map reviews or mobilizing friends — same abuse standard as Naver, and the
      Talk Channel can be sanctioned too
- ❌ Duplicate registrations — Kakao processes duplicate reports quickly and one gets hidden
- ❌ Different prices/hours as a "Kakao-only promotion" — customers compare, trust only drops
- ❌ Mass Talk Channel broadcasts — rising block rates reduce the channel's own exposure

## 9. Measurement

Store-management statistics (views · calls · directions · Talk Channel clicks) exist only in
the center. Measure on two layers:

1. **Public signals (script, automatic)**: mismatch count from `--naver`, Kakao Map review
   count, news count, price-list update date, Talk Channel friends. Save `--json` per date and
   diff
2. **Center statistics (manual, weekly)**: store management > statistics. Merge inbound search
   terms with Naver Search Advisor / Smart Place Center as keyword candidates

```
[baseline]  9/7: Naver mismatches 9 · Kakao Map reviews 0 · news 0 · price list updated 2024-09 · Talk Channel friends 21
[change]    9/8: name · hours · holiday wording matched to Naver + free trial & group discount products added + 3 news items replicated + Kakao Map added to review QR
[re-measure booked] 9/22
[re-measure result] mismatches 0 · reviews 4 · news 5 · Talk Channel friends 33   ← this is what "done" looks like
```
