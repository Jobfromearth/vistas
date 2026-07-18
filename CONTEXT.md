# Vistas

瑞典移民与求职法规的版本化数据服务,以 MCP server 形态分发给 agent 生态。核心承诺:每个回答带官方出处与"该规则何时变过"的时间线;数据可靠性是 Vistas 的责任,答案组织是调用方 agent 的责任。

## Language

### 规则与来源

**RuleChunk(规则单元)**:
入库与检索的最小内容单位,携带引用锚点和双时间轴。同一规则的历史版本通过版本链相连。
_Avoid_: 文档、条目、chunk(裸用)

**法律源(Legal Source)**:
具有法律效力的成文法文本(SFS,经 Riksdagen 开放数据 API 获取),引用锚点可达条款级。
_Avoid_: 官方源(过于宽泛——指南源也是官方的)

**指南源(Guidance Source)**:
机构对规则的散文式说明(Migrationsverket 指南页、立场文件等),无条款编号,引用锚点为页面+章节级。不具法律效力,但承载大量实务信息(处理时间、材料清单、具体门槛数字)。
_Avoid_: 网页、攻略

**引用锚点(Citation Anchor)**:
一条 RuleChunk 可被独立核验的出处定位。分层诚实:法律源 → kapitel + §;指南源 → URL + 章节标题。tool 返回必须明示锚点属于哪一层。
_Avoid_: 引用、出处(需要精确定位含义时)

### 时间

**观察区间(Observed Window)**:
"我们在此时间段内看到该内容存在"。由抓取流水线自动产出,每条 RuleChunk 必有。机器事实,不是法律事实。
_Avoid_: 抓取时间(那只是区间端点的来源)

**生效区间(Legal Validity Window)**:
规则在法律上有效的时间段。仅在可被可靠提取时才填(如 SFS 的 ikraftträdande 日期);提取不出即留空,绝不用观察区间冒充。
_Avoid_: valid_from/to 与观察区间混用

**版本链(Version Chain)**:
同一规则历史版本的有序链,新版本 supersedes 旧版本;旧版本永不删除,只关闭区间。时间线与变更日志能力均由它派生。
_Avoid_: 历史记录、修订

### 分发

**快照(Snapshot)**:
随本地 MCP 包分发的只读 SQLite 数据文件,由流水线定期构建发布。用户机器上只有快照,查询永不离开本机。
_Avoid_: 数据库(指运行形态时)、缓存

**画像(Profile)**:
调用方 agent 传入的适用性过滤参数(如 eu/non_eu、student/worker/graduate、family),即用即弃,永不存储。
_Avoid_: 用户信息、账号

### 边界

**无数据(No Data)**:
检索无法给出带引用锚点的结果时的明确返回值。宁可返回无数据,不硬凑结果。
_Avoid_: 空结果、fallback
