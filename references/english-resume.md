# 英文简历写法：中译英 ≠ 英文简历

`SKILL.md` 阶段 3 的「英文开关」只说"输出中英双版"，没说英文版该怎么写。这份文档补的就是这个。

**核心结论**：英文简历不是中文条目的翻译，是另一套写法。直译出来的东西语法没错，但读起来一眼就是非母语者写的——而英文简历的读者（尤其外企 HR）对这一点极其敏感。数字、时间、署名照旧一个不能动，能换的只有句式和语序。

---

## 一、五条硬规则

### 1. 动词开头，过去时（现职用现在时）

每条 bullet 的第一个词必须是动词，且是**过去式**（除非这段经历还在进行）。

| 别写 | 改写 |
|---|---|
| Responsible for the backend development | Built 12 REST endpoints for a campus bookstore service |
| Participated in performance optimization | Cut p95 latency from 480ms to 90ms by eliminating an N+1 query |
| Familiar with Python and SQL | — （技能行不是 bullet，见第四节） |

`Responsible for` / `Participated in` / `Assisted with` / `Involved in` 是英文简历里最典型的四个弱动词短语，等同于中文的「负责 / 参与 / 协助 / 涉及」。全部换成具体动作。

### 2. 冠词能省就省，但不省错

简历是电报体，`a` / `the` 在多数位置可以省略：

- ✅ `Reduced query time by 80% with composite index`
- ✅ `Built 12 REST endpoints with PostgreSQL and Redis`
- ❌ `Built the 12 REST endpoints`（定冠词在这里是错的，读者不知道指哪 12 个）

省冠词的边界：**不要省到产生歧义**。`Improved model accuracy` 没问题；`Improved accuracy of model` 缺冠词但可接受；`Improved accuracy of the model trained on public data` 里那个 `the` 必须留。

### 3. 数字紧邻结果，单位不省略

中文常写「将误差降至 5.9%」，英文要写成 `cut the median error to 5.9%`——数字跟着动词和结果，不放在句尾当尾巴。

| 别写 | 改写 |
|---|---|
| The error was reduced, reaching 5.9% finally | Cut median error from 33.6% to 5.9% over four rounds of attribution |
| Improved performance by 5.3 times | Cut p95 latency from 480ms to 90ms（locust, 200 concurrent, non-production） |

单位不能省：`480ms` 不是 `480`，`84%` 不是 `84`。口径说明用括号跟在数字后，和中文版一致。

### 4. 拼写体系全文统一

美式或英式选一个，**整份简历不许混**：

| 美式 | 英式 |
|---|---|
| optimize / analyze / modeled / labeled / center | optimise / analyse / modelled / labelled / centre |

投美企用美式，投英企/欧洲用英式，投不确定的（新加坡、香港、外企中国区）用美式。`optimization` 和 `optimisation` 同时出现，比语法错误更扎眼。

### 5. 一条 bullet 一行到一行半

英文一行约 90-120 字符（10.5pt，A4 正文宽）。超过 120 字符就会折行，折行后第二条只剩半行，视觉上很乱。

`lint_resume.py` 的 R4 用显示宽度 150 作阈值（约两行），对英文偏松。**英文简历建议用 `--max-width 120` 单独跑一遍**：

```bash
python3 scripts/lint_resume.py resume-en.md --max-width 120 --facts facts.md
```

> 注意：R4 对以句号结尾的行不检查（那是给中文 STAR 口播稿留的例外）。英文 bullet 请以分号或无标点结尾，否则长度检查不生效。

---

## 二、常见中式英语对照

这些不是语法错，是"读起来不像英文简历"。左列全部换成右列。

| 中式写法 | 问题 | 英文写法 |
|---|---|---|
| `Responsible for...` | 只说明职责，不说明产出 | 动词开头 + 结果 |
| `Successfully completed...` | `successfully` 是废话，完成了就是完成了 | 直接写动作 |
| `Greatly improved...` | `greatly` 无数值支撑，等于没说 | 用具体数字 |
| `Various tasks including A, B, C` | 罗列职责，没有重点 | 只写最重要的一件事 |
| `Learned a lot about X` | 学习不是产出 | 删，或改成"用 X 做出了 Y" |
| `Team spirit, hardworking` | 形容词自评，零信息量 | 删（软技能靠行为体现，不靠形容词） |
| `Participated in the development of...` | 参与 = 不知道你做了什么 | 写你具体做的那部分 |
| `Based on the requirement of...` | 长介词短语开头，动词被推到句尾 | 动词提到最前 |
| `Make the system more stable` | `more` 没有基准 | `Cut error rate from 4.1% to 0.3%` |
| `Data analysis ability` | 名词堆叠 | `Analyzed 3 years of transaction data with pandas` |

---

## 三、载体怎么用英文说

中文版的载体定性（课程项目 / 科研实践 / 竞赛 / 学生工作）必须同样出现在英文版里，不能翻译成更像实习的说法。这是硬约束 1 的英文版。

| 中文 | 英文 | 别写成 |
|---|---|---|
| 课程项目 | Course Project | Industry Project |
| 科研实践 / 实验室项目 | Research Project (undergraduate) | Research Intern |
| 竞赛 | Competition (e.g. MCM/ICM, Kaggle) | — |
| 学生工作 | Student Organization Role | — |
| 个人项目 | Personal Project | Side Business |
| 毕业设计 | Final-Year Thesis Project | — |
| 开源贡献 | Open-Source Contribution | Open-Source Maintainer（除非你真是 maintainer） |

`Intern` 这个词只能用在真实习上。课程项目写成 `Project Intern` 或 `Research Intern` 是英文简历里最常见的越界，背调一问就穿。

---

## 四、技能行与教育背景

技能行不是 bullet，是关键词区——它的作用是过 ATS，不是给人读。

```
Languages: Python, Java, SQL
Frameworks & Tools: PostgreSQL, Redis, Docker, Git, GitHub Actions
```

三条规则：

1. **按类别分组**，不写成一长串逗号。
2. **只写用过的**，写了就要能在项目里被问到。
3. **不写熟练度**（`Proficient` / `Familiar` / `Basic` 都无法验证，且容易自相矛盾）。真要区分，用分组：`Languages` 放主力，`Also familiar` 放次要。

教育背景的英文写法：

```
B.Eng. in Computer Science, XX University        2022.09 – 2026.06
GPA: 3.7/4.0 (top 15%)
```

`B.Eng.` / `B.S.` / `B.Sc.` 选学校官方译名那一个，别自创。GPA 只在有优势时写，且必须注明满分制。

---

## 五、一个完整的 before / after

中文定稿（强化档）：

```text
校园二手书交易服务（课程项目 · 3 人小组，负责后端）        2025.09-2025.12
· 实现 12 个 REST 接口（图书 CRUD / 订单 / 搜索），PostgreSQL 存储 + Redis
  缓存，服务 3.4 万条种子数据；
· 定位并消除 N+1 查询，补 3 个复合索引，本机压测 p95 从 480ms 降至 90ms
  （locust，200 并发，非生产环境）；
· 补 47 个 pytest 用例，行覆盖率从 61% 提到 84%；
· 重构 GitHub Actions 为 lint / test / bench 三个 job 并加依赖缓存，CI 时长
  从 7 分 20 秒降到 2 分 10 秒。
```

**直译版（别这么写）**：

```text
Campus Second-hand Book Trading Service (Course Project, 3-person team, responsible for backend)
· Responsible for realizing 12 REST interfaces (book CRUD / order / search), using
  PostgreSQL storage and Redis cache, serving 34 thousand seed data;
· Located and eliminated N+1 query, added 3 composite indexes, local pressure test
  p95 reduced from 480ms to 90ms (locust, 200 concurrency, non-production environment);
· Supplemented 47 pytest cases, line coverage increased from 61% to 84%;
· Refactored GitHub Actions into lint / test / bench three jobs and added dependency
  cache, CI time reduced from 7 minutes 20 seconds to 2 minutes 10 seconds.
```

问题：`responsible for realizing`、`pressure test`（应为 load test）、`supplemented`（应补 write）、`increased from...to`（弱于 raise from...to）、`34 thousand seed data`（data 不可数）、每条都是"做了什么 + 被动词组"。

**改写版（英文简历写法）**：

```text
Campus Second-Hand Bookstore — Backend (Course Project, team of 3)      Sep 2025 – Dec 2025
· Built 12 REST endpoints (book CRUD, orders, search) on PostgreSQL with Redis caching,
  serving 34k rows of seed data.
· Traced a 480ms p95 to an N+1 query, added 3 composite indexes, and cut p95 to 90ms
  (locust, 200 concurrent, non-production).
· Raised line coverage from 61% to 84% with 47 pytest cases.
· Split CI into lint / test / bench jobs with dependency caching, cutting build time
  from 7m20s to 2m10s.
```

改了什么：

| 项 | 直译版 | 改写版 | 为什么 |
|---|---|---|---|
| 开头 | `Responsible for realizing` | `Built` / `Traced` / `Raised` / `Split` | 动词开头，且是具体动作 |
| 时间 | `2025.09-2025.12` | `Sep 2025 – Dec 2025` | 英文简历的时间格式惯例 |
| 数字单位 | `34 thousand seed data` | `34k rows of seed data` | `data` 不可数，`rows` 才是可数的 |
| 压测 | `pressure test` | `locust, 200 concurrent` | `pressure test` 不是英文里的说法 |
| 覆盖率 | `increased from 61% to 84%` | `Raised ... from 61% to 84%` | `raise` 比 `increase` 更主动 |
| CI | `7 minutes 20 seconds` | `7m20s` | 简历里时间用缩写，省版面 |
| 句末 | 分号 `;` | 句号 `.` | 英文 bullet 用句号；**但注意 R4 会因此跳过长度检查**，见第一节第 5 条 |

数字全部一致：12 / 34k / 480ms / 90ms / 3 / 61% / 84% / 47 / 7m20s / 2m10s。这是硬约束——中英两版之间数字一个都不能变，`check_facts.py` 会把两版当两个版本来对账。

---

## 六、自检清单

交英文稿前逐条过：

- [ ] 每条 bullet 都以过去式动词开头，没有 `Responsible for` / `Participated in`
- [ ] 没有 `successfully` / `greatly` / `various` 这类无信息量的修饰词
- [ ] 所有单位都在（`ms` / `%` / `k`），口径说明在括号里
- [ ] 拼写体系全文统一（美式或英式，不混）
- [ ] 载体词准确：课程项目写 `Course Project`，没有 `Intern`
- [ ] 技能行按类别分组，没写熟练度
- [ ] 每条不超过 120 字符（用 `--max-width 120` 跑过一遍）
- [ ] 中英两版的数字逐个一致（跑 `check_facts.py`）
- [ ] 中文版讲不清的地方，英文版也没硬翻——宁可少写一条
