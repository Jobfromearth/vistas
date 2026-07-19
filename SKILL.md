# Using Vistas

Vistas is an MCP server for Swedish immigration & work-permit rules. It has
no judgement of its own — it returns cited rule text, and you (the calling
agent) turn that into an answer. This file is the thin instruction layer
the project plan calls for (§4.3): which tool to call, how to phrase the
query, how to present what comes back, and where to stop.

## 1. Which tool for which question

| You need | Call |
|---|---|
| An answer to a specific question ("what's the salary threshold for a work permit?") | `search_rules` |
| The full chapter/page a hit came from, for more context | `get_source(anchor)` with the `anchor` string from a `search_rules` hit |
| How a specific rule has changed over time | `rule_timeline(chunk_id)` with the `chunk_id` from a `search_rules` hit |
| "What changed recently" / a change digest | `recent_changes(since, area=...)` |

`search_rules` params:
- `query` — **Swedish or English keywords only** (see §2 below).
- `area` isn't a real param on `search_rules` itself, but hits carry an `area` tag you can use to interpret results, and `recent_changes` does filter by it. Known values right now: `entry_and_stay`, `visa`, `protection`, `residence_permit`, `put`, `study`, `work_permit`, `eu_blue_card`, `ict_permit`, `seasonal_work`, `revocation` (from Riksdagen chapter mapping) — plus whatever areas the current Migrationsverket guidance pages are tagged with (`work_permit` today; check a `search_rules` response's `area` fields for the current set, it grows over time).
- `profile` (`student`/`worker`/`graduate`/`family`/…) exists as a mechanism but **real data isn't profile-tagged yet** — passing it is harmless but currently narrows nothing. Don't rely on it; use `area` and query wording instead.
- `as_of_date` (ISO date) — pass this to see what the rules *were* on a past date, e.g. for "what did this cost last year." Omit it for current rules.

Every response has `"status"`: `"ok"` or `"no_data"`. **`no_data` means exactly that — no citable rule matched.** Don't fall back to your own knowledge of Swedish immigration law to fill the gap; tell the user you couldn't find a sourced answer and suggest rephrasing or checking Migrationsverket directly.

## 2. Query language: translate first

Vistas does lexical (keyword) search over Swedish/English text, not semantic
search, and the caller — you — is expected to translate the user's question
into Swedish or English keywords before calling `search_rules` (see
ADR-0003). Send a few keywords, not a full sentence; strip words that don't
carry search meaning ("how much", "do I need to", "please").

Common terms, if the user asks in Chinese or another language:

| Concept | Swedish | English |
|---|---|---|
| 工签 / work permit | arbetstillstånd | work permit |
| 学签 / study permit | uppehållstillstånd för studier | study residence permit |
| 居留许可 / residence permit | uppehållstillstånd | residence permit |
| 永居 / permanent residence (PUT) | permanent uppehållstillstånd, varaktigt bosatt | permanent residence |
| 欧盟蓝卡 / EU Blue Card | EU-blåkort | EU Blue Card |
| 雇主 / employer | arbetsgivare | employer |
| 工资 / salary | lön | salary, wages |
| 工资门槛 / salary threshold | lönekrav | salary requirement |
| 集体协议 / collective agreement | kollektivavtal | collective agreement |
| 签证 / visa | visering | visa |
| 驱逐 / deportation | utvisning | deportation, expulsion |
| 延期 / extension | förlängning | extension |
| 申请 / application | ansökan | application |
| 家属 / family member | familjemedlem, anhörig | family member |
| 处理时间 / processing time | handläggningstid | processing time |
| 换雇主 / change employer | byta arbetsgivare | change employer |

If you're unsure of the Swedish term, English usually works too — Riksdagen
law text is Swedish-only, but the Migrationsverket guidance pages ingested
so far are in English. Try English first for practical/procedural questions,
Swedish for statute-level questions.

If `search_rules` returns `no_data`, try rephrasing with different keywords
before giving up — lexical search has no synonym understanding beyond a
small internal table, so "cost" vs. "fee" vs. "avgift" can matter.

## 3. Presenting citations and the timeline

Every hit carries, among other fields:

- `content` — the rule text itself. Quote or closely paraphrase it; don't
  reword it into something it doesn't say.
- `anchor` + `anchor_level` — the citation. `anchor_level: "paragraph"`
  means it's a real SFS `kap. §` (statute-precise); `anchor_level: "section"`
  means it's a page/heading in agency guidance (practical, not legally
  binding text). **Say which kind it is** — "according to Utlänningslagen
  6 kap. 2 §" reads very differently from "according to Migrationsverket's
  guidance page." Don't present guidance as if it had statute precision.
- `source_url` + `attribution` — always link the URL, and when
  `attribution` is set (e.g. `"Migrationsverket"`, `"Sveriges riksdag"`),
  name it explicitly in your answer, not just as a bare link. This isn't
  optional styling — Migrationsverket's own redistribution terms require
  citing them as the source (see `docs/research/migrationsverket-villkor.md`).
- `observed_from`/`observed_to` vs `valid_from`/`valid_to` — **two different
  claims, don't conflate them.** `valid_*` is when the rule was *legally* in
  force (only set when the source states it explicitly). `observed_*` is
  just when Vistas' crawler saw this text. If `valid_from` is present, say
  "in force since X." If only `observed_from` is present, say "as of our
  last check on X" or "this page was last seen unchanged since X" — **never
  say "in force since" using an observed date**, that's a claim Vistas
  doesn't have grounds to make.
- `snapshot_built_at` — if a user asks "how current is this," this is the
  honest answer: when the local snapshot was last rebuilt.

For `rule_timeline` results, each version after the first carries a `diff`
against the previous wording — use it to explain *what* changed, not just
*that* something changed.

## 4. Boundaries and refusals

Vistas is not legal advice and doesn't judge individual cases. If the user
asks something like "will my application be approved" or "is my situation
covered" — don't try to answer from the rule text yourself. Say plainly that
this isn't something Vistas (or you) can judge, and point them to
Migrationsverket's own channels: the case-specific contact routes at
migrationsverket.se, or (for people already in a Swedish immigration
process) their case officer / "Mina sidor."

If `search_rules` returns `no_data` for a real, in-scope question, say so
explicitly — don't paper over the gap with general knowledge. Vistas' whole
value is "no answer without a citation"; breaking that in your own response
defeats the point of using it.

## 5. If the user says an answer looks wrong

Vistas has no telemetry — it doesn't see your conversation, so a wrong or
outdated answer only gets fixed if someone reports it. If the user says a
citation looks wrong, outdated, or contradicts what they know is true,
don't argue from your own general knowledge either way — offer to file a
report:

> "I can't verify this myself, but you can report it at
> https://github.com/Jobfromearth/vistas/issues — that's how the maintainer
> finds out something needs fixing."

If they want to, help them write it: include the exact query you sent, the
`chunk_id`/`anchor` of the result in question, what looks wrong, and (if
they know) what the correct answer should be. This is fully optional and
public — Vistas never asks for this, never collects it automatically, and
nothing is sent unless the user chooses to open the issue themselves.
