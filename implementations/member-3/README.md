# 实验室设备预约管理器（成员三实现版）

本目录为 `member-3`（GitHub：`KingSure000`）基于公共需求文档 `docs/requirement.md`、数据契约 `docs/data-schema.md` 与验收用例 `docs/acceptance.md` 独立完成的实验室设备预约管理器实现。

## 1. 技术栈与运行环境

- **开发语言**：JavaScript (CommonJS 后端 + 原生 ES6+ 前端 + 原生 SVG 图表)
- **运行时版本**：Node.js `>= 18.0.0`（本地开发与验收环境为 `Node.js v24.16.0`，`npm 11.13.0`）
- **外部依赖**：**零第三方运行时依赖**（完全基于 Node.js 内置标准库 `node:http`、`node:fs`、`node:crypto`、`node:test` 与原生浏览器 API 构建，所有核心功能与可视化图表 100% 支持离线运行）

## 2. 依赖安装与启动方式

在干净环境中打开终端，进入本实现目录：

```bash
cd implementations/member-3
```

### 依赖安装
本项目无第三方运行时依赖，无需联网下载依赖即可直接运行（执行 `npm install` 亦可通过）：

```bash
npm install
```

### 启动服务

```bash
npm start
```

（等价命令：`node src/server.js`）

启动成功后，在浏览器访问：

- **默认地址**：`http://127.0.0.1:3003`
- 如需自定义端口，可设置环境变量 `PORT`（例如 PowerShell 下：`$env:PORT=4000; npm start`）

### 运行自动化验收测试（覆盖 AC1–AC12）

```bash
npm test
```

（等价命令：`node --test tests/acceptance.test.js`，测试使用系统临时目录下的独立 JSON 文件，不会覆盖或污染本地正式数据）

## 3. 本地数据文件位置

- **默认数据文件路径**：`implementations/member-3/data.json`
- 服务首次启动时若该文件不存在，会自动创建并初始化 `{ "equipments": [], "reservations": [] }`。
- 程序关闭并重新启动后，所有设备与预约记录均从该文件自动加载，不会丢失。
- 该文件名已由仓库根目录 `.gitignore` 中的 `data.json` 规则忽略，不会提交至 Git 仓库。
- 如需自定义数据文件路径，可通过 `DATA_FILE` 环境变量指定。

## 4. 目录结构说明

```text
implementations/member-3/
├── package.json             # 项目元信息与启动/测试脚本定义
├── README.md                # 独立运行说明文档
├── ai-notes.md              # AI 辅助开发全过程原始记录
├── data.json                # 运行时自动生成的本地持久化数据文件（Git 忽略）
├── src/
│   ├── errors.js            # 统一业务异常封装 AppError
│   ├── validators.js        # 日期合法性、30分钟时间粒度、状态机流转表与字段校验
│   ├── storage.js           # JSON 本地持久化读写封装（含临时文件写入与 Windows 降级保护）
│   ├── equipmentService.js  # 设备增删改查、编号全局唯一校验、有效预约删除拦截
│   ├── reservationService.js# 预约创建、半开区间冲突检测、状态流转控制、多维组合筛选
│   ├── statsService.js      # 核心统计指标计算与按设备次数/使用时长聚合
│   ├── app.js               # HTTP 路由分发与静态资源托管工厂
│   └── server.js            # 本地服务启动入口
├── public/
│   ├── index.html           # 单页应用主界面（预约管理、设备管理、统计可视化三栏工作台）
│   ├── styles.css           # 离线浅色桌面端样式表
│   ├── api.js               # 前端请求封装、30分钟时间槽生成与公共工具函数
│   ├── charts.js            # 原生 SVG 设备使用柱状图（次数/时长切换）与状态占比环形图
│   ├── render.js            # 表格、指标卡片与设备详情弹窗渲染模块
│   └── app.js               # 前端状态管理与交互事件绑定
└── tests/
    └── acceptance.test.js   # 覆盖 AC1–AC12 及状态机/持久化边界的自动化测试套件
```
