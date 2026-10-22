<div align="center">

# project-packer

**Turn what you have actually done into interview-proof project experience — push the wording as hard as the facts allow, never touch the facts themselves.**

![ci](https://github.com/ilo-love7/project-packer/actions/workflows/ci.yml/badge.svg)
![version](https://img.shields.io/badge/version-2.3.0-blue)
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
- **Two-layer audit** — `scripts/lint_resume.py` for the mechanical layer (verb blacklist / red-flag words / mixed date formats / number comparison / keyword coverage, offline and dependency-free) plus an agent semantic layer (follow-up tree / conventions / attribution).
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
│   └── example-student-work.md     # contrast example: student work without hard numbers
├── scripts/
│   ├── lint_resume.py              # offline mechanical audit (verbs / red flags / dates / numbers)
│   └── check_docs.py               # documentation consistency (version / counts / cross-refs / links)
├── tests/                          # unittest suite for both scripts (zero dependency)
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

## Lint your draft offline

The mechanical layer runs without the agent — pure standard library, no `pip install`:

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

## Development

```bash
python3 -m unittest discover -s tests -v   # unit tests for both scripts
python3 scripts/check_docs.py              # version badge / stage count / audit item count / cross-refs / links
python3 scripts/lint_resume.py references/example-battery.md --strict
```

`check_docs.py` exists because this project ships nothing but Markdown: writing "21 items" when the checklist actually has 22 produces no compiler error, it just quietly misleads. The checker turns that class of drift into a failing exit code. CI runs all three commands on Python 3.9 / 3.11 / 3.13.

## Examples

- [`references/example-battery.md`](references/example-battery.md) — reproducing the Nature Energy 2019 battery cycle-life paper → resume bullets, a 33.6%→5.9% debugging STAR, follow-up tree, honesty-boundary card.
- [`references/example-student-work.md`](references/example-student-work.md) — a 174-person English check-in activity → substitute quantification, an incentive-failure conflict STAR, and the "why no internship" script.

## Changelog

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
