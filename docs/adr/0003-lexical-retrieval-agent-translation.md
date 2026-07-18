# 词法检索为内核,翻译交给调用方 agent

检索层不使用 embedding 模型:SQLite FTS5(BM25)+ 瑞/英同义词表 + 按签证类型/主题的结构化索引。跨语言问题由调用方 agent 解决——tool 描述与 SKILL.md 要求 query 参数为瑞典语/英语关键词,agent 负责把用户的中文/任意语言问题翻译改写后再调用。

## 为什么放弃 v2 的三路召回(bge-m3 + BM25 + reranker)

① 多语言 embedding 模型 2GB+,无法随 pip 包分发,而本地优先分发(ADR-0001)要求快照+代码秒级安装;② 语料总量仅数千 chunk,词法+结构化导航的召回上限足够高;③ 这是 v2 自身哲学("query 改写、答案组织交给上层 agent")的彻底执行——agent 本来就擅长翻译。

## Consequences

- 召回质量押注在 agent 翻译质量上,评测集必须包含"中文原始问题 → agent 翻译 → 检索命中"的端到端用例;若评测证明词法不够,升级路径是可选的小型量化 embedding(ONNX),不回到 2GB 模型。
- 不需要 GPU、推理服务或向量库,pgvector 从技术栈中移除。
