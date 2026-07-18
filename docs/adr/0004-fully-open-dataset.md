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

## Update (2026-07-19): Lifos / rättsliga ställningstaganden 补充核实——门禁仍不放开,但找到更有力的论证方向

`docs/research/migrationsverket-lifos-villkor.md` 专门核实了上一份研究留白的这一项。结论:

- **没有找到明文许可声明**,Lifos 子站没有自己的 villkor/upphovsrätt 页面,也不引用 www.migrationsverket.se 的"Om webbplatsen"通用条款——不能假定那条通用条款覆盖 Lifos 内容。
- **但找到了一个分量更重、性质不同的论证**:rättsliga ställningstaganden 是 Migrationsverket 法务部门负责人正式签发的决定(Fastställelsebeslut)、有版本号和生效日期、对内部员工有约束力,自我描述为"Migrationsverket 对法规应如何解释的表态"。这个特征很贴近著作权法(1960:729)9 § 的"beslut av myndigheter"(机构决定)/"yttranden av svenska myndigheter"(瑞典机构声明)——和项目现在用来豁免 SFS 法条版权的是**同一条款**。退一步讲,即便够不上 9 §,同法 26a § 第二款也独立赋予任何人复制"机构撰写但不构成 9§决定/声明的公开文件"的权利,排除清单(地图、软件、教学材料、科研成果、美术/音乐/诗歌作品、商业出售物)明显不覆盖法律立场文件。
- **佐证信号**:核查的 5 份 RS 系列文件全部标记为 `publishingType: Publikt`、`accessControll: Publikt`,不在 Lifos 自己"因 GDPR/版权/保密而访问受限"的那个分类里(那类文件会带锁头图标);Migrationsverket 还主动在每份文件页面提供了引用格式,不像是想限制外传的姿态。
- **但这仍是一个法律推断,不是判例支持的定论**——没找到直接把"ställningstagande"这类文书归类到 9§还是 26a§的瑞典判例。**研究者本人明确建议:不要现在就凭这个推断放开摄取门禁**,而是把"这份文件该归 9§ 还是 26a§"这个具体问题带到 M5 发布前的确认性法律复核里去问,复核通过之前,继续维持"摘录+结构化事实+锚点链接"的保守默认。
- 另外发现文档 ID(`documentSummaryId`/`documentAttachmentId`)不是稳定长期标识符(部分旧 ID 已 404),未来如果开始摄取,应该用文件内印的 `RS/xxx/yyyy(版本号)` 编号做锚点,不能用 URL 里的数字 ID。
- **门禁状态不变**:rättsliga ställningstaganden 继续排除在公开快照之外,直到 M5 复核完成。
