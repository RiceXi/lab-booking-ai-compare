# 个人开发分析报告：成员二

## 1. 工具与开发概述

- **GitHub**：Zsource-Fuyi
- **AI 工具**：MiniMax M3.1 Flash
- **使用方式**：
  在仓库工作区内以对话式编程方式完成开发。AI 读取仓库中的 `README.md`、`AGENTS.md`
  与 `docs/` 下的需求、数据契约、验收用例、开发契约五份公共文档，理解业务边界后，
  按"领域模型 → 校验 → 冲突检测 → 持久化 → 服务层 → 界面层 → 测试 → 文档"的顺序
  生成完整实现；人工负责阅读复核、实际运行验证、修正缺陷并提交。
  详细的提示词、问题清单与人工修改见 `implementations/member-2/ai-notes.md`。
- **分支**：`dev/member-2`　**源码目录**：`implementations/member-2/`
- **技术选型**：Python 3 + tkinter（标准库）+ JSON 文件持久化，**零第三方依赖**。
- **最终规模**：13 个源文件、5 个测试文件、118 个自动化用例，全部通过。

选型理由：需求明确要求"能在干净环境按说明启动""所有核心功能可以离线使用"。
纯标准库方案换机器、换 Python 版本都能直接 `python run.py` 跑起来，
不存在 pip 源不可达导致无法启动的风险；图表用 `tkinter.Canvas` 手绘，同样不引入依赖。
代价是界面观感不如 Web 前端精致，但对本作业"业务行为必须一致"的要求反而更稳妥。

## 2. 开发计划

| 阶段 | 内容 | 产出 | 状态 |
| --- | --- | --- | --- |
| 一、契约理解 | 按 `AGENTS.md` 顺序通读 5 份公共文档，梳理每个 FR 的可验证行为与 AC 判定标准 | 契约要点清单 | 完成 |
| 二、架构设计 | 分层设计，确定"界面只负责输入输出、规则全在服务层"的边界 | 目录结构与分层职责 | 完成 |
| 三、领域层实现 | 模型、枚举、状态流转白名单、输入校验、冲突检测、JSON 持久化 | `app/models.py`、`validation.py`、`conflict.py`、`store.py`、`errors.py` | 完成 |
| 四、服务层实现 | 设备增删改查、预约创建、状态流转、删除保护、组合筛选、统计口径 | `app/service.py` | 完成 |
| 五、界面实现 | 设备管理、预约管理、统计可视化三个页签 + 手绘柱状图 | `app/ui/` | 完成 |
| 六、测试补齐 | 单元测试 + AC1~AC12 业务层用例 + 驱动真实界面回调的用例 | `tests/`（118 例） | 完成 |
| 七、运行验证 | 实际启动程序、截图留痕、逐条核对验收用例 | `docs/screenshots/` | 完成 |
| 八、文档留痕 | 运行说明、AI 使用记录、个人报告 | `README.md`、`ai-notes.md`、本报告 | 完成 |

## 3. 关键提示词与迭代过程

### 3.1 关键提示词

完整清单见 `implementations/member-2/ai-notes.md` 第 3 节，核心几条：

1. **任务下达**
   > 仔细阅读文件夹，严格按照我文件夹中对任务的要求完成我软件工程导论的小组任务，
   > 我是成员二，GitHub 账号为 Zsource-Fuyi，使用 MiniMax M3.1 Flash 工具开发，
   > 分支源码目录为 dev/member-2，源码目录 implementations/member-2/

2. **契约消解**
   > 按 AGENTS.md 的顺序读取 README.md、docs/requirement.md、docs/data-schema.md、
   > docs/acceptance.md、docs/development-contract.md，输出需求要点清单：
   > 每个 FR 的可验证行为、契约中的枚举值与流转规则、AC1~AC12 的判定标准，
   > 并指出存在歧义、需要自己决策的地方。

3. **分层设计**
   > 基于上面的契约，用 Python 标准库（tkinter + json，零第三方依赖）设计分层结构：
   > models / validation / conflict / store / service，并给出目录结构与各层职责。
   > 字段语义与 docs/data-schema.md 完全一致，不额外添加业务字段。

4. **规则实现**
   > 时间必须是 HH:mm 且落在 30 分钟粒度；日期必须是真实存在的 YYYY-MM-DD；
   > 冲突判定严格用半开区间公式 new.start < old.end AND old.start < new.end；
   > 只有 booked / in_use 参与冲突判断。返回中文错误信息而不是抛裸异常。

5. **状态机**
   > 状态流转必须严格按数据契约白名单实现，禁止 completed->cancelled、cancelled->booked
   > 等流转，并在错误提示中说明当前状态允许流转到哪些状态。

6. **界面**
   > 三个页签（设备管理、预约管理、统计与可视化）。预约页支持按设备、日期、状态组合筛选，
   > 并提供开始使用/完成/取消三个流转按钮；统计页要有指标卡和柱状图，
   > 柱状图用 Canvas 手画，不引入第三方绘图库。

7. **验收**
   > 为 AC1~AC12 各写一个自动化用例放在 tests/test_acceptance.py，
   > 再补一层驱动真实界面按钮回调的 tests/test_ui_flow.py，
   > 把 messagebox 替换成记录器以便无人值守运行并断言提示文案。

### 3.2 迭代过程

整个开发过程是"**生成 → 运行 → 验证 → 修正**"的循环，共经历 5 轮有实质返工的迭代：

- **第 1 轮**：一次性生成领域层 + 服务层 → 立即写临时脚本跑冒烟测试，
  发现冲突检测、删除保护均按预期拦截，核心规则一次通过。
- **第 2 轮**：生成界面层 → 构造窗口成功，截图发现图表刻度重复、标题重叠，
  以及窗口在 150% 缩放的屏幕上被裁切 → 修正图表与截图方式。
- **第 3 轮**：生成测试层 → 首次运行 106 例中 **1 例失败**（错误文案与断言不一致）。
  人工判断是"实现文案分支不统一"而非"断言写错了"，因此改的是生产代码而非放宽断言。
- **第 4 轮**：补 UI 流程测试 → 12 例一次通过，并且顺带暴露了演示数据日期计算是无效代码。
- **第 5 轮**：文档与清理 → 复核时删掉 `models.py` 中多余的局部导入，
  修正 `ai-notes.md` 中两个与实测不符的用例计数（validation 26→21、service 38→42）。

## 4. AI 生成效果分析

### 4.1 做得好的地方

- **一次性产出可运行的分层骨架**：模型、校验、冲突、持久化、服务五层一次成型，
  字段命名与 `docs/data-schema.md` 逐项对应，没有出现"多一个字段、少一个字段"的对齐错误，
  这是本次最省时间的部分。
- **契约细节还原准确**：半开区间冲突公式、`ALLOWED_TRANSITIONS` 白名单、
  "只有 booked / in_use 占用时间"、原子写入、30 分钟粒度等容易被忽略的约束，
  AI 基本一次写对，且在注释里写清了来源。
- **中文错误提示可读性好**：AI 主动把 `ValidationError` / `ConflictError` / `AppError`
  分级，并让提示带上具体上下文（例如冲突提示里列出冲突预约的日期、时间段和预约人），
  这一点比英文 `raise ValueError` 对普通用户友好很多。
- **测试生成主动对齐验收用例**：把 `docs/acceptance.md` 的 AC 编号直接映射成
  `test_ac1_…`、`test_ac2_…` 这样的用例名，后续核对验收时几乎零成本。

### 4.2 表现一般的地方

- **界面代码偏"能跑就行"**：初版统计页的柱状图刻度用 `:.0f` 四舍五入，
  导致 0.5 被舍成 0、1.5 被舍成 2，出现 0/1/2/2/3 的重复刻度；
  绘图区上边距 34px 也不足以容纳标题和柱顶数值。这类"视觉正确性"需要人眼确认，
  AI 自己不会意识到。
- **辅助脚本的环境假设过强**：初版截图脚本直接按窗口标题查找窗口，
  但 Windows PowerShell 5.1 对无 BOM 的 `.ps1` 按 ANSI 读取，
  脚本里的中文提示语直接让整个脚本解析失败。AI 默认"写出来的脚本能直接跑"，
  没有考虑 Windows 特有的编码坑。
- **细节冗余**：初版 `models.py` 里写了"局部导入避免循环依赖"，
  但实际不存在循环依赖——这类注释型冗余是模型常见的"看起来很专业"的填充。

### 4.3 结论

在**规则密集、可自动验证**的部分（模型、校验、冲突、持久化、业务规则），
AI 的产出质量很高，一次生成即可用，人工改动集中在文案统一与边角；
在**依赖平台环境、视觉呈现**的部分（PowerShell 编码、DPI 缩放、图表排版），
AI 的产出需要人工逐项验证才能交付。这说明本类任务的合理分工是：
让 AI 承担"把契约翻译成结构化代码"，把人工留给"在真实环境里跑一遍并挑毛病"。

## 5. AI 错误、幻觉与人工修改

共发现并修复 **9 处** AI 输出缺陷，完整表格见 `implementations/member-2/ai-notes.md` 第 5 节，
此处列出影响较大的 5 条：

| # | 缺陷 | 人工修改 |
| --- | --- | --- |
| 1 | `seed_demo_data` 里 `today.replace(day=...)` 是无效代码，所谓"第二天"其实是同一天 | 改用 `today + timedelta(days=1)` |
| 2 | `tools/capture.ps1` 含中文提示语，PowerShell 5.1 按 ANSI 解析 `.ps1` 直接语法报错 | 脚本重写为纯 ASCII，窗口定位方式从"按中文标题查找"改为"按进程 PID 枚举"（`EnumWindows` + `GetWindowThreadProcessId`） |
| 3 | 取 Notebook 的表达式取到了第一个页签 Frame 而非 Notebook，导致 `select()` 调用失败 | `MainWindow` 暴露 `self.notebook`，脚本改用 `window.notebook.select(index)` |
| 4 | 截图被屏幕边界裁切（1440×810 物理分辨率 + 150% 缩放） | 改用 Win32 `PrintWindow` + `PW_RENDERFULLCONTENT` 离屏渲染整窗 |
| 5 | 柱状图 Y 轴刻度小数被四舍五入，出现重复刻度；标题与柱顶数值标签重叠 | 新增 `_nice_scale()` 生成整数刻度；上边距 34→46，单位标注移到右上角 |

其中第 2、3、4 条属于**环境相关问题**：AI 生成的代码在逻辑上成立，
但在没有真实运行验证的情况下会静默失败。这三条也是本次人工修改中
最花时间的部分，也直接决定了报告里"人工修改量"这一项的数值。

**关于幻觉**：本轮没有出现"编造不存在的 API"的情况——
`tkinter`/`ttk`/`Canvas`/`PrintWindow` 等 API 均真实存在且按文档使用。
出现的"看似错误"其实都是**对 API 语义理解偏差**（如把 `winfo_children()` 的返回结构想当然），
而不是 API 本身不存在。

## 6. 代码结构说明

```text
implementations/member-2/
├── run.py                  启动入口（支持 --data / --demo）
├── README.md               运行说明
├── requirements.txt        依赖清单（空）
├── ai-notes.md             AI 使用记录
├── app/
│   ├── models.py           Equipment / Reservation、状态枚举、ALLOWED_TRANSITIONS
│   ├── validation.py       时间 / 日期 / 必填 / 时间区间 / 可预约时段校验
│   ├── conflict.py         半开区间重叠判定与冲突查找
│   ├── store.py            JSON 读写（原子写入）
│   ├── service.py          LabService：全部业务规则
│   ├── errors.py           AppError / ValidationError / ConflictError / DataFileError
│   ├── paths.py            数据文件路径常量
│   └── ui/
│       ├── main_window.py  主窗口与页签装配
│       ├── equipment_tab.py    设备管理
│       ├── reservation_tab.py  预约管理 + 组合筛选 + 状态流转
│       ├── stats_tab.py        统计与可视化
│       └── widgets.py          MetricCard / BarChart / 时间选项
├── tests/                  5 个测试文件，118 个用例
├── tools/                  开发辅助脚本（截图、窗口抓取），不参与应用运行
└── docs/screenshots/       界面截图
```

**分层依据**：`docs/acceptance.md` 的每一条判定标准，要么是纯校验（→ `validation.py`），
要么是纯区间运算（→ `conflict.py`），要么是数据读写（→ `store.py`），
要么需要同时访问设备与预约两份数据（→ `service.py`）。
按这个切分，业务层可以完全脱离界面测试，界面层只剩"取值—调用—展示"三件事。
`service.py` 用监听器（`add_listener`）把数据变化广播给三个页签，
因此新增一条预约后，统计页与设备下拉框会立刻同步，不需要手动刷新。

## 7. 验收结果

### 7.1 总体结论

**AC1~AC12 全部通过。** 每条用例同时提供两种验证证据：

- **自动化用例**：业务层 `tests/test_acceptance.py`（23 例），
  界面层 `tests/test_ui_flow.py`（12 例，驱动真实按钮回调并断言弹窗文案）。
- **界面人工操作**：按文档描述在真实窗口中操作并截图留痕。

全套测试结果：

```text
Ran 118 tests in 1.850s
OK
```

### 7.2 逐条验收记录

| AC | 用例名称 | 操作步骤 | 预期结果 | 实际结果 | 结论 |
| --- | --- | --- | --- | --- | --- |
| AC1 添加设备 | `AC1AddEquipmentTests.test_ac1_equipment_appears_in_list` / `test_ac1_add_equipment_through_form` | 在"设备管理"填写编号 EQ-001、名称"高速离心机"、位置"生化楼 A-201"、可预约时段 08:00-20:00，点击"添加设备" | 保存后设备出现在列表中 | 列表出现该行，编号/名称/位置/时段均正确 | ✅ 通过 |
| AC2 重复设备编号 | `AC2DuplicateCodeTests.test_ac2_duplicate_code_is_blocked_with_message` / `test_ac2_duplicate_code_shows_message` | 再次用编号 EQ-001 添加设备 | 阻止保存并显示提示 | 弹出错误框"设备编号「EQ-001」已存在，请更换编号"，列表仍只有 1 条 | ✅ 通过 |
| AC3 创建有效预约 | `AC3CreateReservationTests.test_ac3_valid_reservation_appears_in_list` / `test_ac3_create_reservation_through_form` | 选择 EQ-001，填写预约人张三、日期 2026-11-17、时间 09:00-10:00，点击"创建预约" | 保存后预约出现在列表中 | 列表出现该条，状态为"已预约" | ✅ 通过 |
| AC4 冲突预约 | `AC4ConflictTests.test_ac4_overlapping_reservation_is_blocked` / `test_ac4_conflict_shows_message` | 同设备同日期再创建 09:30-10:30 | 阻止保存并说明冲突 | 弹出"创建失败：与已有预约时间冲突——2026-11-17 09:00-10:00（张三，已预约）……"，列表仍只有 1 条 | ✅ 通过 |
| AC5 首尾相接 | `AC5TouchingTests.test_ac5_touching_reservations_are_allowed` / `test_ac5_touching_reservations_are_allowed` | 先建 09:00-10:00，再建 10:00-11:00 | 允许保存 | 两条预约均创建成功，无错误提示 | ✅ 通过 |
| AC6 非法时间 | `AC6InvalidTimeTests.test_ac6_end_before_start_is_blocked` / `test_ac6_end_equal_start_is_blocked` / `test_ac6_invalid_time_shows_message` | 创建 11:00-09:00，再创建 09:00-09:00 | 阻止保存 | 均弹出"开始时间必须早于结束时间"，列表为空 | ✅ 通过 |
| AC7 取消预约 | `AC7CancelTests.test_ac7_cancel_changes_status_and_frees_slot` / `test_ac7_cancel_frees_slot` | 取消 09:00-10:00 的 booked 预约，再创建同一时段新预约 | 状态变为 cancelled，且不再阻止同时间段新预约 | 状态显示"已取消"；同一时段重新预约成功，列表 2 条 | ✅ 通过 |
| AC8 筛选 | `AC8FilterTests`（4 例） / `test_ac8_filters` | 分别按设备 EQ-001、按日期 2026-11-18、按状态"已取消"筛选，并组合筛选 | 结果符合筛选条件 | 各条件结果数量与内容均正确；组合筛选（设备+日期+状态）命中唯一记录 | ✅ 通过 |
| AC9 删除设备 | `AC9DeleteEquipmentTests`（3 例） / `test_ac9_delete_blocked_then_allowed` | 删除有有效预约的设备；再取消/完成预约后删除 | 有有效预约时阻止，之后允许 | 第一次弹出"设备「EQ-001 高速离心机」仍有 1 条有效预约……请先取消或完成这些预约"；取消后删除成功 | ✅ 通过 |
| AC10 持久化 | `AC10PersistenceTests`（2 例） / `test_ac10_statistics_survive_restart` | 添加设备与预约后关闭程序，重新启动 | 数据仍然存在 | 新建服务实例从同一 JSON 文件读回，设备 1 条、预约 1 条，ID 与名称一致；界面统计页同步显示 | ✅ 通过 |
| AC11 统计 | `AC11StatisticsTests`（2 例） / `test_ac11_statistics_cards` | 准备 3 台设备与多条预约（含 1 条已取消） | 设备数、有效预约数、取消数正确 | 指标卡显示：设备总数 3、有效预约数 1、已取消预约数 1，与数据一致；按设备柱状图与明细表同步 | ✅ 通过 |
| AC12 设备不可用 | `AC12UnavailableEquipmentTests`（3 例） / `test_ac12_unavailable_equipment_shows_message` | 对维护中 / 已停用设备创建预约 | 禁止创建 | 分别弹出"设备「EQ-003…」当前状态为「维护中」，不可创建新预约"和"「已停用」"，列表为空 | ✅ 通过 |

### 7.3 界面截图

| 页签 | 截图 |
| --- | --- |
| 设备管理 | `implementations/member-2/docs/screenshots/tab-equipment.png` |
| 预约管理 | `implementations/member-2/docs/screenshots/tab-reservation.png` |
| 统计与可视化 | `implementations/member-2/docs/screenshots/tab-stats.png` |

### 7.4 需求覆盖自查

| 需求 | 覆盖情况 |
| --- | --- |
| FR1 设备管理 | ✅ 添加、编辑、列表、详情、删除、编号唯一 |
| FR2 预约管理 | ✅ 创建、列表、取消，预约人非空、开始早于结束 |
| FR3 冲突检测 | ✅ 重叠禁止、首尾相接允许、已取消不占用、提示明确 |
| FR4 查询与筛选 | ✅ 设备 / 日期 / 状态，可组合 |
| FR5 状态管理 | ✅ 四种状态 + 严格按契约的流转白名单 |
| FR6 统计与可视化 | ✅ 设备总数、有效预约数、取消数、按设备次数与时长统计、柱状图 ×2 |
| FR7 本地持久化 | ✅ JSON 文件，路径已在 README 与界面标题栏注明 |
| FR8 输入校验 | ✅ 必填、编号唯一、日期合法、时间格式、开始早于结束、冲突拦截、删除保护 |

### 7.5 独立性与协作边界自查

- 仅修改了 `implementations/member-2/` 与 `docs/report/member-2.md` 两个允许范围内的路径，
  公共文档（`README.md`、`AGENTS.md`、`CONTRIBUTING.md`、`docs/requirement.md`、
  `docs/data-schema.md`、`docs/acceptance.md`、`docs/development-contract.md`）未做任何改动。
- 开发期间未查看、未参考成员一与成员三的实现。
- 未修改公共契约来迁就本实现：所有对契约的收紧解释（编号唯一不区分大小写、
  预约时间 30 分钟粒度）都只作用于本实现内部，并在 README 与本报告中显式说明。

## 8. 自我评价

### 8.1 做得好的地方

- **契约先行**：开工先把五份公共文档读完并提炼出可验证的行为清单，
  后续编码基本没有出现"实现和文档对不上"的返工。
- **规则与界面分离**：把冲突判定、状态机、删除保护这些"容易写散"的逻辑集中在
  `service.py`，让它们可以被纯逻辑测试覆盖，这是本实现质量最高的部分。
- **验证到位**：不仅写了单元测试，还专门补了一层**驱动真实界面回调**的用例，
  并把 `messagebox` 换成记录器来断言提示文案——这样"冲突时是否给用户明确提示"
  这类验收要求才真正被验证过，而不是只验证了后台逻辑。
- **过程留痕完整**：AI 的每处缺陷都定位到了文件与行、记录了成因与修复方式，
  可供后续对比分析直接使用。

### 8.2 不足与改进方向

- **界面美观度一般**。tkinter + vista 主题是"能用"级别，
  与 Web 技术栈相比在视觉呈现上明显吃亏。如果重来一次，
  会在满足"零依赖"的前提下额外考虑打包成单文件 exe 方便非技术同学使用。
- **人工验证偏晚**。图表刻度重叠、演示数据日期失效等问题，
  如果在第一轮生成后就立即截图人工核对，可以更早发现，
  实际这两处是在补截图时才暴露的。
- **辅助脚本考虑不周**。三条截图相关的返工都源于对 Windows 环境的假设过强
  （编码、DPI、窗口层级），说明在生成平台相关代码时应主动说明假设与前提。
- **缺少边界测试的深度**。目前对极端输入（如跨月跨年日期、闰年 2 月 29 日、
  恰好 24:00 的结束时间）覆盖不足，后续可补充属性测试。

### 8.3 AI 工具适用性结论

就本作业而言，MiniMax M3.1 Flash 在**规则明确的分层实现**上表现很好，
可以显著缩短"把契约翻译成代码"的时间；
但在**平台相关代码**和**需要人眼确认的呈现效果**上必须人工把关，
且不能省掉"实际跑一遍"这一步。结论是：
AI 适合承担实现的初稿与测试用例的铺开，人工应当把精力集中在
需求解释、规则边界与真实环境验证这三件事上。

## 9. 运行说明

完整说明见 `implementations/member-2/README.md`，摘要如下：

### 9.1 环境要求

- Python 3.8+，系统自带 tkinter（Windows 版 Python 自带；
  Debian/Ubuntu 需 `sudo apt install python3-tk`）
- **无需安装任何第三方依赖**（`requirements.txt` 为空）

### 9.2 启动

```bash
cd implementations/member-2
python run.py            # 正常启动
python run.py --demo     # 数据文件为空时写入演示数据
python run.py --data D:/tmp/my-data.json   # 指定数据文件
```

### 9.3 数据文件位置

```text
implementations/member-2/data/data.json
```

- 首次保存时自动创建 `data/` 目录
- 该目录已被 `.gitignore` 忽略，不会提交到 Git
- 界面右上角实时显示当前数据文件路径
- 写入采用"临时文件 + 原子替换"，异常中断不会写出半截文件

### 9.4 运行测试

```bash
cd implementations/member-2
python -m unittest discover -s tests -t .
```

预期输出 `Ran 118 tests ... OK`。
