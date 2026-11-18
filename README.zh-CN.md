# Marivo NYC Yellow Taxi Demo

[English](README.md) | [简体中文](README.zh-CN.md)

这是一个开箱即用的 Marivo 分析项目，使用 NYC TLC 官方发布的 2025 年 12 月
Yellow Taxi 行程记录和单独发布的 Taxi Zone 对照表。克隆仓库并完成初始化后，
即可在 coding agent 中使用 Marivo 语义层和分析接口。

## 初始化

环境要求：macOS、Linux 或 WSL，已安装 `make`，并能够访问网络。安装程序会
优先使用 Python 3.12 或更高版本；如果本机环境不满足要求，Marivo 安装器会
通过 `uv` 准备运行环境。

```bash
git clone <repository-url>
cd marivo-yellow-taxi-demo
make setup
```

`make setup` 安装 Marivo 并初始化 agent skills，检查两个远程文件的表结构、
验证语义层，并用源月份前七天执行实际观测。分析时，内存中的 DuckDB 通过 HTTPS
直读源文件。首次远程查询可能安装 DuckDB 的 `httpfs` 扩展。
安装器从上游解析 Marivo，重新执行 setup 可能替换本地选定的构建。

## 让 Agent 开始分析

完成 setup 后，在 coding agent 中打开本仓库并提出问题，例如：

> 比较 2025 年 12 月 1–7 日与 8–14 日的计价器车费收入。收入变化了多少？哪些上车行政区、
> 上车区域、支付方式和费率类别对差异贡献最大？在得出结论前检查数据完整性和
> 异常记录，区分计价器车费与乘客支付总额，并且不要作因果推断。

更多中文示例问题位于 [`questions/zh-CN/`](questions/zh-CN/)，英文版本位于
[`questions/en/`](questions/en/)。

## 常用命令

```bash
make verify
make semantic-snapshot
make semantic-check
make analysis-smoke
make data-verify
```

`make semantic-check` 预览代表性语义对象并检查两个区域关联。
`make semantic-snapshot` 对所有已发布语义对象逐项执行有界预览。

## 数据模型

[`cloudfront` 数据源](models/datasources/cloudfront.py) 在同一个内存 DuckDB 引擎中
读取两个独立配置的远程文件。[`yellow_trips`](models/semantic/mobility/trips.py)
读取 2025 年 12 月 Parquet，[上车和下车区域实体](models/semantic/mobility/zones.py)
读取各自角色的 Taxi Zone CSV。OD 分析可使用对应角色的行政区、Taxi Zone 和服务区维度。
导出扁平表格时，可通过 `frame.to_pandas(axis_names=...)` 为同名轴指定不同列名。

```text
yellow_trips
  ├── pickup_location_id  -> pickup_zones
  └── dropoff_location_id -> dropoff_zones
```

行程实体每行对应一条发布记录。该实体没有主键，因此依赖稳定行键的记录级操作
不可用。

受治理的核心指标覆盖：

- 需求量；
- 官方发布的完整费用组成；
- 总体记录打赏和信用卡专用打赏；
- 距离、时长、合理速度和每英里票价；
- 已知乘客数记录的平均乘客数及其覆盖率；
- 拥堵收费；
- 透明的数据质量计数和比率。

上车小时、ISO 星期、周末、Taxi Zone、borough 和 service zone 等维度，可用于
运营模式和时间模式分析。

为了便于审计，官方发布总量会保留修正类和异常记录。常用平均值和效率指标使用
有明确文档约束的 plausible-record 子集：

- pickup 时间与源文件月份一致；
- 行程时长大于 0 且不超过 24 小时；
- 行程距离在 0 至 200 英里之间；
- 推算速度不超过 100 mph；
- fare 和 total amount 非负；
- 上车和下车区域 ID 均位于官方已发布的 1–265 范围内。

## 数据来源与注意事项

- 行程记录和数据字典：
  <https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page>
- 2025 年 12 月行程文件：
  <https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-12.parquet>
- Taxi Zone：
  <https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv>

TLC 说明这些记录由授权技术服务商提供，不保证数据的准确性或完整性。本项目
有意保留不合理记录和修正类记录，以便 Marivo 的数据质量分析能够发现这些问题。
支付类型代码 `5` 和 `6` 的标签遵循 TLC 数据字典。
