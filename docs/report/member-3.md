# 个人开发分析报告：成员三

## 1. 工具与开发概述

- GitHub：KingSure000
- AI 工具：Gemini 3.8 Flash
- 使用方式：WorkBuddy AI 桌面端 Agent 协作模式（2026-11-15 访问使用），基于项目公共文档完成需求契约解析、零外部依赖全栈代码生成、原生离线可视化构建与自动化验收测试验证。

## 2. 开发计划

围绕 `AGENTS.md` 与 `docs/development-contract.md` 的完成标准，将独立开发拆分为五个阶段：

1. **规范审读与环境确认**：按序研读 `README.md`、`requirement.md`、`data-schema.md`、`acceptance.md` 与 `development-contract.md`，切换至 `dev/member-3` 分支，确认本机 D 盘 `Node.js v24.16.0` 与 `Git 2.54` 可直接使用。
2. **契约建模与后端实现**：构建 JSON 本地持久化层（`data.json`）、严格参数校验层、设备管理服务、30 分钟半开区间冲突检测预约服务、状态机流转控制及统计聚合接口。
3. **离线前端与可视化开发**：实现零外部 CDN 依赖的单页 Web 界面，涵盖预约创建与当日占用实时预览、设备/日期/状态多条件组合筛选、设备台账与详情弹窗，以及原生 SVG 柱状图与环形占比图。
4. **全量验收测试（AC1–AC12）**：基于内置 `node:test` 编写端到端 HTTP 验收套件，完整验证 12 项核心用例、非法状态流转拦截与真实重启持久化。
5. **过程复盘与规范提交**：整理运行说明、`ai-notes.md` 与本报告，核查修改边界仅限 `member-3` 专属路径后提交至 `dev/member-3` 分支。

## 3. 关键提示词与迭代过程

| 轮次 | 阶段目标 | 关键提示词摘要 | 迭代产出 |
| --- | --- | --- | --- |
| 第 1 轮 | 需求对齐与环境初始化 | 阅读仓库全部规范文档，作为 `member3` (`KingSure000`) 在不触碰公共契约与其他成员代码的前提下规划技术方案并检查本地环境。 | 明确 `dev/member-3` 边界，识别本机 `Node.js v24.16.0`，确定零第三方依赖 Node 标准库全栈架构。 |
| 第 2 轮 | 后端业务与数据契约落地 | 严格按照 `docs/data-schema.md` 字段名、状态枚举、`[start_time, end_time)` 冲突公式与删除规则实现后端模块与本地 `data.json` 存储。 | 生成 `src/` 下核心服务模块，支持 HTTP REST API 与静态资源托管。 |
| 第 3 轮 | 离线 Web 界面与 SVG 图表 | 构建无外部 CDN 依赖的前端工作台，支持 30 分钟粒度选时、多条件筛选、状态流转按钮及双图表可视化，确保 AC6/AC12 可直接在界面验证。 | 模块化生成 `public/` 下 `index.html`、`styles.css`、`api.js`、`charts.js`、`render.js`、`app.js`。 |
| 第 4 轮 | 自动化验收与重启验证 | 编写覆盖 AC1–AC12、非法日期/时间粒度、禁止状态流转及跨服务重启持久化的自动化测试并逐项执行。 | 产出 `tests/acceptance.test.js`，12 项测试一次通过。 |

## 4. AI 生成效果分析

- **契约遵循度高**：AI 对半开区间 `new.start_time < old.end_time AND old.start_time < new.end_time`、仅对 `booked`/`in_use` 判重、以及 `booked -> in_use -> completed` / `booked -> cancelled` 单向状态机规则理解准确，一次生成即与数据契约字段完全吻合。
- **离线架构设计合理**：针对非功能需求“所有核心功能可以离线使用”与“能从干净环境按说明启动”，未引入外部 Chart.js CDN 或需要本地 C++ 编译链的 `better-sqlite3`，而是采用 Node.js 内置模块 + 原生 SVG 矢量图（柱状图支持次数/时长双维度切换，辅以状态占比环形图），做到了克隆即跑、断网可用。
- **测试闭环效率突出**：借助内置 `node:test` 自动拉起真实 HTTP 服务并在临时目录验证跨实例重启，大幅缩短了回归验证耗时。

## 5. AI 错误、幻觉与人工修改

开发过程中未出现虚构不存在 API 的幻觉，但暴露了若干典型工程边界与平台差异问题，均进行了针对性修正：

1. **Windows 系统代理与伪 Python 环境识别**：首次克隆仓库触发 `schannel: server closed abruptly`，排查注册表后为仓库级 Git 配置本地代理 `127.0.0.1:7897` 解决；同时发现系统 PATH 中的 `python.exe` 为 `0.0.0.0` 微软商店占位符，及时切换至 D 盘已装妥的 `Node.js v24.16.0`。
2. **JS 日期自动进位缺陷防护**：JavaScript 原生 `new Date('2026-02-31')` 会静默进位为 `3月3日`。在 `src/validators.js` 的 `validateDateString` 中加入 `Date.UTC` 年月日反向校验，确保非法日历日期返回 `400 INVALID_DATE`。
3. **Windows 文件原子替换锁降级**：`src/storage.js` 使用临时文件 `fs.renameSync` 原子落盘时，针对 Windows 文件索引偶发句柄占用可能导致 `EPERM` 的风险，补充了清理临时文件并降级 `fs.writeFileSync` 的容错分支。
4. **前端模块化拆分与验收可测性调整**：首次生成大体积单文件前端脚本时触发传输超时，重构拆分为 `api.js`、`charts.js`、`render.js`、`app.js` 四个高内聚模块；同时保留下拉框中 `maintenance`/`retired` 设备选项（附不可预约标记）与独立起止时间选择，方便验收时在 UI 上直观触发并验证 AC6 与 AC12 的拦截提示。

## 6. 代码结构说明

- `implementations/member-3/src/validators.js`：统一维护字段非空、真实日历日期、`HH:mm` 30 分钟粒度及状态机流转白名单。
- `implementations/member-3/src/storage.js`：负责 `implementations/member-3/data.json` 的自动初始化与安全持久化读写。
- `implementations/member-3/src/equipmentService.js`：负责设备增删改查、编号唯一性校验（AC2）与有效预约删除保护（AC9）。
- `implementations/member-3/src/reservationService.js`：负责预约创建、设备可用性与开放时段校验（AC12）、半开区间冲突检测（AC4/AC5）、状态流转（AC7）与多条件组合筛选（AC8）。
- `implementations/member-3/src/statsService.js`：统计设备总数、进行中有效预约数、已完成数、已取消数及每台设备的预约次数与累计时长（AC11）。
- `implementations/member-3/public/`：零外部依赖前端界面与双原生 SVG 可视化图表组件。
- `implementations/member-3/tests/acceptance.test.js`：全自动端到端验收测试脚本。

## 7. 验收结果

基于 `D:\node.exe --test tests/acceptance.test.js` 实测执行，全部 12 项核心验收用例结果如下：

| 用例编号 | 测试场景与输入摘要 | 预期结果 | 实际运行结果 | 结论 |
| --- | --- | --- | --- | --- |
| AC1 | 添加设备 `EQ-SEM-01`（扫描电子显微镜，08:00-20:00） | 保存成功并出现在设备列表中 | 返回 `201`，列表查询包含该设备及完整契约字段 | 通过 |
| AC2 | 再次添加编号同为 `EQ-SEM-01` 的设备 | 阻止保存并提示编号重复 | 返回 `409 DUPLICATE_EQUIPMENT_CODE`，提示“设备编号已存在，不能重复” | 通过 |
| AC3 | 为 `EQ-SEM-01` 创建 `2026-11-16 09:00-10:00` 预约 | 保存成功，初始状态为 `booked` | 返回 `201`，预约列表准确显示该记录 | 通过 |
| AC4 | 为同设备同日创建 `09:30-10:30` 重叠预约 | 阻止保存并说明时间冲突 | 返回 `409 RESERVATION_CONFLICT`，明确提示冲突时段与原预约人 | 通过 |
| AC5 | 为同设备同日创建 `10:00-11:00` 首尾相接预约 | 半开区间不冲突，允许保存 | 返回 `201`，两条相邻预约并存 | 通过 |
| AC6 | 创建 `11:00-11:00`、`14:00-13:00`、`14:15` 非法粒度及 `2026-02-31` | 全部阻止保存并提示原因 | 均返回 `400`，准确提示起止时间顺序、30分钟粒度及日期非法 | 通过 |
| AC7 | 取消原 `09:00-10:00` 预约后，重新预约同一时段 | 状态变为 `cancelled`，新预约成功 | 取消成功且禁止逆向改回 `booked`；同时间段再次预约返回 `201` | 通过 |
| AC8 | 组合按设备 ID + 日期 `2026-11-16` + 状态 `booked` 筛选 | 仅返回同时满足三项条件的预约 | 精准返回该设备当日 2 条 `booked` 记录，排除已取消与他日记录 | 通过 |
| AC9 | 删除含有效预约的设备；流转至 `completed` 后再次删除 | 有有效预约时阻止，完成后允许删除 | 首次返回 `409` 阻止删除；完成预约后再次删除返回 `200` | 通过 |
| AC10 | 关闭 HTTP 服务实例并在原 `data.json` 上重启新实例 | 设备和预约数据完整保留 | 重启后设备数、各状态预约记录与重启前 100% 一致 | 通过 |
| AC11 | 准备 3 台设备与多条不同状态预约后核对统计与图表 | 设备数、有效预约数、取消数完全正确 | 统计接口与界面卡片准确显示 3 台设备、3 条有效预约、1 条已取消 | 通过 |
| AC12 | 分别为 `maintenance` 与 `retired` 状态设备创建新预约 | 系统阻止创建并提示设备不可用 | 均返回 `409 EQUIPMENT_UNAVAILABLE` 并指明当前不可预约状态 | 通过 |

## 8. 自我评价

- **优点**：严格遵循公共数据契约与协作目录边界；零外部依赖架构确保在任何装有 Node.js 的机器上无需联网装包即可一键启动与复现验收；前后端双重校验严密，兼顾了日常易用性（当日占用时段胶囊预览、双图表可视化）与验收可测性。
- **可改进方向**：当前面向单机单用户场景使用 JSON 全量读写完全满足毫秒级响应，若未来整合版扩展至上万级历史预约规模，可在存储接口保持不变的前提下替换为 SQLite 索引存储，并增加时间轴拖拽选时交互。

## 9. 运行说明

- **语言与运行时**：JavaScript，Node.js `>= 18.0.0`（实测版本 `Node.js v24.16.0`）
- **依赖安装**：无第三方依赖，进入 `implementations/member-3` 目录即可直接运行（执行 `npm install` 亦可）
- **启动命令**：
  ```bash
  cd implementations/member-3
  npm start
  ```
  启动后浏览器打开 `http://127.0.0.1:3003` 即可离线使用全部功能。
- **自动化验收测试命令**：
  ```bash
  cd implementations/member-3
  npm test
  ```
- **数据文件位置**：`implementations/member-3/data.json`（首次运行自动生成，已配置 `.gitignore` 忽略，不提交至 Git）。
