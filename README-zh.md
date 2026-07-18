# Vistas

**[English](README.md)**

面向 agent 生态的瑞典移民与求职法规数据服务——每个回答都带官方出处，以及"该规则何时变过"的时间线。

不是聊天机器人，也不是网页应用：是一个**本地 MCP server**。`uvx vistas-mcp` 跑在你自己的机器上，查询一份开放许可的 SQLite 快照。你的问题永远不会离开本机——因为根本没有后端可以发给它。

- **不是法律建议**（inte juridisk rådgivning）——只是一个带出处的法规数据服务。不判断个案（"我的申请会不会被拒"），只返回规则本身，且每条都带引用。给不出引用就明确返回"无数据"，绝不硬凑。
- **分层引用，诚实到底。** 法律源（Riksdagen 开放数据的 SFS 法条）引用到条款级（kap. + §）；机构指南引用到页面+章节级。每条结果都会说明自己是哪一层——不会把指南内容包装成法条级别的精度。
- **双时间轴，而非单轴。** 每个规则版本都带一个*观察区间*（我们的抓取何时看到这条内容）；只有在源头明确给出时，才会有*法律生效区间*（它何时真正生效）。两者永不混用——详见 [ADR-0002](docs/adr/0002-bitemporal-rule-model.md)。
- **零个人数据是架构事实，不是一句承诺。** 你的查询从不离开本机，所以根本没有可收集的东西。详见 [ADR-0001](docs/adr/0001-local-first-mcp-distribution.md)。
- **数据集完全开放。** 版本化快照以 **CC-BY** 发布（需署名出处，这是 Migrationsverket 自己条款的硬性要求，见 [`docs/research/migrationsverket-villkor.md`](docs/research/migrationsverket-villkor.md)）——随便拷贝、fork、二次开发。详见 [ADR-0004](docs/adr/0004-fully-open-dataset.md)。

## 现状

已针对真实的 [Riksdagen 开放数据 API](https://data.riksdagen.se) 和 [migrationsverket.se](https://www.migrationsverket.se) 完成端到端实现与验证：

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M1 数据打通 | Riksdagen SFS 入库（Utlänningslagen 2005:716）、§级切分与法律生效日期提取；Migrationsverket 指南页入库（种子页）、章节级切分；两者均支持双时间轴版本链 | ✅ 已完成 |
| M2 MCP 最小可用 | FTS5 词法检索、stdio server | ✅ 已完成 |
| M3 版本化能力 | `rule_timeline`、`recent_changes`（提前完成）；`topic` 查找、真实画像标注、SKILL.md | 🚧 部分完成 |
| M4 评测与门禁 | GitHub Actions CI（mypy/ruff/pytest）；精标 QA 集与中文端到端评测 | 🚧 仅有 CI 骨架 |
| M5 发布 | 发布到 PyPI、快照发 GitHub Releases | ⏳ 尚未发布 |
| M6 扩展 | 跨境税务（Skatteverket/SINK）、更多 Migrationsverket P0 页面、rättsliga ställningstaganden | ⏳ 尚未实现 |

**合规状态：** 与法条文本不同，机构撰写的散文内容不会自动免版权，所以按 [ADR-0004](docs/adr/0004-fully-open-dataset.md) 的门禁，全文再分发要先核实各站使用条款。migrationsverket.se 主站的核实已经完成——网页散文内容以 **CC-BY**（需署名）整页再分发已确认可行，见 [`docs/research/migrationsverket-villkor.md`](docs/research/migrationsverket-villkor.md)，且已端到端接入一个种子页（工签雇员要求页）；扩展更多 P0 指南页只需往清单加 URL，不需要新机制。`rättsliga ställningstaganden` 法律立场文件（托管在独立的 Lifos 平台）仍未核实，继续排除在外，直到单独核实完成。

还没上 PyPI——在 M5 之前请从源码克隆运行（见下方）。

## 四个 tool

| Tool | 作用 |
|---|---|
| `search_rules` | 按关键词检索现行（或通过 `as_of_date` 检索历史）规则，可按区域/画像过滤 |
| `get_source` | 取出整个父级章节（整章法条，或整页指南）供深读 |
| `rule_timeline` | 某条规则单元的完整版本历史，附相邻版本间的 diff |
| `recent_changes` | 某日期起有哪些变更，可按区域过滤 |

每条结果都带：原文内容、分层引用锚点、官方来源链接、双时间轴、快照构建时间。

## 快速开始（源码运行）

```
git clone https://github.com/Jobfromearth/vistas.git
cd vistas
uv sync
uv run vistas-build          # 从 Riksdagen + Migrationsverket 构建本地快照
uv run vistas-mcp            # 针对该快照启动 stdio MCP server
```

把你的 MCP 客户端（Claude Code、Codex 等）指向本目录下的 `uv run vistas-mcp`。

## 开发

```
uv sync
uv run pytest -m "not live"  # 离线测试套件
uv run mypy
uv run ruff check
```

## 了解更多

- [瑞典移民助手-项目计划书.md](瑞典移民助手-项目计划书.md) — 完整项目计划书
- [CONTEXT.md](CONTEXT.md) — 领域术语表
- [docs/adr/](docs/adr/) — 架构决策记录
