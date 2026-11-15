# 实验室设备预约管理器（成员一）

一个完全离线运行的实验室设备预约管理器。后端使用 Python 标准库，前端使用原生 HTML/CSS/JavaScript，数据保存在 SQLite 中，不需要安装第三方 Python 或前端依赖。

## 运行环境

- Windows 10/11、macOS 或 Linux
- Python 3.10 或更高版本
- 浏览器：Chrome、Edge、Firefox 等现代浏览器

当前验收环境：Python 3.14.5、Node.js 24.16.0（Node.js 只用于 JavaScript 语法检查，不是运行依赖）。

## 启动

在仓库根目录执行：

```powershell
cd implementations/member-1
python server.py
```

程序默认在 <http://127.0.0.1:8000> 启动并打开浏览器。若该端口已被占用，可以指定其他端口：

```powershell
python server.py --port 8080
```

不希望自动打开浏览器时：

```powershell
python server.py --no-browser
```

停止服务：在启动终端按 `Ctrl+C`。

## 数据位置

默认数据文件：

```text
implementations/member-1/data/lab_booking.sqlite
```

`data/` 目录会在首次启动时自动创建，数据库文件不会提交到 Git。备份时先停止程序，再复制 `lab_booking.sqlite`。

也可以使用 `--db` 或环境变量 `LAB_BOOKING_DB` 指定数据文件：

```powershell
python server.py --db D:\lab-data\booking.sqlite
```

## 已实现功能

- 设备新增、编辑、查看、删除
- 设备编号唯一性校验、设备状态与每日开放时段维护
- 预约创建、列表查询、设备/日期/状态组合筛选
- 30 分钟粒度、单日预约和半开区间冲突检测
- `booked -> in_use -> completed`、`booked -> cancelled` 状态流转
- 取消预约后释放冲突时段
- 阻止删除仍有 `booked` 或 `in_use` 预约的设备
- 设备总数、有效预约数、已完成数、已取消数统计
- 按设备的未取消预约次数柱状图
- SQLite 本地持久化
- 桌面与手机响应式界面
- 前端使用本地打包的 Lucide 图标子集，无外部 CDN 依赖

时间规则遵循 `docs/data-schema.md`：

- 时间区间为 `[开始时间, 结束时间)`，首尾相接不冲突。
- 仅 `booked`、`in_use` 参与冲突判断。
- `completed` 和 `cancelled` 不会阻止新预约。
- 设备不是 `available` 时不能创建预约。

## 数据说明

删除没有有效预约的设备时，该设备下已完成或已取消的历史预约会随设备一起删除。这是数据契约允许的两种历史处理方式之一，界面确认框会明确提示。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| GET | `/api/equipment` | 设备列表 |
| POST | `/api/equipment` | 添加设备 |
| GET | `/api/equipment/{id}` | 设备详情 |
| PUT | `/api/equipment/{id}` | 编辑设备 |
| DELETE | `/api/equipment/{id}` | 删除设备 |
| GET | `/api/reservations` | 预约列表，支持 `equipment_id`、`date`、`status` |
| POST | `/api/reservations` | 创建预约 |
| PATCH | `/api/reservations/{id}/status` | 更新预约状态 |
| GET | `/api/stats` | 统计与设备分布 |

## 测试

运行全部自动化测试：

```powershell
python -m unittest discover -s tests -v
```

其中 `tests/test_acceptance.py` 与 `docs/acceptance.md` 的 AC1-AC12 一一对应；`tests/test_api.py` 验证 HTTP 接口、静态页面、错误状态码和冲突返回。

仅运行验收测试：

```powershell
python -m unittest tests.test_acceptance -v
```

Python 与 JavaScript 静态检查：

```powershell
python -m py_compile booking.py server.py tests/test_acceptance.py tests/test_api.py
node --check static/app.js
node --check static/icons.js
```

## 代码结构

```text
implementations/member-1/
├── booking.py                 # 数据契约、校验、状态机和 SQLite 持久化
├── server.py                  # 标准库 HTTP 服务和 JSON API
├── static/
│   ├── index.html             # 工作台、设备、预约三个工作区
│   ├── styles.css             # 桌面与移动端响应式样式
│   ├── app.js                 # 页面交互、表单和 API 调用
│   └── icons.js               # Lucide 图标子集（ISC License）
├── tests/
│   ├── test_acceptance.py     # AC1-AC12
│   └── test_api.py            # HTTP 集成测试
├── ai-notes.md                # AI 开发过程记录
└── data/                      # 运行时 SQLite 数据，不提交 Git
```

## 已知边界

- 不支持跨天预约、登录、审批、通知或云端同步，与需求范围一致。
- 单机单用户使用；若由多个进程同时写入同一个数据库，依赖 SQLite 的文件锁能力。
- 设备开放时段修改后不会自动调整已有预约；当前契约没有定义该迁移行为。
