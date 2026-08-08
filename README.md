# A 股市场参与结构分析

> 判断一段 A 股行情究竟是 **多数股票共同参与**，还是 **少数龙头和热点在扛指数**。

`skill-a-share-market-participation` 从全市场横截面行情快照出发，把市场广度、成交集中度、投机拥挤、龙头依赖和结构脆弱性压缩成一份可复现的市场结构报告。

它适合盘中监控和盘后复盘，尤其适合回答：

- 指数涨了，但到底是普涨还是少数权重股带动？
- 今天成交额是不是过度集中在少数股票？
- 热门股票很强，但市场整体参与度是否跟得上？
- 当前市场更像健康扩散、窄幅抱团，还是投机拥挤？
- 今天的参与度、流动性分布和脆弱性，相比最近历史处在什么位置？

**这不是选股器，也不是交易执行工具。** 输出用于研究和市场监控，不构成投资建议。

---

## 你可以怎么用它？

用户不需要先理解 `scripts/` 目录，也不需要自己决定脚本顺序。直接描述你想判断的市场问题即可。

### 场景 1：判断“指数上涨”到底是不是普涨

你可以直接问：

> 分析一下今天 A 股是普涨，还是少数龙头在带指数。

> 沪深 300 今天涨了，但市场广度怎么样？

> 今天上涨的资金扩散健康吗？

Skill 会重点检查：

- 上涨股票占比；
- 下跌股票占比；
- 上涨股票吸收了多少成交额；
- 个股收益中位数；
- 指数上涨时是否出现 `index-up-breadth-weak`；
- 龙头股票与其余市场之间的收益差。

如果指数上涨、但多数股票下跌，同时成交额高度集中在少数强势股票，报告会更倾向于：

```text
narrow-leadership
```

也就是：**指数看起来强，但参与结构并不宽。**

---

### 场景 2：看成交额到底集中在哪里

你可以问：

> 今天 A 股成交额是不是集中在少数股票？

> 看一下全市场 Top 10% 股票吃掉了多少成交额。

> 今天的流动性分布健康吗？

Skill 会计算：

- Top 1% / 5% / 10% 股票的成交额占比；
- Turnover Gini；
- Turnover HHI；
- Effective traded names；
- 高成交额股票是否同时也是高收益股票。

它不是只看“总成交额有多少”，而是进一步回答：

> **这些成交额到底分散在整个市场，还是挤在很少的名字上？**

---

### 场景 3：识别热点拥挤和龙头依赖

你可以问：

> 今天是不是投机情绪很强？

> 热门股票是不是吸走了太多成交额？

> 市场是不是过度依赖少数龙头？

Skill 会同时观察：

- 高收益股票的成交额占比；
- 大涨大跌股票占比；
- 高换手股票占比；
- 振幅；
- 龙头收益与其余股票中位数之间的差距；
- 热门股票是否收在日内高位附近。

这样可以区分两种看起来都“很热”的行情：

```text
广泛参与 + 热度高
```

和：

```text
少数热点极热 + 大多数股票参与不足
```

后者通常会表现出更高的结构脆弱性。

---

### 场景 4：判断今天的结构是否异常

如果你提供历史指标文件，可以直接问：

> 今天的市场参与度在最近历史上算高还是低？

> 今天的成交集中度是不是近期极端？

> 把今天和过去一段时间的市场结构做个对比。

Skill 会把当前指标放进历史分布中，给出 percentile，例如：

```text
Participation               25th percentile
Liquidity distribution       0th percentile
Speculation                  67th percentile
Fragility risk              100th percentile
```

这比只看一个绝对分数更有意义，因为同样的成交集中度，在不同市场阶段可能代表不同的结构状态。

---

## 什么样的提示词会触发这个 Skill？

当问题明确涉及 **A 股全市场广度、参与度、成交集中、热点拥挤、龙头依赖或结构脆弱性** 时，就适合使用。

典型提示词包括：

```text
分析一下今天 A 股是普涨还是少数龙头带动。

看看今天市场参与度怎么样。

今天成交额集中在哪里？

指数涨了，但个股是不是其实很弱？

今天是不是热点抱团？

A 股现在投机拥挤程度高吗？

市场流动性分布健康吗？

今天的结构脆弱性高不高？

和最近历史相比，今天的市场广度算什么水平？

给我生成一份今天的 A 股参与结构报告。
```

下面这些问题则不是本 Skill 的主要用途：

```text
推荐几只股票

预测明天大盘涨跌

帮我自动交易

计算订单滑点和市场冲击

做 VWAP / TWAP 执行

分析某只股票的北向、融资或大宗交易资金流
```

---

## 一份报告会告诉你什么？

报告核心由 **1 个状态 + 4 个分数 + 一组结构指标和风险标记** 组成。

### 市场状态

最终状态会落在以下 6 类之一：

| 状态 | 含义 |
|---|---|
| `broad-participation` | 多数股票共同参与，成交和上涨较为扩散 |
| `balanced-rotation` | 市场结构相对均衡，没有明显扩散或压力占主导 |
| `narrow-leadership` | 指数或活跃度主要由少数龙头推动 |
| `speculative-crowding` | 投机强度和结构脆弱性同时偏高 |
| `defensive-contraction` | 市场参与度明显收缩，但尚未出现极端拥挤压力 |
| `deleveraging-stress` | 参与度很弱，同时脆弱性和抛压结构明显升高 |

### 四个核心分数

| 分数 | 0–100 代表什么 |
|---|---|
| **Participation** | 上涨和成交是否广泛扩散到更多股票 |
| **Liquidity distribution** | 成交是否分散，而不是集中在少数股票 |
| **Speculation** | 大波动、高换手、热点成交是否活跃 |
| **Fragility risk** | 市场是否过度依赖集中成交、龙头和少数热点 |

这些分数是**描述性启发指标**，不是收益预测、仓位建议或交易信号。

---

## 示例：什么叫“窄幅龙头行情”？

仓库内置的合成样例会生成类似下面的结果：

```text
State: narrow-leadership

Participation              45.0
Liquidity distribution     46.4
Speculation                54.1
Fragility risk             68.5

Advancers                  41.7%
Decliners                  58.3%
Turnover in advancers      79.8%
Median stock return        -0.46%
Top 10% turnover share     49.3%
Effective traded names     19 / 60
Leadership spread          +7.06pp
```

这组数据表达的是：

> 虽然大量成交额集中在上涨股票，但全市场多数股票仍然下跌，且 Top 10% 股票占据接近一半成交额，龙头收益显著领先其余市场。

因此报告将其归类为：

```text
narrow-leadership
```

而不是把“指数涨、成交活跃”简单理解成全市场健康。

---

## 最简单的使用方式

### 方式一：直接让 Agent 获取最新市场快照

如果运行环境已经配置 PandaData 或 AKShare，可以直接说：

> 抓取今天最新 A 股数据，判断是普涨还是少数龙头带动，并生成市场参与结构报告。

内部流程是：

```text
自然语言需求
      ↓
获取最新全 A 快照
      ↓
校验交易日 / 数据源 / 行数
      ↓
计算市场广度、成交集中、拥挤与脆弱性
      ↓
生成 Markdown + JSON 报告
```

实时数据源顺序固定为：

1. **PandaData** — 主数据源；
2. **AKShare** — PandaData 不可用时的备用数据源。

不会用新闻网页、搜索结果或临时网页爬虫来代替全市场行情。

### 方式二：上传自己的 CSV

如果你已经有全市场行情快照，只需要最少三列：

```csv
code,pct_change,amount
600000,6.20,2400000000
600001,5.10,2100000000
600002,-0.80,180000000
```

然后可以直接说：

> 用这个 CSV 分析今天的 A 股市场参与结构。

分析器还支持股票名称、换手率、振幅、高低开收、流通市值、行业等可选字段。完整输入约定见 [references/input-contract.md](references/input-contract.md)。

---

## 30 秒离线体验

不联网也可以直接跑内置合成样例。

安装依赖：

```bash
python -m pip install -r requirements.txt
```

运行：

```bash
python scripts/analyze_market_participation.py examples/sample_snapshot.csv \
  --date 2026-08-06 \
  --index-return 0.86 \
  --history examples/sample_history.csv \
  --out-json example-report.json \
  --out-md example-report.md
```

成功后会生成：

```text
example-report.json
example-report.md
```

内置样例预期状态为：

```text
narrow-leadership
```

并会看到约：

```text
Participation          45.0
Liquidity distribution 46.4
Speculation            54.1
Fragility risk         68.5
```

`examples/` 中的数据是**合成测试数据**，只用于验证计算逻辑，不代表任何真实交易日。

---

## 获取实时快照

### 使用 `uv`

首次初始化：

```bash
uv sync
```

抓取：

```bash
uv run --no-sync --no-cache a-share-snapshot \
  --out a_share_spot.csv \
  --benchmark 沪深300
```

### 只使用 Python

```bash
python scripts/fetch_akshare_snapshot.py \
  --out a_share_spot.csv \
  --benchmark 沪深300
```

成功后生成：

```text
a_share_spot.csv
a_share_spot.meta.json
```

元数据会记录交易日、抓取时间、数据源、行数和基准名称。

如果使用 PandaData 自动登录，可通过环境变量提供凭证：

```text
PANDA_DATA_USERNAME=your_username
PANDA_DATA_PASSWORD=your_password
PANDA_DATA_BASE_URL=http://pandadata.pandaaiquant.com
```

不要提交或分发包含真实账号密码的 `.env`。

---

## 生成正式报告

```bash
python scripts/analyze_market_participation.py a_share_spot.csv \
  --meta a_share_spot.meta.json \
  --out-json report.json \
  --out-md report.md
```

如果有历史指标文件：

```bash
python scripts/analyze_market_participation.py a_share_spot.csv \
  --meta a_share_spot.meta.json \
  --history market_history.csv \
  --out-json report.json \
  --out-md report.md
```

报告确认无误后，才建议使用 `--append-history` 将当前交易日加入历史样本。

---

## 输出结构

JSON 顶层主要包括：

```text
state
scores
breadth
liquidity_distribution
crowding
risk_flags
constructive_signals
top_turnover_names
industries
history_context
source_meta
```

其中：

- `state`：当前市场结构分类；
- `scores`：四个 0–100 分数；
- `breadth`：上涨占比、成交广度和收益分布；
- `liquidity_distribution`：成交集中度和有效参与股票数；
- `crowding`：热点、高换手和龙头依赖；
- `risk_flags`：确定性风险标记；
- `constructive_signals`：结构较健康时的正向标记；
- `history_context`：相对历史分位；
- `source_meta`：数据日期、来源和抓取元信息。

完整输出约定见 [references/output-contract.md](references/output-contract.md)。

---

## Reviewer / Maintainer：如何验收？

### 1. 运行单元测试

```bash
python -m unittest discover -s tests -v
```

### 2. 跑离线样例

```bash
python scripts/analyze_market_participation.py examples/sample_snapshot.csv \
  --date 2026-08-06 \
  --index-return 0.86 \
  --history examples/sample_history.csv \
  --out-json /tmp/a-share-participation.json \
  --out-md /tmp/a-share-participation.md
```

验收时至少确认：

```text
state ≈ narrow-leadership
participation ≈ 45.0
liquidity distribution ≈ 46.4
speculation ≈ 54.1
fragility risk ≈ 68.5
```

### 3. 可选：验证实时数据链路

在已经配置 PandaData / AKShare 的环境中运行：

```bash
python scripts/fetch_akshare_snapshot.py --out live_snapshot.csv
python scripts/analyze_market_participation.py live_snapshot.csv \
  --meta live_snapshot.meta.json \
  --out-json live_report.json \
  --out-md live_report.md
```

实时验收应同时检查：

- metadata 中的交易日是否符合预期；
- 数据源是否明确记录；
- 股票行数是否合理；
- 报告是否明确区分盘中与盘后数据。

---

## 方法边界

详细指标定义、打分和状态规则见 [references/methodology.md](references/methodology.md)。使用时需要特别注意：

- 单日横截面只能描述**当日市场结构**，不能证明因果关系；
- 盘中快照是临时状态，不能和收盘快照直接当成同一口径比较；
- `Speculation Score` 衡量的是投机强度，不天然代表看多或看空；
- 高成交集中度不一定是坏事，应结合市场广度、龙头依赖和历史分位一起解释；
- 日线横截面无法推断订单簿深度、队列位置、bid-ask spread、冲击成本或成交质量；
- 本 Skill 不做订单路由、VWAP/TWAP、fill simulation、slippage 或 TCA；
- 本 Skill 不做单只股票的融资融券、北向资金或大宗交易资金流归因。

---

## 项目结构

```text
skill-a-share-market-participation/
├── SKILL.md
├── README.md
├── LICENSE
├── requirements.txt
├── pyproject.toml
├── scripts/
│   ├── fetch_akshare_snapshot.py
│   └── analyze_market_participation.py
├── references/
│   ├── input-contract.md
│   ├── methodology.md
│   └── output-contract.md
├── examples/
│   ├── sample_snapshot.csv
│   ├── sample_history.csv
│   └── sample_report.md
└── tests/
```

---

## QuantSkills 项目声明

本项目是 **Community Project**，用于量化研究、市场监控和教育示例，不代表 QuantSkills 官方认证、背书或投资观点。

- **项目类型**：Skill
- **研究对象**：A 股全市场横截面参与结构
- **主要数据源**：PandaData；AKShare 作为备用
- **核心输入**：股票代码、涨跌幅、成交额；可选换手率、振幅、市值、行业等
- **主要输出**：市场状态、四个结构分数、广度/集中度/拥挤指标、风险标记、历史分位
- **验证方式**：内置合成输入、预期输出、单元测试和可选实时数据链路
- **许可证**：MIT

**仅供研究与教育，不构成投资建议，不承诺收益，也不代表任何表面市场结构一定会延续或反转。**
