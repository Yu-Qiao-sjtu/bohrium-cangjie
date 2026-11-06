---
name: bohrium-cangjie
description: "把书籍、论文、长视频、播客或课程蒸馏成玻尔科学空间可加载的技能。用户要求蒸馏成玻尔 skill、把仓颉产物适配到 .bohrium/skills、或把 Wisp 技能 frontmatter 改成玻尔格式时使用。不用于单纯摘要、书评，也不把产物装进 Wisp 技能目录。"
---

# 玻尔仓颉

用 Wisp Cangjie 的六阶段蒸馏，把交付物收成玻尔科学空间 `0.10.17` 能扫描的技能目录。提取、验证、能力卡和压力测试仍按已安装的 `wisp-cangjie` 执行。本技能只改编译之后的格式和安装位置。

## 何时使用

用户要「蒸馏成玻尔 skill」「适配到玻尔」「装进 .bohrium/skills」，或已经有仓颉 `dist/` 产物、需要改成桌面端格式。

## 交付契约

每个可发现技能是 `<技能根>/<name>/SKILL.md`。

- frontmatter 只有 `name` 和 `description`。
- `name` 全小写 kebab-case，短于 64 字符，并且等于目录名。
- `description` 是一行双引号标量，不超过 1024 字符，不含 `<` `>`。触发词放在前 500 字，目录预览在这里截断。
- 文件是无 BOM 的 UTF-8。
- 不写 `tags`、`wisp`、`metadata`、`license`，也不写 `disableModelInvocation`、`modelInvocable`、`userInvocable`。
- 正文、`references/`、`scripts/`、`assets/` 保持仓颉编译结果，不改写方法论。

用户级安装根是 `%USERPROFILE%\.bohrium\skills`。只扫描这一层，嵌套的 `SKILL.md` 不会单独出现。

## 步骤

1. 确认有原文。没有文本就停下，不凭记忆蒸馏。
2. 按 `wisp-cangjie` 做阶段 0 到阶段 4，并在骨架、入选名单、single/pack 三处让用户确认。
3. 用仓颉编译器生成 Wisp 产物。这一步的 frontmatter 仍是 Wisp 格式，不能直接安装。
4. 在本仓库根目录执行：

```text
python -m bohrium_cangjie adapt --source <仓颉 dist 或单个技能目录> --out <适配输出>
```

5. 读 JSON 报告。`rejected` 的目录不要安装。`stripped_keys` 里应能看到被去掉的 `tags`、`wisp`、`metadata`。
6. 用户确认安装位置后执行：

```text
python -m bohrium_cangjie install --source <适配输出> --dest %USERPROFILE%\.bohrium\skills
```

`unchanged` 表示目标已有相同内容。`conflict` 表示目标已有不同内容，本命令不会覆盖。
7. 从安装目录回读 `SKILL.md`，确认第一行是 `---`，且只有两个字段。告诉用户新开一条玻尔对话后，技能才会被重新扫描。

仓库未安装进当前 Python 时，在仓库根目录用 `PYTHONPATH=src` 运行同一个模块。Windows PowerShell 是 `$env:PYTHONPATH = "src"`。
