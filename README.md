# bohrium-cangjie

把 [Wisp Cangjie](https://github.com/Yu-Qiao-sjtu/wisp-cangjie) 编译出的技能，收成玻尔科学空间桌面端能加载的格式。

仓颉继续负责阶段 0 到阶段 4，以及 `scripts/distill.py compile`。它的 `SKILL.md` 带块标量 `description`，还有 `tags`、`wisp` 和 `metadata`。本机 `scix.exe` `0.10.17` 的扫描器只接受 `name` 与单行 `description`，多出来的字段会让技能不可用。`adapt` 的输出目录就是玻尔直接扫描的技能，安装时不再做第二次格式转换。正文和附属文件原样复制。

## 契约

规则来自本机 `D:\玻尔·科学空间\versions\0.10.17-ebc8e7182ab8-required-1520739-update\scix.exe` 里的 `src/local_skills/frontmatter.rs`，以及 `brain.mjs` 的目录预览长度。

| 项 | 要求 |
|---|---|
| 位置 | `%USERPROFILE%\.bohrium\skills\<name>\SKILL.md`，只扫描一层 |
| frontmatter | 只有 `name`、`description` |
| `name` | 全小写 kebab-case，短于 64 字符，等于目录名 |
| `description` | 非空单行，最多 1024 字符，不能含 `<` `>` |
| 目录预览 | 500 字符后截断，触发词放在前面 |
| 编码 | UTF-8，无 BOM |
| 禁止键 | `disableModelInvocation`、`modelInvocable`、`userInvocable` |

## 用法

```powershell
$env:PYTHONPATH = "src"
python -m bohrium_cangjie adapt --source D:\path\to\cangjie\dist\book --out D:\path\to\adapted
python -m bohrium_cangjie install --source D:\path\to\adapted --dest "$env:USERPROFILE\.bohrium\skills"
```

`--source` 可以是单个技能目录，也可以是仓颉 pack（若干 `<name>/SKILL.md` 与旁边的审计文件）。命令把 JSON 报告写到 stdout。`rejected` 或 `conflict` 时退出码为 1。pack 里有一个技能被拒绝时，整份适配输出会删掉。`conflict` 不会覆盖已经装过、且内容不同的目录。点开头的文件和符号链接不会复制。

装完以后新开一条玻尔对话，宿主才会重新扫描。

## 例子

`examples/high-expression-good-prognosis/` 是成品技能，演示「高表达且预后较好的基因如何讨论」。来源文章是 [高表达，预后好基因的研究思路](https://mp.weixin.qq.com/s/c5IMOOi7MXYVVVBc4SBFBA)。文中的反式脂肪酸和灌胃实验只留在能力卡示例里，不写进技能的触发条件。目录里的 `SKILL.md` 只有 `name` 和 `description`，复制到 `%USERPROFILE%\.bohrium\skills\high-expression-good-prognosis` 即可被玻尔识别。

给玻尔代理用的操作说明在 `skills/bohrium-cangjie/SKILL.md`。安装这个技能时，目录名必须是 `bohrium-cangjie`。

## 测试

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```
