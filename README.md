<div align="center">

# project-packer

**Turn what you have actually done into interview-proof project experience — push the wording as hard as the facts allow, never touch the facts themselves.**

![ci](https://github.com/ilo-love7/project-packer/actions/workflows/ci.yml/badge.svg)
![version](https://img.shields.io/badge/version-2.5.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![type](https://img.shields.io/badge/agent%20skill-SKILL.md-orange)

<p align="center">
  <b>English</b> · <a href="./README.zh-CN.md">简体中文</a>
</p>

</div>

---

An agent skill that turns real work — course projects, research, competitions, open source, student activities — into **defensible, high-impact** project experience for job applications.

This is not a resume beautifier, and it is not a fabrication assistant. The core rule in one sentence: **the ceiling of exaggeration is your ability to defend three layers of follow-up questions** — the wording can be pushed to whatever the facts support, but the facts (numbers, dates, authorship, affiliation) cannot move an inch.

> Evolved from `internship-packer` (an internship-experience packer): it no longer touches the sensitive area of faking internships, and is positioned as a job-application expression tool covering students, new graduates and career switchers. Old links still resolve through GitHub redirects.

## Core design

- **Hard constraints first** — never invent verifiable facts (employer affiliation / title / dates / authorship / numbers); every quantified number needs an evidence pointer; terminology upgrades only when truthful (reproduction ≠ original research); proactively prompts for AI-collaboration disclosure.
- **Packaging tiers** — a Standard tier (safe to defend) and an Intensified tier (wording maxed out, with a defence plan for every line), chosen by how close the interview is. Numbers are identical across both tiers.
- **Archaeology mode** — scans the user's workspace or repository and pulls numbers from data tables and result files rather than from memory; every item carries an evidence pointer and how it was obtained.
- **Wording traffic lights** — green (write it directly) / amber (needs a qualifier) / red (must be cut), checked line by line before delivery.
- **Adversarial audit** — a background-check reviewer and a technical interviewer as two viewpoints, plus number-by-number traceback and a privacy scan. Nothing ships with an unresolved fail.
- **Carrier reframing** — prepares answers to the aggressive questions ("was this an internship?" / "why do you have no internship?") in advance, translating non-internship experience into evidence of self-direction.
- **Fact ledger** — one `facts.md` as the single source of truth per user (numbers + convention + evidence pointer + both final tiers + defence score); a forced diff before every output so repeated packaging never drifts.
- **Sparring mode** — the agent plays the interviewer and drills down layer by layer with three-dimensional feedback; statements that collapse get downgraded, and the questions get written back into the follow-up tree and question bank.
- **Four-layer audit** — three executable checks plus one semantic layer: `lint_resume.py` (verbs / red flags / dates / numbers / keywords), `trace_numbers.py` (every number back to a file:line in your workspace), `scan_privacy.py` (secrets and PII, masked on output), then the agent's semantic pass (follow-up tree / conventions / attribution). Nothing ships with an unresolved fail.
- **Defence score** — each bullet gets 0–3 points (evidence strength + follow-up-tree coverage); anything below 2 is barred from the Intensified tier.
- **ATS adaptation** — a plain-text version spec plus JD keyword coverage, with missing keywords sorted into three categories; no keyword stuffing, no hidden text.
- **Retrospective write-back** — real interview questions that the follow-up tree did not anticipate get written back into the tree and banked; hit-rate statistics drive the next round.

## Install

Drop the whole folder into your agent's skills directory:

```bash
# Claude Code
git clone https://github.com/ilo-love7/project-packer.git ~/.claude/skills/project-packer

# Other agents that follow the SKILL.md spec (AgentMore, etc.)
# copy it into the corresponding skills directory, keeping SKILL.md at the root
```

Directory structure:

```
project-packer/
├── SKILL.md                        # main flow: 8-stage workflow (stage 0-7) + hard constraints
├── references/
│   ├── templates.md                # output templates (incl. substitute quantification, carrier scripts)
│   ├── integrity-audit.md          # adversarial audit checklist (5 viewpoints, 22 items)
│   ├── fact-file.md                # fact ledger: the single source of truth
│   ├── drill-mode.md               # sparring mode: interviewer drill-down + write-back
│   ├── example-battery.md          # golden example: a research reproduction with hard data
│   ├── example-student-work.md     # contrast example: student work without hard numbers
│   └── example-software.md         # software example: self-measured metrics + three job-target variants
├── templates/                      # copy-paste starting points
│   ├── facts.template.md           # fact ledger skeleton
│   ├── question-bank.template.md   # interview question bank skeleton
│   └── delivery.template.md        # the full delivery package skeleton
├── scripts/
│   ├── lint_resume.py              # mechanical audit (verbs / red flags / dates / numbers)
│   ├── trace_numbers.py            # traces every number in a draft back to a real file
│   ├── scan_privacy.py             # secrets and PII scanner, masks what it finds
│   ├── check_docs.py               # documentation consistency (version / counts / cross-refs / links)
│   └── _common.py                  # shared file walker used by the two scanners
├── tests/                          # unittest suite for all four scripts (zero dependency)
├── evals.md                        # regression test cases (must run after any revision)
└── .github/workflows/ci.yml        # tests + doc checks on every push
```

## Usage

**How to trigger it** — tell the agent: "help me package this experience", "how do I write this project on my resume", "how do I interview without an internship", "prepare my interview talking points".

**Three modes, routed automatically** (decided in stage 0):

| Mode | Fits | Flow |
|---|---|---|
| Quick | You just want one experience turned into a resume bullet | Short intake → bullet → red-flag check, a few minutes |
| Oral | You describe the experience directly | Eight questions in one pass → full flow |
| Archaeology | You give a repository or workspace path | Scan code and data for evidence → full flow |

**Full output** (complete flow): 4–6 resume bullets ｜ 3 STAR stories (with anticipated follow-up trees) ｜ a 30-second elevator pitch ｜ an honesty-boundary card ｜ carrier-reframing scripts ｜ an evidence list ｜ an audit report. For an English job description it also outputs bilingual bullets and pitch.

## Offline checks

Three checks run without the agent — pure standard library, no `pip install`. They are the executable form of the three claims this skill makes: *the wording is defensible*, *the numbers are real*, *nothing private leaked*.

### 1. Mechanical audit — `lint_resume.py`

```bash
# basic: verbs / red-flag words / mixed date formats / overlong bullets
python3 scripts/lint_resume.py resume.md

# cross-check every number against the fact ledger, and score JD keyword coverage
python3 scripts/lint_resume.py resume.md --facts facts.md --keywords "Python,SQL,A/B testing"

# machine-readable, for wiring into your own pipeline
python3 scripts/lint_resume.py resume.md --facts facts.md --json
```

| Flag | Effect |
|---|---|
| `--facts facts.md` | Flags any significant number in the draft that never appears in the ledger |
| `--keywords "a,b,c"` | Prints JD keyword coverage plus the missing list |
| `--max-width N` | Bullet length limit in display width (default 150 ≈ two lines; CJK counts as 2) |
| `--min-number N` | Numbers below N without a decimal point or `%` are treated as incidental and skipped (default 10) |
| `--strict` | Treat warnings as failures, for use in CI |
| `--json` | Emit structured JSON instead of text |

Exit codes: `0` clean ｜ `1` warnings only ｜ `2` errors present.

Note on the noise filter: a draft is full of incidental numbers ("spent 3 hours debugging"). Comparing every one of them against the ledger drowns the real warnings, so only numbers with a decimal point, a `%` sign, or a value at or above the threshold are checked one by one. The rest are counted and reported as a single informational line.

### 2. Number traceback — `trace_numbers.py`

The skill's central promise is "every number has an evidence pointer". This is that promise as a file scan:

```bash
python3 scripts/trace_numbers.py resume.md ../my-project
```

```
[HIT ] 5.9
       results/summary.csv:2  …B0005,5.9…
       docs/debug.md:1  …首跑 33.6%，四轮归因后降到 5.9%。…

[MISS] 174
       not found anywhere in the workspace → supply evidence, or downgrade to a qualitative claim
```

A `MISS` is the interesting case: either the number came from memory (which the skill forbids), or the evidence is somewhere the scan cannot see. Both need a human decision — what neither needs is the number shipping as-is.

Matching is boundary-aware, so `3` does not match inside `13` or `3.5`, and `5.9` does not match `5.95`. The draft itself is excluded, otherwise every number would trivially "hit" its own source line. Significance uses the same rule as `lint_resume.py`, so the two tools never contradict each other.

### 3. Privacy scan — `scan_privacy.py`

```bash
python3 scripts/scan_privacy.py delivery.md
python3 scripts/scan_privacy.py delivery.md --allow "138\d{8}"   # whitelist your own phone number
```

| Level | Catches |
|---|---|
| ERROR | Private key blocks, `sk-` / `ghp_` / `AKIA` / `xoxb-` tokens, credentials inside a URL, plaintext password assignments |
| WARN | ID card numbers, phone numbers, private IPs, absolute paths containing a username |
| INFO | Email addresses (a resume needs one — just confirm it is yours) |

**Everything it reports is masked before printing.** A tool that echoes your leaked API key to the terminal — where it lands in your shell history and gets pasted into a chat window — is itself a new leak. Masking depth varies by risk: secrets keep only three characters, phone numbers keep head and tail (`138****5678`), internal IPs and emails print in full because you need to see *which machine* and *which address* to fix them.

Exit codes: `0` clean ｜ `1` warnings ｜ `2` errors.

Running it against this repository itself will surface a few warnings from the scanner's own test fixtures and from the regex definitions in its source. That is expected — a rule describing `/home/<user>` naturally matches its own description. The invariant worth keeping is `ERROR = 0`, and there is a test asserting exactly that across every file in the repo.

## Development

```bash
python3 -m unittest discover -s tests -v   # unit tests for all four scripts
python3 scripts/check_docs.py              # version badge / stage count / audit item count / cross-refs / links
python3 scripts/lint_resume.py references/example-battery.md --strict
```

`check_docs.py` exists because this project ships nothing but Markdown: writing "21 items" when the checklist actually has 22 produces no compiler error, it just quietly misleads. The checker turns that class of drift into a failing exit code. CI runs all three commands on Python 3.9 / 3.11 / 3.13.

## Examples

- [`references/example-battery.md`](references/example-battery.md) — reproducing the Nature Energy 2019 battery cycle-life paper → resume bullets, a 33.6%→5.9% debugging STAR, follow-up tree, honesty-boundary card.
- [`references/example-student-work.md`](references/example-student-work.md) — a 174-person English check-in activity → substitute quantification, an incentive-failure conflict STAR, and the "why no internship" script.
- [`references/example-software.md`](references/example-software.md) — a three-person course project backend → p95 480ms→90ms, coverage 61%→84%, CI 7m20s→2m10s; shows the same experience rewritten for a backend, a QA and a platform role, plus how to answer "is this all your own work?" on a team project.

## Start here

Three files exist purely so the first run does not start from a blank page:

| File | When |
|---|---|
| [`templates/facts.template.md`](templates/facts.template.md) | Copy to `facts.md` before packaging anything. The number table header (number / convention / evidence pointer / how to obtain / defence score) is what the machine checks align against. |
| [`templates/delivery.template.md`](templates/delivery.template.md) | Copy at stage 5. The section order is fixed: resume block first, because that is where 80% of the reading happens. |
| [`templates/question-bank.template.md`](templates/question-bank.template.md) | Copy after your first real interview. One real question = one record, marked ✅ hit / 🟡 outside the tree / ❌ collapsed. |

## Changelog

<details>
<summary><b>v2.5.0</b> (2026-10-22) — templates to start from, and the missing software example</summary>

The skill described three artefacts — a fact ledger, a question bank, a delivery package — and told you to "build one following the spec". There was nothing to copy, which is the first wall a new user hits. `templates/` now holds all three, each opening with how-to-use notes and each pre-shaped so the machine checks line up with it: the ledger's number table has exactly the columns `lint_resume.py --facts` expects, and the delivery package's section order is fixed.

`references/example-software.md` fills the biggest gap in the example set. The two existing examples are a research reproduction with hard data and student work with none; neither covers the most common case, a project whose "results" you measured yourself. It walks through p95 480ms→90ms, coverage 61%→84% and CI 7m20s→2m10s, then does two things the other examples cannot: it rewrites the *same* experience three times for a backend, a QA and a platform role (same facts, different emphasis), and it shows how to answer "is this all your own work?" on a team project without either inflating or erasing your contribution.

Also fixes a lint false positive that every delivery package would have hit: R2 flagged red-flag words even when they sat inside quotes, so an audit table documenting `"自主研发" → cut` reported an error on itself. Quoted occurrences are now treated as quotation rather than assertion and counted in an informational line.

</details>

<details>
<summary><b>v2.4.0</b> (2026-10-22) — number traceback and privacy scanning become executable</summary>

Two of the skill's three promises were, until now, enforced only by the agent remembering to enforce them. Both are now file scans.

`trace_numbers.py` takes a draft and a workspace and answers one question per number: *where did this come from?* It prints `HIT` with the file and line, or `MISS` with the instruction to supply evidence or downgrade the claim. Matching is boundary-aware (`3` will not match inside `13` or `3.5`), the draft excludes itself, and significance reuses the exact same rule as the linter so the two tools cannot disagree.

`scan_privacy.py` catches private keys, `sk-`/`ghp_`/`AKIA`/`xoxb-` tokens, credentials embedded in URLs, plaintext password assignments, ID numbers, phone numbers, private IPs and username-bearing paths. It masks everything before printing — a tool that echoes a leaked key into your terminal is a new leak, not a fix — and scales the masking by risk: secrets keep three characters, phone numbers keep head and tail, internal IPs print in full because you need to see which machine to change it.

Both share `scripts/_common.py` for file walking, so they never disagree about which files exist. The suite grows from 61 to 103 tests, including a check that the repo's own scripts contain no secret-shaped strings.

</details>

<details>
<summary><b>v2.3.0</b> (2026-10-22) — test suite, CI, and a doc-consistency checker</summary>

The project now tests itself. Adds a 60-case `unittest` suite covering every lint rule (both directions: must fire and must not fire) and every documentation check; a GitHub Actions workflow running on Python 3.9 / 3.11 / 3.13; and `scripts/check_docs.py`, which verifies the version badge, stage count, audit item count, `第 N 节` cross-references, bilingual heading alignment and relative links — the class of drift that Markdown-only projects cannot catch by compiling.

Two lint rules were reworked after measuring their real output. **R4** now measures display width instead of character count (a CJK character occupies two columns, so 75 Chinese characters and 150 Latin characters are both "two lines"); **R5** only cross-checks numbers carrying a decimal point, a `%` sign, or a value at or above a threshold — an unmodified rule flagged `spent 3 hours` as an unsourced claim, and a linter that cries wolf gets switched off. Also fixes: the audit checklist had 22 items numbered up to 21 (item 16 appeared twice), the README advertised a "6-stage workflow" when `SKILL.md` had 8 stages, and eight `第 N 节` references broke silently whenever a section was inserted.

</details>

<details>
<summary><b>v2.2.2</b> (2026-10-15) — tool-chain visibility and plain-language outcomes</summary>

Resume bullets gain two rules: "tool-chain visibility" (tool and software names must appear in the bullet — they are the direct source of ATS keywords) and "plain-language outcomes" (a plain explanation follows each technical term so a non-expert understands it in five seconds), with a red line on how far plain language may go without distorting the statistic. Driven by user feedback.

</details>

<details>
<summary><b>v2.2.1</b> (2026-10-15) — push process detail down</summary>

Resume bullets gain a "process detail sinks down" rule: one bullet carries one action only (what was done / with what / what came out), while how it was discovered, which hypotheses were ruled out and the fix details all sink into the follow-up tree and STAR. Driven by dogfooding feedback.

</details>

<details>
<summary><b>v2.2</b> (2026-10-15) — fact ledger, sparring, lint, defence score, ATS</summary>

Adds the fact ledger (`facts.md` as the single source of truth, diffed before output), sparring mode (interviewer drill-down with downgrade-and-write-back), the offline lint script (`scripts/lint_resume.py`, mechanical audit layer), the defence-score card (below 2 barred from the Intensified tier), ATS screening adaptation (plain-text version + three-category keyword coverage), question-bank banking, and company-specific injection (no fabrication when nothing is found). Evals gain 6 cases in group H.

</details>

<details>
<summary><b>v2.1</b> (2026-10-15) — internship-packer becomes project-packer</summary>

Repositioned from internship-packer to project-packer (a project-experience packer), avoiding the sensitive area of internship fabrication and widening the audience. Adds Standard / Intensified packaging tiers (exaggeration ceiling = ability to defend three layers; numbers identical across tiers; every intensified line gets a defence plan). Evals gain 4 cases in group G.

</details>

<details>
<summary><b>v2.0</b> (2026-10-15) — quick mode, reframing, substitute quantification</summary>

Adds quick mode, carrier-reframing scripts, substitute quantification paths, an English switch, retrospective write-back (stage 6), a recomputable-number audit (viewpoint E) and privacy red lines; adds a student-work contrast example.

</details>

<details>
<summary><b>v1.0</b> — initial release</summary>

Six-stage workflow, hard constraints, wording traffic lights, two-viewpoint audit, and the battery-project golden example.

</details>

## License

See [LICENSE](LICENSE). MIT.
