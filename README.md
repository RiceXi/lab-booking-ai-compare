# 实验室设备预约管理器

软工导论小组作业：三名成员使用不同 AI 工具，基于同一份需求独立开发实验室设备预约管理器，随后对比开发过程与实现质量，并完成一个整合优化版本。

当前阶段：个人独立开发。

## 组员与工具分配

| 成员 | GitHub 账号 | 使用 AI 工具 | 开发分支 | 源码目录 |
| --- | --- | --- | --- | --- |
| 成员一 | RiceXi | DeepSeek-V4.1-Flash | dev/member-1 | implementations/member-1/ |
| 成员二 | Zsource-Fuyi | MiniMax M3.1 Flash | dev/member-2 | implementations/member-2/ |
| 成员三 | KingSure000 | Gemini 3.8 Flash | dev/member-3 | implementations/member-3/ |

## 项目阶段

1. 需求冻结：确认范围、数据契约和验收用例。
2. 个人独立开发：三名成员分别在自己目录中完成可运行版本。
3. 版本冻结：三份实现完成后打 tag，并合并到 main。
4. 对比分析：比较不同 AI 工具的生成质量、迭代效率和人工修改量。
5. 整合优化：选择一个基础版本，吸收其他版本优点，完成最终版本。

当前只执行第 1、2 阶段。对比报告、整合版和最终评析在个人版本冻结后再开始。

## 开工顺序

1. 阅读 [AGENTS.md](AGENTS.md)。
2. 阅读 [需求文档](docs/requirement.md)。
3. 阅读 [数据契约](docs/data-schema.md)。
4. 阅读 [验收用例](docs/acceptance.md)。
5. 只在自己对应的源码目录和个人报告中开发。

## 仓库结构

```text
.
├── README.md
├── AGENTS.md
├── CONTRIBUTING.md
├── docs/
│   ├── requirement.md
│   ├── data-schema.md
│   ├── acceptance.md
│   ├── development-contract.md
│   ├── ai-log-template.md
│   ├── report/
│   │   ├── member-1.md
│   │   ├── member-2.md
│   │   ├── member-3.md
│   │   ├── compare.md
│   │   └── evaluation.md
│   └── assets/
├── implementations/
│   ├── member-1/
│   ├── member-2/
│   └── member-3/
└── merged-release/
```

## 交付物

- 三份可独立运行的实验室设备预约管理器
- 三份个人 AI 辅助开发报告
- 小组对比讨论报告
- 一个整合优化版本
- 软件评析报告

## 协作边界

- 个人开发阶段禁止修改公共需求、数据契约和验收用例。
- 每个人只修改自己的实现目录和个人报告。
- 个人版本冻结前不得复制或参考其他成员实现。
- GitHub 用于版本隔离和过程留痕，不作为本作业的主要分析对象。

