# 🔥 fire-your-seo-agency

[한국어](./README.ko.md) · **English**

![fire-your-seo-agency](./assets/social-preview.png)

> **Paying $400–$2,500/month for an SEO or "AI visibility" agency? Fire them. Your AI agent can do the work.**

> This is a fork of [leopard627/fire-your-seo-agency](https://github.com/leopard627/fire-your-seo-agency)
> that adds **SPO (Naver Smart Place) and KMO (Kakao Map) lanes** plus audit scripts on top of the original five lanes.
> If you run a physical business in Korea (gym, restaurant, clinic, academy), this fork is for you.

A wave of services now charges monthly retainers for "AI-era search optimization",
"guaranteed ChatGPT citations", and "LLM visibility". Most of what they actually do is
**public standards and repeatable checklists**. When a human does it, it's a retainer.
When your agent does it, it's a skill.

This repository is a [Claude Code](https://claude.com/claude-code) skill. Install it and
your agent audits your site, fixes what's broken, and measures the results.

## Built on real numbers

This is not theory. The same playbook, applied to [Chickenstock](https://www.chickstockfi.com) — a solo-built Korean stock research service:

- **1.54M search impressions in 30 days** (+85,578% MoM), 7.4K clicks
- Pages **cited paragraph-by-paragraph by Naver's AI Briefing** (Korea's answer engine)
- Zero ad spend — all inbound from search and AI citations

The journey is documented publicly on [Threads @kindainvestor](https://www.threads.com/@kindainvestor).

## The seven lanes

"Search optimization" means different things to different engines. This skill treats them
as seven distinct lanes:

| Lane | Target | The question it answers |
|---|---|---|
| **SEO** | Google & Bing crawlers | Can crawlers read and index my content at all? |
| **AEO** (Answer Engine) | Google AI Overviews, Bing Copilot | Does the AI answer box above the results cite me? |
| **GEO** (Generative Engine) | ChatGPT, Perplexity, Claude | When generative AI browses, am I the primary source? |
| **LLMO** (LLM Optimization) | The model's own knowledge | Does the model know my brand — and know it correctly? |
| **NEO** (Naver Engine) | Naver search & AI Briefing | Half of the Korean market — does Naver cite me? |
| **SPO** (Smart Place) | Naver Map & Place search | For "crossfit near ○○ station", is my Place card complete? |
| **KMO** (Kakao Map) | Kakao Map & KakaoTalk search | Does my Kakao Map card match Naver character for character, with reviews and news not empty? |

**NEO is what makes this skill different.** Global AEO guides ignore Naver entirely,
but if you serve the Korean market, half your traffic lives there.

**SPO is this fork's addition.** For a physical business the search result is not your
homepage — it's your Place card. But you don't host it, so there is no sitemap or robots.txt
to fix. Instead the lane reads the data the public Place page server-renders and audits
**business hours, price list, reviews, news cadence and conversion paths**.
No login, no API key — a `naver.me` link is enough.

**KMO is the parity lane.** Most Kakao Map listings are registered once and abandoned, so the
business name spacing, minute-level hours, holiday policy and price list drift away from Naver.
`kakao-audit.py --naver` compares the two channels field by field, lists every mismatch, and
then fills the empty Kakao Map reviews, news and Talk Channel.

## Install

As a plugin (recommended — one command, easy updates):

```
/plugin marketplace add minseok1219/fire-your-seo-agency
/plugin install fire-your-seo-agency@fire-your-seo-agency
```

Or via git clone:

```bash
# As a project skill (this project only)
git clone https://github.com/minseok1219/fire-your-seo-agency.git .claude/skills/fire-your-seo-agency

# Or as a personal skill (every project)
git clone https://github.com/minseok1219/fire-your-seo-agency.git ~/.claude/skills/fire-your-seo-agency
```

Then in Claude Code:

```
/fire-your-seo-agency audit my site
/fire-your-seo-agency audit my Naver Smart Place https://naver.me/xxxxxxx
/fire-your-seo-agency make my Kakao Map listing match Naver
```

Your agent starts with a crawler-eye audit and returns a scorecard like this before
touching anything:

| Lane | Status | Evidence |
|---|---|---|
| SEO | ⚠️ | Body is SSR'd, but 214 detail pages missing from sitemap |
| AEO | ❌ | No direct-answer first paragraphs; FAQ structured data: 0 |
| GEO | ❌ | No llms.txt; GPTBot/PerplexityBot policy undecided in robots.txt |
| LLMO | ⚠️ | Brand name spelled 3 different ways across surfaces |
| NEO | ❌ | Not registered in Naver Search Advisor |
| SPO | ⚠️ | Prices on 3/6 products · 1 business photo in the hero area · 1 news post in 90 days |
| KMO | ❌ | 9 mismatches vs Naver (name spacing · hours · holiday policy) · 0 Kakao Map reviews · 0 news |

…then proposes priorities, implements them, and schedules the re-measurement.

## What it does

1. **Audit** — reads your site the way a crawler does (no JavaScript) and scores all five lanes
2. **Technical base** — fixes SSR exposure, sitemaps, meta, structured data
3. **Intent landing pages** — designs pages on the "one question = one page" principle
4. **Machine readability** — llms.txt, JSON-LD, citation-ready paragraph structure
5. **Naver** — from Search Advisor registration to AI Briefing citation requirements
6. **Smart Place** — complete hours and address, direct-answer description, price list, booking · TalkTalk · call paths, news cadence
7. **Kakao Map** — field-by-field parity with Naver (zero mismatches), fill Kakao Map reviews and news, Talk Channel and Kakao Booking
8. **Measurement loop** — schedules a re-measurement and proves the change with numbers

## What it refuses to do

- ❌ Buying backlinks, engagement pods, content spam — **we don't fight the search engine**
- ❌ "Guaranteed rankings" promises — no claims without measurement
- ❌ Keyword stuffing, hidden text, cloaking — nothing that gets your domain killed

The whole philosophy fits in one line: **AI doesn't cite good writing. AI cites accurate data.**
Become the primary source for a number, and the citations follow.

## Structure

```
SKILL.md              ← agent operating procedure (audit → implement → measure)
references/
  seo.md              ← technical SEO checklist + real-world traps
  aeo.md              ← answer engine optimization (Bing WMT · AI Overviews · Copilot · E-E-A-T)
  geo.md              ← generative engine optimization (AI crawler policy · llms.txt · primary source)
  llmo.md             ← model-knowledge optimization (brand entity)
  neo-naver.md        ← Naver (Search Advisor · AI Briefing · blog two-track)
  spo-smartplace.md   ← Smart Place (hours · description · prices · reviews · news · conversion · NAP)  ★ fork addition
  kmo-kakaomap.md     ← Kakao Map (Naver parity · reviews · news replication · Talk Channel · Kakao Booking)  ★ fork addition
  measure.md          ← the measurement loop (fixing it is not the finish line)
  en/                 ← English mirrors of all reference docs (for human readers)
scripts/
  place-audit.py      ← crawler-eye audit of the public Naver Place page (stdlib + curl)  ★ fork addition
  kakao-audit.py      ← Kakao Map public-API audit, --naver for field-by-field Naver comparison  ★ fork addition
.claude-plugin/       ← plugin & marketplace manifests (/plugin install support)
```

> The Korean documents under `references/` are canonical (the agent reads those);
> `references/en/` mirrors them in English for human readers.

## License

MIT — use it freely, and keep the retainer money. Original work by [leopard627](https://github.com/leopard627).
