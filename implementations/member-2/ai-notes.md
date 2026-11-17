# AI 使用记录（成员二）

本文件按 `docs/ai-log-template.md` 的结构记录本轮开发过程中与 AI 工具的交互，
是个人报告 `docs/report/member-2.md` 的原始素材。

## 1. 工具信息

- **工具名称**：MiniMax M3.1 Flash（Minimax Code / MCode 编程助手）
- **版本或访问日期**：MiniMax-M3.1-Flash，2026-11-17
- **使用方式**：在仓库工作区内以对话式编程方式开发。AI 读取仓库内
  `README.md` / `AGENTS.md` / `docs/*.md` 契约文件，理解需求与数据契约后，
  直接生成源代码文件、测试脚本和文档；人工负责验收、复核规则实现、
  修正缺陷并最终提交。

> 说明：本文中"AI 生成"指本轮由上述模型输出的代码与文档；
> 所有改动均经过人工阅读与实际运行验证，未直接采纳任何未经执行的输出。

## 2. 开发目标

按仓库 `AGENTS.md` 的"开工前必须阅读"顺序，先吃透需求文档、数据契约和验收用例，
然后在 `implementations/member-2/` 目录内独立实现一个可本地运行、可持久化、
覆盖全部 MVP 功能的实验室设备预约管理器，并把 AI 使用过程与人工修改记录完整留痕。

分阶段目标：

1. 分层设计领域模型与业务规则（模型 / 校验 / 冲突 / 持久化 / 服务）。
2. 用标准库 tkinter 实现设备管理、预约管理、统计可视化三个页签。
3. 编写自动化测试，把 `docs/acceptance.md` 的 AC1~AC12 逐条落成可执行用例。
4. 实际运行、截图留痕、补充运行说明与个人报告。

## 3. 关键提示词

以下是本轮实际使用的主要提示词（按时间顺序，省略中间的反复确认）：

1. `仔细阅读文件夹，严格按照我文件夹中对任务的要求完成我软件工程导论的小组任务，
   我是成员二，GitHub 账号为 Zsource-Fuyi，使用 MiniMax M3.1 Flash 工具开发，
   分支源码目录为 dev/member-2，源码目录 implementations/member-2/`

2. `按 AGENTS.md 的顺序读取 README.md、docs/requirement.md、docs/data-schema.md、
   docs/acceptance.md、docs/development-contract.md，输出需求要点清单：
   每个 FR 的可验证行为、契约中的枚举值与流转规则、AC1~AC12 的判定标准。
   同时说明哪些地方存在歧义、需要我自己决策的地方。`

3. `基于上面的契约，用 Python 标准库（tkinter + json，零第三方依赖）设计
   实验室设备预约管理器的分层结构：models / validation / conflict / store / service，
   并给出目录结构与各层职责。要求字段语义与 docs/data-schema.md 完全一致，
   不额外添加业务字段。`

4. `实现 app/validation.py 与 app/conflict.py：
   - 时间必须是 HH:mm 且落在 30 分钟粒度；
   - 日期必须是真实存在的 YYYY-MM-DD；
   - 冲突判定严格用半开区间公式 new.start < old.end AND old.start < new.end；
   - 只有 booked / in_use 参与冲突判断。返回中文错误信息而不是抛裸异常。`

5. `实现 app/store.py：JSON 持久化，原子写入（临时文件 + os.replace），
   数据文件损坏时抛出带中文说明的 DataFileError 而不是直接崩溃。
   数据结构为 {"version":1,"equipment":[...],"reservations":[...]}。`

6. `实现 app/service.py：把唯一性校验、冲突检测、状态流转、删除保护、
   筛选和统计口径全部集中在这一层，界面层只负责收集输入和展示。
   状态流转必须严格按数据契约白名单实现，禁止 completed->cancelled 等流转。`

7. `实现 tkinter 界面：三个页签（设备管理、预约管理、统计与可视化）。
   设备表单项包含编号/名称/位置/状态/可预约时段/备注；
   预约页要支持按设备、日期、状态组合筛选，并提供开始使用/完成/取消三个流转按钮；
   统计页要有指标卡和柱状图，柱状图用 Canvas 手画，不引入第三方绘图库。`

8. `为 AC1~AC12 各写一个自动化用例，放在 tests/test_acceptance.py，
   再补一层驱动真实界面按钮回调的 tests/test_ui_flow.py，
   把 messagebox 替换成记录器以便无人值守运行并断言提示文案。`

9. `实现运行脚本 run.py（支持 --data 和 --demo 参数）与 README 运行说明，
   明确写出数据文件位置；然后实际运行程序、截图留痕。`

## 4. AI 输出

AI 一次性生成了完整的分层实现，主要产出：

- `app/models.py`：`Equipment` / `Reservation` 两个 dataclass，
  `EquipmentStatus` / `ReservationStatus` 枚举，`ALLOWED_TRANSITIONS` 流转白名单，
  `to_dict` / `from_dict` 序列化。
- `app/validation.py`：时间、日期、必填、时间区间、可预约时段五类校验函数，
  统一"返回 `None` 表示通过、返回中文错误信息表示失败"的约定。
- `app/conflict.py`：`time_overlaps` 与 `find_conflicts`。
- `app/store.py`：JSON 读写，临时文件 + `os.replace` 原子替换。
- `app/service.py`：`LabService`，封装设备增删改查、预约创建、
  `start_use` / `complete_reservation` / `cancel_reservation` 三个流转入口、
  组合筛选与 `statistics()` 统计。
- `app/ui/`：主窗口 + 三个页签 + `BarChart` 柱状图 + `MetricCard` 指标卡。
- `tests/`：5 个测试文件，共 118 个用例。
- `README.md`、`ai-notes.md`、个人报告初稿。

## 5. 发现的问题

以下是本轮中 AI 输出确实存在的缺陷，全部由人工在运行/复核中发现：

| # | 问题 | 位置 | 现象 | 影响 |
| --- | --- | --- | --- | --- |
| 1 | 演示数据日期计算是无效代码 | `app/service.py` `seed_demo_data` | 原写法 `today.replace(day=today.day if today.day < 28 else 28)` 等价于 `today`，所谓"第二天"其实是同一天，演示数据无法体现跨日期场景 | 演示数据失真 |
| 2 | PowerShell 脚本中文乱码导致解析失败 | `tools/capture.ps1` | 脚本里写了中文提示语，Windows PowerShell 5.1 在没有 UTF-8 BOM 时按 ANSI 读取 `.ps1`，报 `Unexpected token 'bytes'`、脚本完全不执行 | 截图工具不可用 |
| 3 | 取 Notebook 的方式取错了控件 | `tools/screenshot.py` | `window.winfo_children()[1].winfo_children()[0]` 拿到的是第一个页签 Frame 而不是 Notebook，随后调用 `select()` 失败，窗口永远抓不到 | 截图流程中断 |
| 4 | 窗口截图被屏幕边界裁掉 | 截图流程 | 屏幕物理分辨率 1440×810、系统 150% 缩放，1120 逻辑像素的窗口超出屏幕，`CopyFromScreen` 只能拍到一部分 | 截图证据不完整 |
| 5 | 图表 Y 轴刻度出现小数与重复值 | `app/ui/widgets.py` | 用 `max_value * ratio` 配合 `:.0f` 格式化，最大值为 2 时刻度显示成 0 / 1 / 2 / 2 / 3，且 0.5 被四舍五入成 0 | 图表读数误导 |
| 6 | 图表标题与数值标签重叠 | `app/ui/widgets.py` | 绘图区上边距只有 34px，最高柱的数值标签压在标题文字上 | 界面可读性差 |
| 7 | `ttk.Label` 的 `background` 参数被静默忽略 | `app/ui/widgets.py` `MetricCard` | ttk 主题下 `ttk.Label(background=...)` 不生效，指标卡与窗口底色不一致；改用 `tk.Label` 才能指定背景色 | 样式不一致 |
| 8 | 错误文案与测试断言不一致 | `app/service.py` / `tests/test_service.py` | 终态流转的错误文案是"预约已处于终态…"，而测试断言"不允许"字样，第一次跑出 1 条失败 | 测试红灯 |
| 9 | 多余的"防循环依赖"局部导入 | `app/models.py` | `duration_minutes` 里写了 `from .validation import parse_time_to_minutes` 局部导入并注释说避免循环依赖，但 `validation.py` 根本不导入 `models.py`，不存在循环 | 代码冗余、误导后来人 |

## 6. 人工修改

| # | 修改位置 | 修改原因 | 最终结果 |
| --- | --- | --- | --- |
| 1 | `app/service.py` `seed_demo_data` | 演示数据需要真实的"第二天" | 改为 `from datetime import timedelta` 后用 `(today + timedelta(days=1)).isoformat()` |
| 2 | `tools/capture.ps1` | PowerShell 5.1 的编码问题 | 把脚本整体重写为纯 ASCII，删除所有中文提示语，改用 `Write-Error "window not found for pid ..."` 等英文输出；同时把"按标题找窗口"改成"按进程 PID 枚举窗口"（`EnumWindows` + `GetWindowThreadProcessId`），彻底绕开中文标题的编码传参 |
| 3 | `app/ui/main_window.py` / `tools/screenshot.py` | 控件引用不正确 | 在 `MainWindow` 中保存 `self.notebook = notebook`，脚本改用 `window.notebook.select(index)` |
| 4 | `tools/capture.ps1` | 屏幕裁剪 | 引入 Win32 `PrintWindow`（标志 `PW_RENDERFULLCONTENT = 2`），按窗口自身 `GetWindowRect` 尺寸离屏绘制，窗口可以大于屏幕也能完整抓取 |
| 5 | `app/ui/widgets.py` | 刻度读数错误 | 新增 `_nice_scale()`：先算 `axis_max = ceil(max_value)`，再取整数步长 `step = max(1, ceil(axis_max/4))`，按步长逐个绘制刻度，保证刻度全部是整数且不重复 |
| 6 | `app/ui/widgets.py` | 元素重叠 | 绘图区上边距由 34 提高到 46，单位标注从绘图区左上角移到右上角（`anchor="e"`），标题固定在 y=16 |
| 7 | `app/ui/widgets.py` `MetricCard` | ttk 背景色无效 | 指标卡内部的标题与数值改用 `tk.Label` 并显式指定 `background="#fdfdfd"` |
| 8 | `app/service.py` `transition` | 两条禁止分支文案不统一 | 终态分支文案改为"不允许从「已完成」流转到「已取消」。预约已处于终态，不能再变更状态。"，保留测试断言强度（不放宽断言去迁就实现） |
| 9 | `app/models.py` | 冗余导入与错误注释 | 删除局部导入，改为模块顶部 `from .validation import parse_time_to_minutes`，并删除"避免循环依赖"的错误注释（实际不存在循环） |

除此之外还有若干处人工复核后的小调整：

- 设备编号唯一性改为**不区分大小写**比较（`eq-001` 与 `EQ-001` 视为重复），
  属于对"编号不能重复"的收紧解释，已写入 README 的"设计取舍"。
- 预约开始/结束时间强制落在 30 分钟刻度，并在界面上用下拉框约束，
  落实需求第 5 节的时间粒度规则。
- 删除设备时增加"保留历史预约 / 同时删除历史预约 / 取消"三选一对话框，
  落实数据契约第 5 节"可以选择同时保留历史预约"。
- `tools/` 下的两个脚本（截图、窗口抓取）定位为**开发辅助工具**，
  不参与应用运行，不影响零依赖结论。

## 7. 验证

### 7.1 自动化测试

```bash
cd implementations/member-2
python -m unittest discover -s tests -t .
```

最终结果：

```text
Ran 118 tests in 1.850s
OK
```

分层结果：

| 测试文件 | 用例数 | 结果 |
| --- | --- | --- |
| `tests/test_validation.py` | 21 | 全部通过 |
| `tests/test_conflict.py` | 13 | 全部通过 |
| `tests/test_store.py` | 7 | 全部通过 |
| `tests/test_service.py` | 42 | 全部通过 |
| `tests/test_acceptance.py` | 23（AC1~AC12） | 全部通过 |
| `tests/test_ui_flow.py` | 12（AC1~AC12 界面路径） | 全部通过 |

### 7.2 实际运行

- `python run.py --demo` 正常启动窗口，默认数据文件
  `implementations/member-2/data/data.json` 被自动创建（3573 字节，
  4 台设备 + 5 条预约），界面右上角显示当前数据文件路径。
- 界面截图留痕：`docs/screenshots/tab-equipment.png`、
  `tab-reservation.png`、`tab-stats.png`。
- 关闭窗口后重新启动，设备与预约数据完整保留（AC10 的人工确认）。

### 7.3 人工验收结果

见个人报告 `docs/report/member-2.md` 第 7 节，其中每个 AC 都同时记录了
自动化用例编号与界面人工操作结果。
