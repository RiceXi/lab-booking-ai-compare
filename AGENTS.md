# Agent 开发说明

本仓库用于软工导论课程中的 AI 辅助软件开发对比实验。当前阶段是个人独立开发。

## 开工前必须阅读

按以下顺序阅读：

1. `README.md`
2. `docs/requirement.md`
3. `docs/data-schema.md`
4. `docs/acceptance.md`
5. `docs/development-contract.md`

## 当前阶段允许修改的范围

每个成员只能修改自己的目录和个人报告：

- 成员一：`implementations/member-1/`、`docs/report/member-1.md`
- 成员二：`implementations/member-2/`、`docs/report/member-2.md`
- 成员三：`implementations/member-3/`、`docs/report/member-3.md`

不得修改：

- `README.md`
- `AGENTS.md`
- `CONTRIBUTING.md`
- `docs/requirement.md`
- `docs/data-schema.md`
- `docs/acceptance.md`
- `docs/development-contract.md`
- 其他人的实现和报告

## 实现要求

- 软件必须能在本地独立运行。
- 数据必须保存在本地，程序重启后不能丢失。
- 必须覆盖需求文档中的 MVP 功能。
- 必须遵守数据契约中的字段语义、状态和冲突规则。
- 必须逐项执行验收用例，并在个人报告中记录结果。
- 技术栈不限，但必须在实现目录内提供运行说明。

## AI 过程记录要求

开发过程中持续记录：

- 使用的 AI 工具和访问日期
- 关键提示词
- AI 生成的错误代码或不存在的 API
- 人工修改的位置和原因
- 重要测试结果

记录可以写在实现目录的 `ai-notes.md` 中，最终整理进个人报告。

## 独立开发约束

- 不得查看或复制其他成员尚未冻结的实现。
- 不得让其他成员代替完成自己的核心实现。
- 如遇需求歧义，向项目负责人报告，不要自行修改公共契约。

## 完成标准

- 软件可以按说明启动。
- 所有 MVP 功能可操作。
- 冲突预约会被阻止。
- 数据可以持久化。
- 验收用例全部执行并有记录。
- 个人报告包含 AI 使用过程、错误分析和人工修改说明。

