# Migrationsverket.se villkor/upphovsrätt — compliance research for guidance-source redistribution

Research date: 2026-07-18. Conducted against primary sources (migrationsverket.se, riksdagen.se, lagen.nu) via direct page fetches, not blog posts or secondary summaries. All quotes below are verbatim Swedish text pulled from the cited URL at fetch time; translations are mine.

## Summary verdict

**The current ADR-0004 conservative default (abstract + structured facts + anchor link only, full text held internally, pending per-site villkor verification) can be relaxed for migrationsverket.se specifically — but only for the "text" category, and the site's own copyright notice, not a full go-ahead for everything Migrationsverket publishes.** Migrationsverket's "Om webbplatsen" page states plainly: *"All text på vår webbplats är fri att använda och sprida vidare förutsatt att du anger Migrationsverket som källa"* ("All text on our website is free to use and further distribute, provided you cite Migrationsverket as the source") — no attribution-only vs. bulk-copy distinction, no explicit carve-out against packaging into a third-party project, just a blanket permission conditioned on attribution. That covers HTML guidance pages (visa guides, processing-time pages) as prose. It does **not** cover photographs/illustrations (separate permission required) and it is silent on the specific case of "rättsliga ställningstaganden" PDFs, which sit on a different platform (Lifos) whose own terms I could not locate — treat those as unverified and keep them behind the conservative default until a Lifos-specific villkor page is found or Migrationsverket is asked directly. Sweden's öppna data-lagen (2022:818) is a weak support at best: Migrationsverket's own "Öppna data" page states their statutory open-data program covers **statistics only**, not general web prose, so the law itself is not the basis for redistributing guidance text — the site's own copyright notice is. **Recommendation: proceed to full-text redistribution for ordinary migrationsverket.se HTML guidance pages under CC-BY (attribution to Migrationsverket is a hard requirement per their own terms — CC0 would technically violate their stated condition), keep rättsliga ställningstaganden PDFs and any Lifos-hosted content under the conservative abstract+link default until verified separately.**

---

## 1. Does migrationsverket.se have a public terms-of-use / villkor / upphovsrätt page?

**Yes.** Primary page: **"Om webbplatsen"**
- Swedish: https://www.migrationsverket.se/om-migrationsverket/om-webbplatsen.html
- English: https://www.migrationsverket.se/English/About-the-Migration-Agency/About-the-website.html

Fetched directly (two independent fetches, consistent results). Full structure of the Swedish page, section by section:

- **Teknisk information** (technical info: supported browsers, JavaScript requirement, PDF viewer)
- **Tillgänglighet** (accessibility: text-to-speech, resizing, keyboard nav, languages)
- **Säkerhet** (security: data protection, public-computer caution)
- **Juridisk information** (legal information), containing:
  - **Upphovsrätt:** *"All text på vår webbplats är fri att använda och sprida vidare förutsatt att du anger Migrationsverket som källa."* Followed by a statement that photographs require Migrationsverket's permission (press-image page excepted).
  - **Länka till oss:** links to the site are welcome; don't use Migrationsverket's logo to link, and don't frame the site inside another site's frameset.
  - **E-tjänster:** users of e-services must provide truthful information; false information can carry criminal liability.

There is no separate dedicated "villkor.html" or "upphovsrätt.html" page — the copyright statement lives as one subsection of this general "Om webbplatsen" page. I did not find a separate, more detailed IP/licensing policy document anywhere on migrationsverket.se.

## 2. Does the policy distinguish "citing/linking" from "bulk copying and redistributing"?

**No.** The text is unqualified: *"All text på vår webbplats är fri att använda och sprida vidare"* ("all text ... is free to use and distribute further") — "sprida vidare" (distribute further) is a term that naturally covers republishing/redistribution, not just quoting a sentence with a link back. There is no separate clause capping how much may be copied, no "for personal/non-commercial use only" qualifier, and no distinction drawn between a citation excerpt and a bulk copy of a whole page or set of pages. The only carve-outs in the same "Juridisk information" block are (a) photographs/illustrations need separate permission, and (b) don't use their logo or iframe/frame their site when linking — neither of which restricts bulk text reuse.

Caveat: this is a short, general-purpose consumer-facing notice, not a lawyer-drafted license text — it doesn't anticipate an MCP data-pipeline use case, so "no explicit restriction found" is the honest finding rather than "explicitly permitted for this exact use case."

## 3. Does it require attribution?

**Yes, explicitly and as the sole stated condition.** *"...förutsatt att du anger Migrationsverket som källa"* ("...provided you cite Migrationsverket as the source"). This is a hard requirement, not a suggestion. Practical implication for ADR-0004: **CC0 is not a safe license choice for Migrationsverket-sourced guidance text**, since CC0 disclaims any conditions including attribution, and could be read as inconsistent with Migrationsverket's stated term. **CC-BY (or an equivalent explicit-attribution license) is the correct choice** for any snapshot content sourced from migrationsverket.se, and the "署名要求入 schema" gate mentioned in section 2.2 of the project plan is not just a nice-to-have — it's the operative legal condition, so anchor/source metadata must be preserved end-to-end from ingestion through whatever the MCP tool returns.

## 4. Does it explicitly permit or forbid a third party packaging site content into an open-source project for redistribution?

**Neither explicitly.** The notice doesn't contemplate this specific scenario (a structured/versioned open-license dataset redistributed via GitHub Releases as part of an MCP server). It grants a broad, unconditional-except-attribution right to use and further distribute text, which on its plain wording *would* cover this use case, but Migrationsverket did not write the notice with this scenario in mind, so there's some residual interpretive risk (e.g., an aggressive reading of "sprida vidare" as "share it further to a person," not "algorithmically republish the whole site under a permissive open license forever"). I could not find any FAQ, policy statement, or press item from Migrationsverket addressing bulk/automated redistribution, scraping-for-redistribution, or third-party open datasets built from their site. Given the plain text is permissive and no restriction was found despite a real search effort, I assess the risk as low-to-moderate rather than zero, which is why the recommendation above still keeps rättsliga ställningstaganden (a more sensitive, quasi-legal document category on a separate platform) behind the conservative default.

## 5. Does öppna data-lagen (SFS 2022:818) apply to agency website prose, or only to published datasets/APIs?

**Answer: the law's abstract scope is broad enough to reach prose in principle, but Migrationsverket's own implementation of it in practice is statistics-only — so it is not a usable basis for claiming a right to redistribute guidance prose.**

Two separate findings:

**(a) The law's own text (2022:818), via lagen.nu consolidated text:**
- `1 kap. 4 §` defines "data" very broadly: *"information i digitalt format oberoende av medium"* ("information in digital format, independent of medium") — this wording does not exclude prose/guidance text; a webpage's text is "information in digital format."
- `1 kap. 8 §`: the law's obligations are triggered either when (i) someone with a legal right of access (i.e., under offentlighetsprincipen/tryckfrihetsförordningen) requests the data for reuse, or (ii) the authority voluntarily makes data available for reuse. It does not itself create a freestanding right to demand any given piece of content be opened up — it governs the *terms* under which already-accessible or voluntarily-published material must be released (no unreasonable restrictions, reasonable fees, machine-readable formats, etc.).
- `1 kap. 10 §` lists exclusions from the law's scope: data covered by patent/design rights (point 1), **data a third party (tredje man) holds copyright to under lagen (1960:729)** (point 2), computer programs (point 3), logos/heraldic symbols (point 4). Note the "tredje man" (third-party) framing in point 2 — this exclusion is about *other people's* copyright, not the authority's own authored content, so it does not by itself exclude Migrationsverket-authored guidance prose from the law's scope (Migrationsverket is not a third party to its own text).
- Source: https://lagen.nu/2022:818/konsolidering/2022:818 (consolidated text, fetched directly). I was not able to independently cross-check every paragraph number against riksdagen.se's own SFS reproduction in this session, so treat the specific `§` numbering as sourced from lagen.nu's consolidation rather than double-verified against a second primary copy; the substantive content (broad "data" definition, third-party-copyright exclusion, access-request/voluntary-publication trigger) is consistent with how DIGG's own guidance describes the law.

**(b) Migrationsverket's actual practice under the law**, per their own "Öppna data" page — https://www.migrationsverket.se/om-migrationsverket/statistik/oppna-data.html (fetched directly):
- *"Migrationsverkets öppna data består av statistik som publiceras här på vår webbplats."* ("Migrationsverket's open data consists of statistics published here on our website.") — i.e., their öppna data-lagen-driven program is scoped to statistics exports (asylum applications, decisions, permits granted, reception-system counts — Excel files, monthly/annual), not guidance prose.
- *"Migrationsverket förfogar över betydligt mer information än den som publiceras som öppna data, men all information kan inte tillgängliggöras"* — reasons given include *sekretess, skydd för personuppgifter, upphovsrätt eller annan lagstiftning* (confidentiality, personal-data protection, copyright, or other legislation).
- No CC0/CC-BY or other formal license is stated for the statistics either — the page's stated condition is essentially "no conditions, contains no personal data," which is informal, not a real license grant.

**Conclusion for the project:** don't cite öppna data-lagen as the legal basis for redistributing migrationsverket.se guidance prose — it isn't, in Migrationsverket's own practice. The actual basis is the "Om webbplatsen" copyright notice answered in Q1–Q4 above (a straightforward, ordinary copyright permission, attribution-conditioned), which is a cleaner and stronger basis anyway since it's unambiguous and specifically about text.

## 6. Comparison point: does data.riksdagen.se distinguish dataset reuse from agency-authored prose?

**Partially — informative by analogy.** Page: **"Användningsvillkor"** — https://www.riksdagen.se/sv/dokument-och-lagar/riksdagens-oppna-data/anvandarstod/anvandningsvillkor/ (fetched directly).

Key points:
- General permission: *"Riksdagens öppna data är fria att användas och spridas vidare så länge du anger källa"* ("Riksdagen's open data is free to use and distribute further as long as you cite the source") — same shape as Migrationsverket's notice: free reuse conditioned on attribution ("Källa: Sveriges riksdag" / "Source: The Swedish Parliament").
- Explicit copyright carve-out: *"Material i riksdagens öppna data som är skyddat enligt upphovsrättslagen (1960:729) får inte återges eller tillgängliggöras för allmänheten utan tillstånd från rättighetshavaren. Exempel på sådant material är bilder."* ("Material in Riksdagen's open data that is protected under the Copyright Act (1960:729) may not be reproduced or made available to the public without the rights-holder's permission. Images are an example of such material.") This confirms, by the same pattern the project is already relying on for SFS law text (1960:729 §9 excludes statute/official-document text from copyright), that Riksdagen treats the *legal/document text itself* as outside copyright (freely reusable) while singling out **images** as the copyrighted exception — structurally identical to Migrationsverket's "all text free, photographs need permission" split.
- Same no-endorsement/no-logo condition as Migrationsverket: *"Det är till exempel inte tillåtet att använda riksdagens logotyp eller namnet Sveriges riksdag i tjänsten eller applikationen"* (don't use Riksdagen's logo or name in a way implying endorsement).

**Why this is informative by analogy:** both authorities converge on the same two-part model — (1) authored text/document content: free to reuse and redistribute with attribution, full stop; (2) images/logos: separately copyrighted, need permission. Neither site draws a "citation vs. bulk-copy" line, and neither site's terms were written with an MCP/open-dataset redistribution scenario in mind, but both independently reach the same permissive default for text. That convergence increases confidence that Migrationsverket's notice means what it plainly says, rather than being an oversight or a narrower-than-worded internal expectation.

---

## Open items / not verified

- **Rättsliga ställningstaganden (legal position PDFs):** I could not locate a copyright/villkor statement specific to these documents or to the Lifos platform (lifos.migrationsverket.se) that hosts many of them. Whether the general "Om webbplatsen" text notice extends to PDF documents hosted on a separate subdomain is not confirmed. **Recommend treating these as unverified and keeping them under ADR-0004's conservative default (abstract + facts + link) until a Lifos-specific check is done or Migrationsverket is asked directly**, even though the project plan (2.1) lists them as P0.
- **Processing-time / statistics pages:** covered by the same "Om webbplatsen" text notice for prose; numeric processing-time data itself is factual/non-copyrightable regardless.
- I did not get independent legal counsel and this is not legal advice — it is primary-source document research. Given this gates an irrevocable CC0/CC-BY publication decision (per ADR-0004, "一旦以 CC0 发布即不可撤回"), a short confirmatory read by someone with actual Swedish copyright-law competence before the M1 gate is still worth the cost, even though the primary-source evidence gathered here is unambiguous on its face.
