# bohrium-cangjie

把 [Wisp Cangjie](https://github.com/Yu-Qiao-sjtu/wisp-cangjie) 编译出的技能，收成玻尔科学空间桌面端能加载的格式。

## 边界

当前蒸馏只接受文字和静态图片，不接受文字加视频。

文字限于期刊论文、预印本、综述、述评，讲解研究该怎么讨论的书面点评，以及以方法选择和讨论顺序为正文的书面材料。图片限于嵌在这些文字里的机制图、通路图、技术路线图、结果图和统计图，并且要和图注、正文一起读。

视频、播客、课程录像、字幕、时间轴，以及文字只是视频简介的材料，不在范围内。从视频截下来的帧也不当作科学图来蒸馏。

仓颉继续负责阶段 0 到阶段 4，以及 `scripts/distill.py compile`，但只处理上面边界内的文字和配图。编译结果里的 `description` 是块标量，并带有 `tags`、`wisp` 和 `metadata`。`adapt` 只保留 `name` 与单行 `description`，输出目录就是玻尔直接扫描的技能，安装时不再做第二次格式转换。正文在交付前改成用户要做的事，不把仓颉的原子能力卡原样装上。

## 用法

```powershell
$env:PYTHONPATH = "src"
python -m bohrium_cangjie adapt --source D:\path\to\cangjie\dist\book --out D:\path\to\adapted
python -m bohrium_cangjie install --source D:\path\to\adapted --dest "$env:USERPROFILE\.bohrium\skills"
```

`--source` 可以是单个技能目录，也可以是仓颉 pack（若干 `<name>/SKILL.md` 与旁边的审计文件）。命令把 JSON 报告写到 stdout。`rejected` 或 `conflict` 时退出码为 1。pack 里有一个技能被拒绝时，整份适配输出会删掉。`conflict` 不会覆盖已经装过、且内容不同的目录。点开头的文件和符号链接不会复制。

装完以后新开一条玻尔对话，宿主才会重新扫描。

## 例子

`examples/high-expression-good-prognosis/` 演示「高表达且预后较好的基因如何讨论」。来源文章是 [高表达，预后好基因的研究思路](https://mp.weixin.qq.com/s/c5IMOOi7MXYVVVBc4SBFBA)。讨论顺序在 `SKILL.md`，文中那项研究只在 `references/example.md`。目录复制到 `%USERPROFILE%\.bohrium\skills\high-expression-good-prognosis` 即可被玻尔识别。

给玻尔代理用的操作说明在 `skills/bohrium-cangjie/SKILL.md`。安装这个技能时，目录名必须是 `bohrium-cangjie`。

## 测试

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```
