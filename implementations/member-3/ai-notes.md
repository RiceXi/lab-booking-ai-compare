# AI 使用记录（成员三 KingSure000）

## 工具信息

- 工具名称：Gemini–4–Carbon（通过 WorkBuddy AI 桌面端驱动）
- 版本或访问日期：2026-11-15
- 使用方式：本地工作空间 Agent 对话协作模式（需求契约审读 → 架构规划 → 模块化生成 → 自动化验收测试驱动迭代）

## 第 1 轮：仓库规范审读、环境探测与技术选型

### 开发目标
拉取课程仓库，严格确认成员三允许修改的文件边界、数据契约规则及本地可用运行时环境。

### 关键提示词
> 我要完成一份软件工程课程的大作业，需要完全用 AI 做一个软件，项目网址为 `https://github.com/RiceXi/lab-booking-ai-compare`，其中我是 `member3`（GitHub 账户名 `KingSure000`）。仔细阅读项目中的相关文件，严格按照项目中文件要求的标准来做，本地操作空间为软件工程文件夹。

### AI 输出
- 按 `AGENTS.md` 规定顺序完整读取 `README.md`、`docs/requirement.md`、`docs/data-schema.md`、`docs/acceptance.md`、`docs/development-contract.md`。
- 确认修改范围仅限 `implementations/member-3/` 与 `docs/report/member-3.md`，工作分支为 `dev/member-3`，严禁查看其他成员分支代码。
- 检查本机 Windows 真实环境变量，确认 D 盘已安装 `Git 2.54` 与 `Node.js v24.16.0`。

### 发现的问题与人工/工程调整
1. **Git 克隆 TLS 连接中断**：首次执行 `git clone` 报错 `schannel: server closed abruptly (missing close_notify)`。排查本机 Windows 注册表发现系统代理开启于 `127.0.0.1:7897`，而 Git 未配置代理。仅在当前仓库 `.git/config` 内设置 `http.proxy` / `https.proxy` 后顺利拉取。
2. **伪装的 Python 可执行文件识别**：系统 `PATH` 中虽存在 `python.exe`，但检查版本为 `0.0.0.0`（实为 `WindowsApps` 微软商店引导占位符，并非真实 Python 环境）。结合 D 盘已有 `Node.js v24.16.0`，最终选定**零第三方依赖的 Node.js 标准库方案**，既无需额外安装软件，又彻底规避了 Windows 下 `sqlite3`/`better-sqlite3` 缺少 C++ 编译链导致 `node-gyp` 安装失败的常见问题。

## 第 2 轮：数据契约建模与后端核心服务实现

### 开发目标
严格对齐 `docs/data-schema.md` 实现 `Equipment`、`Reservation` 字段校验、30 分钟时间粒度、半开区间冲突检测、状态流转机与 JSON 持久化。

### 关键提示词
> 在 `implementations/member-3/src/` 下实现存储层、输入校验器、设备管理、预约冲突检测、状态机流转和统计聚合接口，确保完全遵守 `docs/data-schema.md` 中的字段名、枚举值和 `[start_time, end_time)` 冲突公式，处理好非法日历日期与 Windows 文件写入锁问题。

### AI 输出
生成了 `errors.js`、`validators.js`、`storage.js`、`equipmentService.js`、`reservationService.js`、`statsService.js`、`app.js`、`server.js`。

### 发现的问题与修正
1. **JavaScript `Date` 自动进位陷阱**：常规 `new Date('2026-02-31')` 在 JS 中不会报错，而是静默进位为 `2026-03-03`，违反 `FR8 日期必须合法`。在 `validators.js` 中改为正则提取年月日后构造 `Date.UTC(y, m - 1, d)` 并反向比对 `getUTCFullYear/Month/Date`，精准拦截不存在的日历日期。
2. **Windows 原子重命名句柄占用风险**：`storage.js` 采用“先写 `.tmp` 临时文件再 `fs.renameSync`”保证持久化原子性，但在 Windows 下若文件被索引服务短暂占用可能抛出 `EPERM`。为此补充了 `catch` 清理临时文件并降级 `fs.writeFileSync` 覆写的双保险逻辑。
3. **有效预约统计口径对齐**：核对契约第 5 节与 AC9，“有效预约”定义为 `booked` 或 `in_use`。为避免统计展示产生歧义，`statsService.js` 同时输出 `active_reservations`（进行中有效预约）、`completed_reservations`（已完成）、`non_cancelled_reservations`（非取消累计）和 `cancelled_reservations`（已取消）。

## 第 3 轮：离线 Web 前端、原生 SVG 可视化与可测性优化

### 开发目标
实现完全离线可用的单页管理界面，覆盖设备 CRUD、预约创建、冲突告警、组合筛选及可视化图表。

### 关键提示词
> 构建离线可用的前端界面（不依赖任何外部 CDN），包含预约创建与多维筛选、设备台账与详情弹窗、以及原生 SVG 柱状图和状态占比环形图；确保所有验收用例（特别是 AC6 非法时间和 AC12 不可用设备）都能直接在前端界面操作并验证拦截提示。

### 发现的问题与修正
1. **单文件生成过大触发网络超时**：最初尝试将全部前端逻辑写入单个大体积 `app.js` 时发生流式响应超时。随后按职责重构拆分为 `api.js`、`charts.js`、`render.js`、`app.js` 四个独立模块，结构更清晰且消除了生成超时。
2. **UI 过度防呆影响验收测试可操作性**：若前端在下拉框中直接隐藏 `maintenance`/`retired` 设备，或自动改写结束时间使其永远大于开始时间，会导致测试人员无法在界面直观演示 AC6 与 AC12 的错误拦截提示。修正后保留所有设备选项（标注 `[维护中 - 禁止新预约]`）并允许独立选择起止时间，提交时在表单顶部与全局横幅醒目展示后端返回的业务拦截原因。

## 第 4 轮：AC1–AC12 全量自动化测试与重启持久化验证

### 验证结果
使用 `D:\node.exe --test tests/acceptance.test.js` 执行自动化验收套件，12 个子测试项（覆盖 AC1–AC12、非法状态流转拦截、跨实例重启持久化）全部一次通过（Pass 12 / Fail 0，耗时 290ms），静态资源与健康检查接口均返回 HTTP 200，`git check-ignore` 确认 `data.json` 被正确忽略。

## 第 5 轮：真实本地终端（CMD / PowerShell）启动复测与运行文档修正

### 发现的问题
人工在本机 Windows 终端按初版运行说明实测启动时，暴露出两处 AI 初版通用 Bash 风格说明未覆盖的 Windows 终端兼容性细节：
1. **Windows CMD 跨盘符切换失效与行内注释差异**：在默认 `C:\Users\...>` 提示符下执行不带 `/d` 的 `cd "E:\..."` 不会切换当前工作盘符，导致执行 `npm start` 时报 `ENOENT: Could not read C:\Users\...\package.json`；同时 CMD 不将 `#` 识别为行尾注释。
2. **Windows PowerShell 默认执行策略拦截 `npm.ps1`**：在未修改 `ExecutionPolicy` 的全新 Windows PowerShell 中直接敲 `npm start` 会触发 `PSSecurityException（禁止运行脚本 D:\npm.ps1）`。
3. **重复启动端口冲突提示可读性不足**：若前序服务仍在监听 `3003` 端口，再次启动会直接抛出原生 Node `EADDRINUSE` 堆栈。

### 人工与工程修改
- 修改 `implementations/member-3/src/server.js`：增加 `server.on('error')` 捕获 `EADDRINUSE`，输出清晰的中文提示说明端口已占用及访问地址。
- 修改 `implementations/member-3/README.md` 与 `docs/report/member-3.md`：按 **Windows CMD（强调 `cd /d` 且不带 `#` 注释）**、**Windows PowerShell（给出免改策略的 `npm.cmd start` / `node src/server.js` 方案）** 与 **Git Bash / macOS / Linux** 分环境细化启动步骤，确保任何评测环境按文档均可一次启动成功。
