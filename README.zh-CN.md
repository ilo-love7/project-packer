<div align="center">

# project-packer

**把真实做过的事包装成面试可防守的高强度项目经历——措辞可以拉满，事实一个不能动。**

![version](https://img.shields.io/badge/version-2.2.2-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![type](https://img.shields.io/badge/agent%20skill-SKILL.md-orange)

<p align="center">
  <a href="./README.md">English</a> · <b>简体中文</b>
</p>

</div>

---

把用户真实做过的事（课程项目、科研、竞赛、开源、学生工作）包装成**面试可防守**的高强度项目经历。

不是简历美化器，更不是造假助手。核心规则一句话：**夸大的天花板 = 追问三层的防守能力**——措辞可以拉满到事实允许的强度，事实（数字、时间、署名、隶属）一个不能动。

> 由 internship-packer（实习经历包装器）转型而来：不再触碰"实习造假"敏感点，定位为求职表达优化工具，覆盖在校生、应届校招、社招转行等更广人群。旧链接经 GitHub 重定向仍然有效。

## 核心设计

- **硬约束优先**：不虚构可核查的事实（雇主隶属/职务/时间/署名/数字）；每个量化数字必须有证据指针；术语如实升级（复现 ≠ 自研）；主动提醒 AI 协作披露口径
- **包装强度分级**：标准档（稳妥防守）与强化档（措辞拉满 + 逐条防守预案），按面试临近度选用，两档数字完全一致
- **考古模式**：直接扫描用户的工作区/仓库，从数据表和结果文件里取数字（不信口述），每条素材带证据指针和取证方式
- **措辞红绿灯**：绿（直接写）/ 黄（必须带限定词）/ 红（必须砍），交稿前逐条过
- **对抗审计**：背调审核员 + 技术面试官双视角，外加数字逐个回溯和隐私扫描，fail 项未处理不得交稿
- **载体重定位**：提前备好"这段是实习吗 / 为什么你没有实习经历"的进攻性回答，把非实习载体翻译成自驱力证据
- **事实档案**：每个用户一份 facts.md 唯一事实源（数字+口径+证据指针+两档定稿+防守分），输出前强制 diff，多次包装不漂移
- **陪练模式**：agent 扮演面试官逐层追问，三维反馈，答崩的表述降档、问题回写追问树与真题库
- **双层审计**：`scripts/lint_resume.py` 机械层（动词黑名单/红灯词/日期混用/数字比对/关键词覆盖，离线零依赖）+ agent 语义层（追问树/口径/归属）
- **防守分评分卡**：每条 bullet 0~3 分（证据强度 + 追问树覆盖），<2 分禁入强化档
- **ATS 适配**：纯文本版规范 + JD 关键词覆盖率，缺词三分类，不堆砌不隐写
- **复盘回写**：真实面试被问到但追问树里没有的问题，回写进树并沉淀真题库，命中率统计驱动下次包装

## 安装

把整个文件夹放进你的 agent 的 skills 目录：

```bash
# Claude Code
git clone https://github.com/ilo-love7/project-packer.git ~/.claude/skills/project-packer

# 其他支持 SKILL.md 规范的 agent（AgentMore 等）
# 复制到对应 skills 目录即可，确保 SKILL.md 位于根目录
```

目录结构：

```
project-packer/
├── SKILL.md                        # 主流程：6 阶段工作流 + 硬约束
├── references/
│   ├── templates.md                # 输出模板（含替代量化、载体话术）
│   ├── integrity-audit.md          # 对抗审计检查单（5 视角 21 条）
│   ├── fact-file.md                # 事实档案：唯一事实源
│   ├── drill-mode.md               # 陪练模式：面试官追问 + 回写
│   ├── example-battery.md          # 黄金示例：有硬数据的科研复现项目
│   └── example-student-work.md     # 对照示例：无硬数字的学生工作
├── scripts/
│   └── lint_resume.py              # 离线机械层审计（动词/红灯词/日期/数字）
└── evals.md                        # 回归测试用例（改版后必跑）
```

## 使用

**触发方式**：对 agent 说"帮我包装经历 / 这个项目怎么写进简历 / 没有实习经历怎么面试 / 准备面试话术"。

**三种模式自动分流**（阶段 0 判定）：

| 模式 | 适用 | 流程 |
|---|---|---|
| 快速模式 | 只想把一段经历写成简历条目 | 简版收集 → 条目 → 红灯快查，几分钟出稿 |
| 口述模式 | 直接描述经历 | 八件事一次问完 → 全流程 |
| 考古模式 | 给出仓库/工作区路径 | 扫描代码与数据提取证据 → 全流程 |

**完整产出**（全流程）：简历条目 ×4-6 ｜ STAR 故事 ×3（含追问预判树）｜ 30 秒电梯稿 ｜ 诚实边界卡 ｜ 载体重定位话术 ｜ 证据清单 ｜ 审计报告。英文 JD 自动输出双语简历条目与电梯稿。

## 示例

- [example-battery.md](references/example-battery.md)：复现 Nature Energy 2019 锂电池寿命预测项目 → 简历条目、33.6%→5.9% 排障 STAR、追问树、诚实边界卡
- [example-student-work.md](references/example-student-work.md)：174 人英语打卡活动 → 替代量化、激励失效冲突 STAR、"为什么没有实习经历"话术

## 更新日志

<details>
<summary><b>v2.2.2</b>（2026-10-15）工具链显性 + 成果大白话</summary>

简历条目新增"工具链显性"（工具/软件名必须入 bullet，ATS 关键词直接来源）与"成果大白话"（术语后跟白话解释，外行 5 秒能懂）两规则，附白话化口径红线（不歪曲统计口径）；用户反馈驱动。

</details>

<details>
<summary><b>v2.2.1</b>（2026-10-15）过程细节下沉</summary>

简历条目新增"过程细节下沉"规则——一条 bullet 只装一个动作（做了什么/用什么做/结果是什么），怎么发现、排除假设、修复细节等过程全部下沉到追问树与 STAR；dogfood 实测反馈驱动。

</details>

<details>
<summary><b>v2.2</b>（2026-10-15）事实档案、陪练、lint、防守分、ATS</summary>

新增事实档案（facts.md 唯一事实源，输出前 diff）、陪练模式（面试官对练+答崩降档回写）、离线 lint 脚本（scripts/lint_resume.py，机械层审计）、防守分评分卡（<2 分禁入强化档）、ATS 机筛适配（纯文本版+关键词覆盖三分类）、真题库沉淀、公司定制注入（查不到不编造）；evals 新增 H 组 6 条用例。

</details>

<details>
<summary><b>v2.1</b>（2026-10-15）internship-packer 转型为 project-packer</summary>

由 internship-packer 转型为 project-packer（项目经历包装器），规避实习造假敏感点、扩大适用人群；新增标准/强化两档包装强度（夸大上限=追问三层防守能力，两档数字一致，强化表述逐条配防守预案）；evals 新增 G 组 4 条用例。

</details>

<details>
<summary><b>v2.0</b>（2026-10-15）快速模式、载体重定位、替代量化</summary>

新增快速模式、载体重定位话术、替代量化路径、英文开关、复盘回写（阶段 6）、数字可复算审计（视角 E）与隐私红线；新增学生工作对照示例。

</details>

<details>
<summary><b>v1.0</b> 初始版本</summary>

六阶段工作流、硬约束、措辞红绿灯、双视角审计、电池项目黄金示例。

</details>

## License

见 [LICENSE](LICENSE)。MIT。
