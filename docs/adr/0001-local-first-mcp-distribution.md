# 本地优先的 MCP 分发,远程托管延后

v2 计划原定"远程 streamable HTTP 为主、本地 stdio 为副"。我们反转了这个顺序:交付形态为本地 stdio MCP 包(`uvx vistas-mcp`)+ 随包分发的只读 SQLite 快照,数据流水线跑在 GitHub Actions 上,不部署任何服务器。理由:① 用户 query(可能含移民身份等高敏感个人信息)永不离开用户机器,GDPR 合规面趋近于零——远程形态下 IP 限流与可观测 trace 均构成个人数据处理,与"零个人数据"承诺矛盾;② 无 VPS 容量与运维负担;③ 触达面(Claude Code / Codex 等 stdio 客户端用户)与已接受的"会用 agent 的小众"早期用户定位一致。

## Considered Options

- **远程为主(v2 原案)**:多触达 claude.ai 网页/手机用户,代价是 GDPR 全套义务、服务器运维、滥用面。若未来出现真实需求信号,同一代码加 HTTP 壳即可远程化,届时按"隐私由设计"(内存限流、不存 query 原文、短留存日志)补齐。
- **MCP + 薄前端**:触达面最大,但重新引入 v2 刚砍掉的前端栈、LLM API 成本与自由生成风险面。已拒绝。

## Consequences

- 远程化被保留在路线图,不是永久放弃;检索层 API 化设计需保持可加壳。
- 与 Kollega 共享后端基建(FastAPI/Postgres/Redis/ARQ)的叙事不再成立,两项目技术栈分叉(见 ADR-0003)。
