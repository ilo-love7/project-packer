<div align="center">

# project-packer

**Turn what you have actually done into interview-proof project experience — push the wording as hard as the facts allow, never touch the facts themselves.**

![ci](https://github.com/ilo-love7/project-packer/actions/workflows/ci.yml/badge.svg)
![version](https://img.shields.io/badge/version-2.9.0-blue)
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
- **Five-layer audit** — four executable checks plus one semantic layer: `lint_resume.py` (verbs / red flags / yellow words / dates / numbers / keywords), `trace_numbers.py` (every number back to a file:line in your workspace), `scan_privacy.py` (secrets and PII, masked on output), `check_facts.py` (one ledger against several resume versions — cross-version conflicts, unrecorded numbers, idle material), then the agent's semantic pass (follow-up tree / conventions / attribution). Nothing ships with an unresolved fail.
- **JD parsing** — paste the job description whole; `parse_jd.py` turns it into a grouped, frequency-sorted keyword list and prints the exact `--keywords` string the linter takes. High-frequency words are hard requirements, single mentions are bonuses, and that ordering is the priority order for the evidence map.
- **Multi-project budgeting** — one page holds 12–20 lines of project experience, so "how many projects, how many bullets each, who goes first" is arithmetic rather than taste. A 3-axis score (job fit + defence score + distinctiveness) sorts every experience into L1 full / L2 compact / L3 one-liner / L4 interview-only; a project with a defence score of 0 can never exceed L2, and projects are ordered by relevance rather than recency. Cut material moves into the fact ledger, never into the bin.
- **English and internship branches** — an English job description does not produce a translation, it produces a different writing system: past-tense verbs first, articles dropped, units kept, one spelling convention, 120 characters per line. Having an internship flips the discipline from "push the wording" to "be precise" — the evidence is stronger, but so is the verification: NDA boundaries, a clear statement of which part was yours, and the four questions every internship gets asked.
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
│   ├── example-software.md         # software example: self-measured metrics + three job-target variants
│   ├── example-delivery.md         # a fully filled delivery package (all seven sections)
│   ├── multi-project.md            # fitting several projects onto one page: budget, tiers, scoring, ordering
│   ├── english-resume.md           # writing the English version: rules, Chinglish table, before/after
│   └── with-internship.md          # when you DO have an internship: NDA lines, ownership, four questions
├── templates/                      # copy-paste starting points
│   ├── facts.template.md           # fact ledger skeleton
│   ├── question-bank.template.md   # interview question bank skeleton
│   └── delivery.template.md        # the full delivery package skeleton
├── scripts/
│   ├── lint_resume.py              # mechanical audit (verbs / red flags / yellow words / dates / numbers)
│   ├── parse_jd.py                 # turns a raw job description into the keyword list
│   ├── trace_numbers.py            # traces every number in a draft back to a real file
│   ├── check_timeline.py           # merged timeline: reversed ranges, overlaps, gaps
│   ├── check_facts.py              # one ledger x several resume versions: conflicts / orphans / idle
│   ├── scan_privacy.py             # secrets and PII scanner, masks what it finds
│   ├── check_docs.py               # documentation consistency (version / counts / cross-refs / links)
│   └── _common.py                  # shared file walker used by the two scanners
├── tests/                          # unittest suite for all seven scripts (zero dependency)
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

Five checks run without the agent — pure standard library, no `pip install`. They are the executable form of the five claims this skill makes: *the wording is defensible*, *the numbers are real*, *nothing private leaked*, *the versions agree with each other*, *the timeline holds up*.

### 1. Mechanical audit — `lint_resume.py`

```bash
# basic: verbs / red-flag words / yellow words / mixed date formats / overlong bullets
python3 scripts/lint_resume.py resume.md

# cross-check every number against the fact ledger, and score JD keyword coverage
python3 scripts/lint_resume.py resume.md --facts facts.md --keywords "Python,SQL,A/B testing"

# let the tool pull the keywords out of the job description itself
python3 scripts/lint_resume.py resume.md --facts facts.md --jd jd.txt

# machine-readable, for wiring into your own pipeline
python3 scripts/lint_resume.py resume.md --facts facts.md --json
```

| Flag | Effect |
|---|---|
| `--facts facts.md` | Flags any significant number in the draft that never appears in the ledger |
| `--keywords "a,b,c"` | Prints JD keyword coverage plus the missing list |
| `--jd jd.txt` | Extracts keywords from the raw JD and merges them into `--keywords` |
| `--max-width N` | Bullet length limit in display width (default 150 ≈ two lines; CJK counts as 2) |
| `--min-number N` | Numbers below N without a decimal point or `%` are treated as incidental and skipped (default 10) |
| `--strict` | Treat warnings as failures, for use in CI |
| `--json` | Emit structured JSON instead of text |

Exit codes: `0` clean ｜ `1` warnings only ｜ `2` errors present.

**R7, the yellow words.** `integrity-audit.md` has always said that 优化/主导/自动化 need a qualifier, but "need a qualifier" was a judgement call. R7 turns it into three questions with three different answers, because each class of word is missing a different thing: an *effect* word (优化/提升/降低/缩短/减少/加速/改善/提高) needs a comparison — `X→Y`, `从 N 到 M`, `降至 N`, or any `%`; an *ownership* word (主导/牵头/独立完成/全权) needs a scope — a headcount or module count, or a team qualifier; a *degree* word (自动化) needs coverage — a percentage, a step count, or a trigger frequency.

It is deliberately `WARN` only. A red-flag word can be failed outright (自主研发 is wrong however you phrase it); a yellow word cannot, because "优化思路来自导师评审" is a perfectly honest sentence that happens to contain 优化. R7 asks a question, it does not pass a verdict. Two cases it refuses to flag: a word in quotes (an audit table saying `"主导" → fix` is documenting the problem, not committing it), and a word at the end of a clause (`活动确为副部长牵头` describes who led, it does not claim you did) — without that second rule, every delivery package would warn on its own audit section. It also only looks at resume bullets, not prose, so the STAR script in section 3 of a delivery package is exempt.

Two things it cannot check and says so: whether 提出 is genuinely original, and whether a scoped 主导 was really yours. Both are evidence questions, not vocabulary questions — that is what the follow-up tree is for.

`parse_jd.py` also runs standalone when you want to see what it found and why:

```bash
python3 scripts/parse_jd.py jd.txt              # grouped report + a ready-made --keywords string
python3 scripts/parse_jd.py jd.txt --keywords-only
```

It matches a built-in vocabulary of common role terms (hard skills / tools and platforms / soft skills), then adds anything else that looks technical — contains a digit, a `+`/`#`, is all caps, or is camelCase — behind a stoplist so `THE` and `AND` never become keywords. The honest limit: a Chinese term outside the vocabulary will not be found, which is what `--extra` is for. Nothing is invented to fill the gap.

Note on the noise filter: a draft is full of incidental numbers ("spent 3 hours debugging"). Comparing every one of them against the ledger drowns the real warnings, so only numbers with a decimal point, a `%` sign, or a value at or above the threshold are checked one by one. The rest are counted and reported as a single informational line.

Note on what R4 does *not* check: a delivery package's STAR sections are also `- ` list items, but they are spoken scripts, not two-line resume bullets. Lines ending in a full stop are treated as prose and skipped, with an informational line saying how many. The cost is explicit — an English bullet ending in a period escapes the length check, so end English bullets with a semicolon.

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

### 4. Ledger reconciliation — `check_facts.py`

The rule "numbers are identical across every version" was, until now, a sentence in a document. `lint_resume.py --facts` compares one draft against one ledger; it cannot see that two resumes disagree with each other.

```bash
python3 scripts/check_facts.py facts.md 简历-后端.md 简历-测试.md
python3 scripts/check_facts.py facts.md "简历-*.md"
```

```
[CONFLICT] 「中位误差 #%，覆盖 # 人」第 1 个数字
           简历-后端.md:L5  5.9
           简历-测试.md:L5  6.4
           → 同一指标跨版本数字不一致，比措辞弱致命得多，先对齐再交稿

[ORPHAN] 简历-测试.md：2 个数字不在档案里
           L7  40  「另做了 #% 的优化」
           → 先入档（数字 + 口径 + 证据指针）再定稿，否则下次包装又会漂

[IDLE] 档案里有 3 个数字没进任何版本（素材闲置）
           61 / 7 / 20
```

Two confidence levels, and the split is the point:

| Level | How it is detected | Exit |
|---|---|---|
| `CONFLICT` | The whole line, with every number replaced by `#`, is identical across versions but one value differs — a copy-paste followed by a quiet edit. Zero false positives. | 2 |
| `SUSPECT` | The wording differs (an L1 full version and an L2 compact version naturally differ) but the six characters on each side of the number match, across different files. Can be a false positive, so it is a warning for a human to confirm. | 1 |

What neither catches: the same metric reworded so thoroughly that even the surrounding words change. The tool reports what it can prove; guessing at the rest would train users to ignore it. `IDLE` is deliberately informational — L4 material is *supposed* to stay off the resume.

### 5. Timeline — `check_timeline.py`

"Check the overall timeline" was the last hard constraint with no executable form. `lint_resume.py` checks that date *formats* are consistent; it says nothing about how the ranges relate.

```bash
python3 scripts/check_timeline.py resume.md
python3 scripts/check_timeline.py resume.md --today 2026.10 --gap-months 3
```

```
总时间轴
  2022.09 - 2026.06   XX大学 计算机科学与技术（本科）
  2024.05               校级一等奖学金
  2025.03 - 2025.06   XX科技 后端开发实习生（全职）
  2025.05 - 2025.08   YY网络 数据平台实习生（全职）
  2025.09 - 2025.12   校园二手书交易服务（课程项目 · 3 小组）

[ERROR] REVERSED 区间倒挂：2025.12-2025.09「毕业设计：推荐系统」结束早于开始
[WARN]  OVERLAP 2025.05-2025.06 重叠 2 个月：「XX科技 后端开发实习生（全职）」×「YY网络 数据平台实习生（全职）」 两段都声称占满时间 → 确认是否矛盾
```

The merged timeline is the actual deliverable here — it is what "核对总时间轴" looks like when it becomes a command instead of an instruction. Noise control is deliberate and matters more than coverage:

| Suppressed | Why |
|---|---|
| Overlap with an education entry | A degree spans four years; every internship overlaps it. Reporting it means three yellow lines on every student resume. |
| Two entries with an identical range | Two course projects in the same semester is normal, not a contradiction. |
| Point dates (awards, certificates) | They are not spans, so they cannot overlap anything. |
| Table rows | A delivery package's audit table is full of dates; parsing them invents overlaps and reversals out of nowhere. |

Overlap is only a `WARN` when **both** sides claim to occupy full time (`全职` / `实习` / `在职`). Otherwise it is `INFO` and labelled as parallel experience. Reversed ranges are the only `ERROR`, because they are the only thing that is unambiguously wrong.

## Development

```bash
python3 -m unittest discover -s tests -v   # unit tests for all seven scripts
python3 scripts/check_docs.py              # version / stage count / audit items / cross-refs / links / eval numbering / changelog / tree / paths
python3 scripts/lint_resume.py references/example-battery.md --strict
python3 scripts/lint_resume.py references/example-delivery.md --strict
python3 scripts/check_timeline.py references/example-delivery.md --today 2026.10
```

`check_docs.py` exists because this project ships nothing but Markdown: writing "21 items" when the checklist actually has 22 produces no compiler error, it just quietly misleads. The checker turns that class of drift into a failing exit code — eleven checks, including four added after they caught real mistakes here: an eval group that skipped a number, a version bumped without a changelog entry, a new `references/` file missing from the README directory tree, and a `references/…` path in `SKILL.md` pointing at a file that does not exist. CI runs all three commands on Python 3.9 / 3.11 / 3.13.

## Examples

- [`references/example-battery.md`](references/example-battery.md) — reproducing the Nature Energy 2019 battery cycle-life paper → resume bullets, a 33.6%→5.9% debugging STAR, follow-up tree, honesty-boundary card.
- [`references/example-student-work.md`](references/example-student-work.md) — a 174-person English check-in activity → substitute quantification, an incentive-failure conflict STAR, and the "why no internship" script.
- [`references/example-software.md`](references/example-software.md) — a three-person course project backend → p95 480ms→90ms, coverage 61%→84%, CI 7m20s→2m10s; shows the same experience rewritten for a backend, a QA and a platform role, plus how to answer "is this all your own work?" on a team project.
- [`references/example-delivery.md`](references/example-delivery.md) — the same experience as a **finished delivery package**: all seven sections filled, including the evidence table, the defence-score card, the audit report and the revision log. The resume block is four lines; the other six sections are why those four lines are allowed to exist.

## Choosing what to show

Most people's problem is not writing one experience well — it is having five and a page that fits two. [`references/multi-project.md`](references/multi-project.md) treats that as arithmetic:

| Projects | Bullets each | Verdict |
|---|---|---|
| 2 | 5–6 | sweet spot — each one gets room to breathe |
| 3 | 3–4 | workable, but one must clearly lead |
| 4 | 2–3 | all shallow, none memorable |
| 5+ | 1–2 | a list, not a resume |

Every experience gets scored 0–3 on three axes (job fit / defence score / distinctiveness) and lands in one of four tiers: **L1** full (4–6 bullets) ｜ **L2** compact (2–3) ｜ **L3** one line under "Other projects" ｜ **L4** interview-only, off the resume. A defence score of 0 caps an experience at L2 no matter how good the rest looks. Ordering is by relevance, not recency — the first project carries the memory hook.

What gets cut does not get deleted: it moves into `facts.md` and the follow-up tree, waiting for "tell me about something else you built". **What you are cutting is page space, not material.**

## Start here

Three files exist purely so the first run does not start from a blank page:

| File | When |
|---|---|
| [`templates/facts.template.md`](templates/facts.template.md) | Copy to `facts.md` before packaging anything. The number table header (number / convention / evidence pointer / how to obtain / defence score) is what the machine checks align against. |
| [`templates/delivery.template.md`](templates/delivery.template.md) | Copy at stage 5. The section order is fixed: resume block first, because that is where 80% of the reading happens. |
| [`templates/question-bank.template.md`](templates/question-bank.template.md) | Copy after your first real interview. One real question = one record, marked ✅ hit / 🟡 outside the tree / ❌ collapsed. |

## Changelog

<details>
<summary><b>v2.9.0</b> (2026-10-22) — the yellow words get a predicate</summary>

The last hard constraint with a document but no check was #3, "terminology is upgraded honestly". It turned out to be two-thirds done already: `R2` catches the red words (自主研发 / 显著优于 / 行业领先 / 填补空白) outright, and `R1` catches the soft verbs at the start of a bullet (参与 / 协助 / 负责). What nothing caught was the middle band — the words that are fine to use and wrong to use *bare*.

`R7` covers it, and the design is the interesting part. The yellow band is not one rule but three, because each class is missing a different thing:

| Class | Words | Missing | Satisfied by |
|---|---|---|---|
| Effect | 优化 提升 降低 缩短 减少 加速 改善 提高 | a comparison | `X→Y`, `从 N 到 M`, `降至 N`, any `%` |
| Ownership | 主导 牵头 独立完成 全权 | a scope | headcount / module count / 团队·小组·跨部门·全流程 |
| Degree | 自动化 | coverage | percentage, step count, 定时·每日·每周·自动触发 |

Three decisions that matter more than the word list:

**`WARN`, never `ERROR`.** A red word can be failed however it is phrased; a yellow word cannot, because the same characters can be an honest sentence. 「优化思路来自导师评审」is not a claim about results. R7 asks "where are the numbers", and the answer is allowed to be "there are none, this is context" — which is exactly what a `WARN` means.

**A word at the end of a clause is not a claim.** The first version flagged `活动确为副部长牵头 → pass` in `example-student-work.md`, a line that describes who led, not a claim that the user did. The predicate became: unquoted, *and* followed by something other than clause-ending punctuation. Without it every delivery package warns on its own audit section, because that section is written as `"主导"限真实主导：…牵头 → pass`.

**Same scope as `R4`.** Only resume bullets, not prose — the STAR script in section 3 of a delivery package is meant to be spoken, and 「我优化了接口」is what you would actually say. The cost is identical and now documented twice: a bullet ending in a full stop escapes both checks, so Chinese entries end with `；` and English entries end with `；` or nothing.

Two things R7 explicitly cannot do, and the docs say so rather than pretending: whether 提出 is genuinely original, and whether a scoped 主导 was really yours. Both are evidence questions for the follow-up tree.

One existing test had to be narrowed. `test_does_not_flag_verb_in_the_middle` asserted that `- 主导并参与模型训练` produced no warnings at all — true only while R7 did not exist. It now asserts no *`R1`* warnings, plus a new test pinning down that the mid-line 主导 is R7's business. The division of labour is now tested rather than implied.

Tests 206 → 222, and the four reference examples still produce zero `R7` warnings — the rule was tuned against them, not the other way round.

</details>

<details>
<summary><b>v2.8.0</b> (2026-10-22) — the timeline, the English version, and the internship case</summary>

Four gaps left over from the last audit, and the first one is the last hard constraint without a tool.

**`check_timeline.py`** makes "核对总时间轴" a command instead of an instruction. It merges every date range in a draft into one timeline, then reports reversed ranges (`ERROR`), future start dates (`WARN`), overlaps between two experiences that both claim full time (`WARN`), and gaps over six months (`INFO`). The merged timeline is the real deliverable — it is what the constraint was asking you to look at all along.

Most of the work went into what *not* to report, because a timeline checker that fires on every student resume gets switched off in a week. Suppressed: overlaps with an education entry (a degree spans four years, everything overlaps it), two entries with an identical range (two projects in one semester is normal), point dates like awards (not spans, cannot overlap), and table rows (a delivery package's audit table is full of dates and will invent reversals out of nowhere). Overlap is only a warning when both sides say 全职/实习/在职; otherwise it is labelled parallel experience. Four of those five rules were added after watching the first version produce noise on a realistic resume.

**`references/english-resume.md`** — the English switch used to mean "output a bilingual version", which in practice produced a translation. A translation is not an English resume: `Responsible for realizing 12 REST interfaces` is grammatically fine and reads as non-native in the first three words. The doc covers five hard rules (past-tense verb first, article policy, units never dropped, one spelling convention, 120 characters per line), a Chinglish table, the English for each carrier type (`Course Project`, never `Project Intern`), and one complete before/after where the numbers are identical across both languages.

**`references/with-internship.md`** — the reverse gap. The skill was born as `internship-packer` and then spent every release solving "no internship", saying nothing about people who have one. The discipline flips: stronger evidence, but easier verification, so the job is precision rather than force. Covers the four phrasing differences from personal projects, whether to name the company, four NDA boundaries with a script for "can you go into detail", the four questions every internship gets asked, big-company-specialist versus small-company-full-stack, and how to handle an internship shorter than three months.

**`references/drill-mode.md`** grew from 28 lines to a full spec. The gap that mattered: the old version used one set of questions for every role, but an algorithms interviewer digs at complexity, a backend interviewer digs at failure modes, a QA interviewer digs at judgement criteria. Adds a per-role table, a pressure-interview track, five angles for questions outside the tree, a battle-report template, and six anti-patterns including the one that ruins most practice sessions — going easy when the user stalls.

Tests 173 → 206.

</details>

<details>
<summary><b>v2.7.0</b> (2026-10-22) — the last four claims become executable</summary>

The pitch of this project is "every promise is a check you can run". Counting honestly, three promises had checks and four did not: *the timeline is consistent*, *the ledger is the single source of truth*, *numbers are identical across versions*, and *diff before you output*. All four were enforced only by the agent remembering to enforce them.

`check_facts.py` covers the last three at once. Point it at one ledger and any number of resume versions and it reports three things: `CONFLICT` (the same metric with different values), `ORPHAN` (a number in a resume that never made it into the ledger), and `IDLE` (ledger numbers no version uses — informational, because L4 material is supposed to stay off the resume). Conflict detection runs at two confidence levels, and the split is the interesting part. Whole-line skeleton identical but one value changed — a copy-paste followed by a quiet edit — is a `CONFLICT` with zero false positives and a failing exit code. Wording different but the six characters either side of the number matching, across files, is a `SUSPECT`: an L1 full version and an L2 compact version naturally differ, so it gets a warning and a human decision instead. What it cannot catch is a metric reworded so thoroughly that even the surrounding words change; the tool says so rather than guessing.

`parse_jd.py` fixes the input side. `--keywords` wanted a hand-split comma string; the real action is pasting the job description whole. It now gets parsed into a grouped, frequency-sorted list — high frequency means hard requirement, a single mention means bonus, and that ordering is the priority order for the evidence map. Matching is a built-in vocabulary plus a heuristic for anything that looks technical (a digit, `+`/`#`, all caps, camelCase) behind a stoplist, so `THE` and `AND` never become keywords. A Chinese term outside the vocabulary is simply not found, which is what `--extra` is for — the tool does not invent one to fill the gap. `lint_resume.py --jd` wires the two together.

`check_docs.py` gains four checks, and three of them were written because they had already caught real mistakes in this repo: an eval group that skipped a number (C8), a version bumped without a changelog entry (C9), a new `references/` file missing from the README directory tree (C10 — it caught `example-delivery.md` within a minute of being written), and a `references/…` path in `SKILL.md` pointing at nothing (C11, which the existing link check could not see because it only follows Markdown links, not backticked paths).

`references/example-delivery.md` fills the last content gap: a delivery package with all seven sections actually filled. The template was a skeleton and the three examples were fragments, so "what does the finished thing look like" had no answer.

One lint fix came out of writing it. R4 flagged the STAR sections of the delivery package as overlong bullets — they are `- ` list items, but they are spoken scripts, not two-line resume entries, and every user following the template would have received four false warnings. Lines ending in a full stop are now treated as prose, counted in an informational line. The cost is stated plainly in the docs: an English bullet ending in a period escapes the length check, so English bullets should end with a semicolon.

</details>

<details>
<summary><b>v2.6.0</b> (2026-10-22) — what to do when you have more projects than page</summary>

The skill could take one experience and make it strong. It had nothing to say about the situation almost everyone is actually in: five experiences, one page, and no basis for deciding which two to keep. That gap is now `references/multi-project.md`.

The framing is deliberately unromantic. A one-page A4 at 10.5pt holds roughly 45–52 lines of body text, of which project experience gets 12–20 — which means two projects get 5–6 bullets each and five projects get 1–2. At that point it stops being a resume and becomes a list. So the default answer is 2–3, and the decision per experience is a 3-axis score (job fit / defence score / distinctiveness, 0–3 each) that lands it in one of four tiers: L1 full, L2 compact, L3 one line under "Other projects", L4 interview-only. Two rules are non-negotiable: an experience with a defence score of 0 — pure verbal account, no evidence pointer — can never exceed L2, and projects are ordered by relevance rather than recency, because the first one carries the memory hook.

The part people resist is L4, so the document is explicit about it: **what gets cut is page space, not material.** Dropped experiences move into `facts.md` and the follow-up tree, where they answer "tell me about something else you built". Also covered: multi-version management (one ledger, several resumes, numbers identical across all of them), seven anti-patterns including "shrink the font to fit more", and full walkthroughs for the 1-project, 3-project and 6-project cases.

Also rewrites the `description` in `SKILL.md` frontmatter from 269 to 196 characters. Skill lists truncate, and a description that gets clipped loses exactly the part that triggers it — the trigger phrases now come earlier, and multi-project selection is named as a supported mode.

</details>

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
