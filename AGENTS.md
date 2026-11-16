# AGENTS.md

本仓库是 Skill 库，不是某个产品的进度板。本文只做指针。

- 技能关系的总导航：[`NAVIGATION.md`](NAVIGATION.md)。使用状态不写进本仓库。
- 每个使用方项目在自己的根目录保存 `SKILL_MAP.md`。更新命令、失败时怎么办、多项目隔离：[`navigation/README.md`](navigation/README.md)。
- 强制项、关口和红线仍只以 [`skills/project-essentials/MANDATORY.md`](skills/project-essentials/MANDATORY.md) 为准（M-01 到 M-15，G0 到 G3，R-1 到 R-3）。本文件不改那些规则。
- 开工核对技能目录时，运行 `navigation/skill-map sync`。`--project` 必须是那个项目根的绝对路径。不要猜项目，不要把使用记录写进 `skills/`。
- Windows 的 cmd / PowerShell 用 `py -3 <技能库>\navigation\skill_map.py sync`，或 `navigation\skill-map.cmd`。`python3` 退出 9009 就不是解释器。失败就报告这条命令自己的退出码，不要手写 `SKILL_MAP.md`。
