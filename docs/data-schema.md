# 数据契约

本文件定义三个实现共同遵守的业务字段和规则。实现可以使用 JSON 或 SQLite，但字段语义必须一致。

## 1. 设备 Equipment

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | string | 是 | 系统生成的唯一标识 |
| code | string | 是 | 设备编号，全局唯一 |
| name | string | 是 | 设备名称 |
| location | string | 是 | 存放位置 |
| status | enum | 是 | available、maintenance、retired |
| opening_start | string | 是 | 每日可预约开始时间，HH:mm |
| opening_end | string | 是 | 每日可预约结束时间，HH:mm |
| notes | string | 否 | 备注 |
| created_at | string | 是 | ISO 8601 时间 |
| updated_at | string | 是 | ISO 8601 时间 |

设备状态：

- `available`：可预约
- `maintenance`：维护中，不可新建预约
- `retired`：已停用，不可新建预约

## 2. 预约 Reservation

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | string | 是 | 系统生成的唯一标识 |
| equipment_id | string | 是 | 对应设备 id |
| requester | string | 是 | 预约人姓名或学号 |
| date | string | 是 | 预约日期，YYYY-MM-DD |
| start_time | string | 是 | 开始时间，HH:mm |
| end_time | string | 是 | 结束时间，HH:mm |
| status | enum | 是 | booked、in_use、completed、cancelled |
| notes | string | 否 | 备注 |
| created_at | string | 是 | ISO 8601 时间 |
| updated_at | string | 是 | ISO 8601 时间 |

预约状态：

- `booked`：已预约
- `in_use`：使用中
- `completed`：已完成
- `cancelled`：已取消

## 3. 状态流转

允许：

- `booked -> in_use`
- `booked -> cancelled`
- `in_use -> completed`

禁止：

- `completed -> in_use`
- `cancelled -> booked`
- `completed -> cancelled`

## 4. 时间与冲突规则

- 日期使用本地日期，不处理跨天预约。
- 时间粒度为 30 分钟。
- 开始时间必须早于结束时间。
- 时间区间使用半开区间 `[start_time, end_time)`。
- 两个预约冲突的条件：

```text
new.start_time < old.end_time AND old.start_time < new.end_time
```

- 只与状态为 `booked` 或 `in_use` 的预约进行冲突判断。
- 已取消和已完成的预约不参与冲突判断。
- 预约时间必须落在设备的 `opening_start` 和 `opening_end` 之间。
- 设备状态不是 `available` 时不能创建新预约。

## 5. 删除规则

- 设备存在状态为 `booked` 或 `in_use` 的预约时，不允许删除。
- 设备没有有效预约时允许删除。
- 删除设备时，可以选择同时保留历史预约，但历史预约不能影响后续预约冲突。

## 6. 数据文件

- JSON 实现建议使用 `data.json`。
- SQLite 实现建议使用 `data.sqlite`。
- 数据文件不能提交到 Git。
- 运行说明中必须写明实际数据文件位置。

