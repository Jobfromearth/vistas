# 版本化数据集完全开放,放弃"不可复制"护城河叙事

版本化数据快照以开放许可公开发布在 GitHub Releases,任何人可整体复制。v2 计划书"这是别人无法一次性复制的数据资产"的叙事作废——本地优先分发(ADR-0001)本身就要求把完整快照交到每个用户手里,数据保密与开源分发不可兼得,我们选后者。

项目的真实壁垒改为:持续运转的抓取流水线、版本链的时间累积由谁维护、以及维护信誉。这与开源定位、瑞典开放数据法精神、求职作品集价值全部自洽。

## Consequences

- 指南源内容在核实各站 villkor 前,公开快照中只含摘录+结构化事实(数字、日期——事实本身无版权)+锚点链接,全文照存于流水线内部;核实通过后放开。核实是 M1 入库前置门禁。
- 一旦以 CC0 发布即不可撤回,故许可选择在首次发布快照前定案,而非事后。

## Update (2026-07-18): 许可定为 CC-BY,migrationsverket.se 文本门禁已核实通过

`docs/research/migrationsverket-villkor.md` 一手核实了 migrationsverket.se 的"Om webbplatsen"版权声明与 data.riksdagen.se 的使用条款,结论:

- **许可从"CC0 或 CC-BY 待定"收窄为确定用 CC-BY。** Migrationsverket 原文:"All text på vår webbplats är fri att använda och sprida vidare förutsatt att du anger Migrationsverket som källa"(网站上所有文本均可自由使用与再分发,前提是注明 Migrationsverket 为出处)——署名是明文的硬性条件,CC0 放弃一切条件(包括署名)与此不兼容,继续用 CC0 会技术性违反对方条款。Riksdagen 自己的开放数据条款是同一模式(自由复用+署名),因此整个数据集统一用 CC-BY,不会伤到法条部分(法条本就不受版权保护,署名要求对它只是无害的额外动作)。
- **Migrationsverket 网页散文(签证指南、处理时间页等)门禁已核实通过,可整页入库+再分发**,不再需要停留在"摘录+链接"的保守默认——前提是全链路带上 Migrationsverket 出处署名(源头到 tool 返回都不能丢)。
- **rättsliga ställningstaganden(法律立场文件,托管在 Lifos 子站)仍未核实**,找不到专门的版权声明,继续按本 ADR 原有的保守默认处理,即使计划书 2.1 节把它列为 P0。
- **开放数据法(2022:818)不是可用依据**——Migrationsverket 自己的"Öppna data"页面说其法定开放数据项目只覆盖统计数据,不含网页散文;真正依据是网站自身版权声明,不是这部法律。
- 研究报告本身声明"非正式法律意见",鉴于这是不可撤回的发布决策,建议 M5 发布前找有瑞典版权法背景的人做一次确认性复核。
