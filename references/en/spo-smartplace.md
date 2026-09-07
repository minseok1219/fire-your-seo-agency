# SPO — Smart Place Optimization (Naver Map · Place search · AI Briefing local answers)

If you run a physical business (gym, restaurant, clinic, academy, salon…), the answer to
"crossfit near Geoyeo station" is **not your homepage — it's your Place card**. NEO asks
"does Naver cite my domain?"; SPO audits and fills a **Naver-hosted profile you don't
control**, through the crawler's eyes. Three goals: ① Place search ranking ② showing up as
the card in AI Briefing / Map local answers ③ converting from the card to call / booking / chat.

> Naver's ranking logic is private. This lane never promises "fix this and rank higher".
> Instead it fills **every signal measurable from real fields on the public page**, then
> re-measures with Smart Place Center statistics.

## 0. Crawler-eye audit — run the script first

The public Place page (`m.place.naver.com/place/{id}/home`) server-renders business data into
`window.__APOLLO_STATE__`. Readable with no login and no API key:

```bash
# accepts naver.me short links, map URLs, or a bare numeric ID
python3 scripts/place-audit.py https://naver.me/xxxxxxx
python3 scripts/place-audit.py 1790538774 --json   # every raw field
```

What the script reads (fields confirmed SSR-exposed as of 2026-09):

| Field | Apollo key | What it tells you |
|---|---|---|
| `placeDetail.newBusinessHours` | ROOT_QUERY | **the real business hours** — per-day times · regular closures · temporary closures · open/closed status |
| `missingInfo.is*Missing` | PlaceDetailBase | Naver's missing-info flags. ⚠️ `isBizHourMissing` keys off the legacy field and reads true even when hours exist (observed false positive) — informational only |
| `openingHours` | PlaceDetailBase | legacy hours field, usually null — never judge on it |
| `roadAddress` / `road` | PlaceDetailBase | address · directions |
| `virtualPhone` / `phone` / `talktalkUrl` | PlaceDetailBase | conversion paths (SmartCall · TalkTalk) |
| `conveniences` / `paymentInfo` | PlaceDetailBase | amenities · payment methods |
| `categoryCodeList` | PlaceDetailBase | number of category mappings |
| `Menu:*` | products / price list | the answer to "how much?" |
| `VisitorReviewStatsResult` | review stats | count · rating · photo reviews · themes |
| `Feed:*` (feed tab) | news posts | cadence · categories · blog sync |
| `PlaceDetailTopPhotoItem` | home hero area | are visitor photos crowding out yours? |
| `placeDetail.tabs` | tab list | `ticket`/`booking` tab = booking enabled |

**Not in SSR** (loaded client-side via GraphQL — the script marks these 🔎): the description,
the 5 representative keywords, homepage/SNS links, total photo count. Verify those in Smart
Place Center (smartplace.naver.com) yourself or ask the user for a screenshot.

⚠️ Naver's markup changes without notice. If a whole field comes back empty, it may be a
parse failure rather than a real gap — cross-check in a browser once, and fix the script.

## 1. Basic info completeness — judge on the real fields

- [ ] **Hours for 7/7 days**: per-weekday times + breaks + regular closures, all filled. An empty
      weekday is "not entered", not "closed" — mark rest days as regular closures explicitly.
      Empty hours drop you from "open now" filters and AI answers say "hours not available".
      Class-based businesses (gyms): door-open hours here, the class timetable in the
      description or a product image
- [ ] **Register temporary closures in hours too** (`comingIrregularClosedDays`): a holiday or
      competition closure posted only as news leaves the card's "open now" badge wrong
- [ ] **`missingInfo` flags are informational only**: if `isMenuImageMissing`,
      `isDescriptionMissing` or `isConveniencesMissing` is true, cross-check in Center. But
      `isBizHourMissing` was observed true on a business with hours fully registered —
      **never mark ❌ on the flag alone**. The script does not use it for scoring
- [ ] **Category**: does the primary category match the real business? (Registering a CrossFit
      box as "gym" is correct when Naver has no CrossFit category — use the parent + description
      and keywords to compensate)
- [ ] **Directions**: "Exit N of ○○ station, N min walk". Underground or in-building: floor and unit
- [ ] **Amenities · payment**: tick every applicable item. Parking, restrooms, wifi, group use are
      filter conditions
- [ ] **Phone**: confirm SmartCall (0507) is connected — only SmartCall calls show in Center stats

## 2. Description · representative keywords (🔎 manual items)

- [ ] **First sentence is a direct answer**: "[area + type + differentiator]" in the first 40
      characters, e.g. "2 min from Geoyeo stn exit 4, a CrossFit box with a free first-timer
      trial". Same principle as AEO's direct-answer paragraph — AI Briefing often quotes the
      description's first sentence verbatim
- [ ] **5 representative keywords**: real "area + type" search phrases (e.g. Geoyeo-dong crossfit,
      Geoyeo station gym, Songpa crossfit, Macheon crossfit, crossfit free trial). The brand
      name ranks anyway — don't waste a slot on it
- [ ] ❌ **No keyword stuffing in the business name**: "CrossFit Able Geoyeo Songpa Gym PT Diet"
      violates Naver's naming policy and gets exposure restricted. Business name = the sign
      on the door

## 3. Products · prices

- [ ] Put **numeric prices** on core products. A price list that only says "inquire" can't
      answer "how much is ○○" and loses comparison searches to competitors with prices
- [ ] Entry products (free trial, consultation) **on the first line** (`index: 0`) — the first
      product visible on the card
- [ ] Product images: clear `isMenuImageMissing`. Timetables and facility photos count
- [ ] When prices change, post it in news too — a card price that disagrees with a news post
      costs trust

## 4. Reviews — clean methods only

- [ ] **Reply to 100% of visitor reviews**: replies are a trust signal and a keyword surface.
      Mention area / type / product names naturally, but copy-pasted replies are a spam
      pattern — reference what the reviewer said
- [ ] **Ask for receipt / booking reviews in person**: a "please leave a Naver review" sign or
      QR at checkout is allowed. Discounts or gifts in exchange for reviews violate Naver
      policy (review abuse)
- [ ] **Read the review themes**: the script's `themes` (service · location · facilities…) are
      the strengths customers actually name. Align description, news and blog topics to them
- [ ] **Zero reviews in the last 30 days is a risk**: recency matters more than total count for
      the "living business" judgment (observed)
- [ ] Blog reviews: if sponsored blog reviews outnumber visitor reviews, you look like an
      "advertised business". Keep the ratio from flipping

## 5. News (feed) — the freshness signal

- [ ] **At least twice a month**, 6+ posts in the trailing 90 days. Script field:
      `owner_posts_last_90d`
- [ ] **Mix categories**: notice · SALE · temporary closure · event. A feed of only "SALE"
      reads as an ad stream
- [ ] **Always post temporary closures**: closing without notice piles up "wrong hours" reports
- [ ] **Blog sync**: connecting a Naver blog auto-collects blog posts into the feed
      (`Feed:{blogId}_*`). Use the same blog as NEO's inside track — no double maintenance
- [ ] Write news bodies as [question → direct answer]: "Can total beginners join? → Yes. On
      your first visit we check fitness and adjust load and difficulty." — that's the paragraph
      shape AI Briefing lifts

## 6. Conversion paths — open all three

- [ ] **Booking**: is `ticket`/`booking` in `tabs`? Make the free trial / consultation a booking
      product — you get the "bookable" badge and AI answers steer to "book on Naver"
- [ ] **TalkTalk**: `talktalkUrl` present + manage response rate (Center stats). First line of
      the auto-reply: hours and location
- [ ] **Phone (SmartCall)**: `virtualPhone` present. Missed-call message steers to TalkTalk
- [ ] Conversion stats exist only in Center > Statistics > "call · directions · booking · TalkTalk
      clicks". Snapshot weekly

## 7. Photos · video

- [ ] **Is the home hero area yours?** Script field `business_photos_in_top`. If visitor photos
      fill the ~10 hero slots you don't control the first impression — re-upload business photos
      with a recent date and they move up
- [ ] Storefront · interior · facilities · class in progress · timetable · coach profiles, at least
      10, mixed landscape and portrait
- [ ] **Clips (short video)**: clips linked to the Place show as video in the hero area. Hashtags
      must include `#businessname #area+type` to match the Place (observed: matched via hashtags)
- [ ] Replace hero photos older than ~2 years — an "aging business" signal

## 8. Entity consistency — Place ↔ your domain ↔ SNS

The LLMO principle applied to a physical business. **Name · address · phone (NAP) identical
to the character on every surface**:

- [ ] Place business name = homepage `<title>` = Instagram profile name = blog name = the sign
      ("CrossFit Able Geoyeo" vs "Able Geoyeo" vs "ABLE GEOYEO" mixed = entity split)
- [ ] If you own a domain, add `LocalBusiness` JSON-LD (or a subtype: `SportsActivityLocation`,
      `Restaurant`…) and list the Place URL (`https://m.place.naver.com/place/{id}`), Instagram
      and blog in `sameAs` — the declaration that "these names are all one entity"
- [ ] Expose your own domain in the Place description / news, even as plain text (links NEO's
      outside track)
- [ ] `og:title` is generated as `{business name} : Naver`, so the business name IS the search
      snippet — including the area in the name (e.g. "○○ Geoyeo") helps local matching and is
      not a policy violation

## 9. Don'ts (Place reports and sanctions are fast)

- ❌ Buying reviews, incentivized reviews, mobilizing friends for visitor reviews — abuse
      verdicts delete reviews and restrict exposure
- ❌ Keyword stuffing in the business name, false categories (a gym as a "clinic")
- ❌ Registering the same location as multiple Places — reviews split and one gets marked closed
- ❌ Frequent changes to hours and prices — a noisy edit history lowers information trust
- ❌ Reposting identical news text — the same spam filter as Naver Blog runs here

## 10. Measurement

Place has no API like Search Advisor. Measure on two layers:

1. **Public signals (script, automatic)**: days with hours entered · priced products · visitor
   review count · 90-day news count. Save `--json` output per date and diff
2. **Center statistics (manual, weekly)**: Place views, top inbound search terms, call ·
   directions · booking · TalkTalk clicks. **The top inbound terms are your keyword candidate
   list** — a top term not among your 5 keywords = the next keyword to add
3. **Ranking snapshot**: search the 5 keywords in the Naver app (mobile) and record Place rank
   and whether the AI Briefing local answer shows you, as O/X. Results are location-based —
   re-measure **from the same place at the same time of day** or the comparison is meaningless

```
[baseline]  9/7: hours 7/7 · prices 3/6 · visitor reviews 127 · 90-day news 5 · "Geoyeo crossfit" rank 2
[change]    9/8: 5 keywords + numeric prices + free-trial booking product on line 1 + 8 business photos refreshed
[re-measure booked] 9/22
[re-measure result] prices 6/6 · reviews 134 · news 8 · rank 1 · booking clicks 12 → 31   ← this is what "done" looks like
```
