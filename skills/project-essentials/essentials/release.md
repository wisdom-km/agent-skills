# E11 版本号与 CHANGELOG

档位：曳光弹 + 长期。时机：发布前。

类比：药盒上的批号。出了问题，先知道是哪一批。

为什么：bug 报告第一件要问的就是「哪个版本」。没有版本号，用户说的问题和你手里的代码对不上。

## 最低版

1. 用语义化版本号 `MAJOR.MINOR.PATCH`：不兼容的改动升 MAJOR；兼容的新功能升 MINOR；兼容的 bug 修复升 PATCH（[Semantic Versioning 2.0.0](https://semver.org/)）。第一次给别人用之前，可以用 `0.x.y`。
2. 版本号只写在一个地方（例如 `package.json`、`pyproject.toml`、扩展的 manifest），其他地方从这里读。
3. 应用里能看到版本号（关于页面、`--version`、设置页），日志里带 `version` 字段（见 `debug-with-logs` 的 LOGS.md）。
4. 每次发布写一条 CHANGELOG，模板见 [CHANGELOG.md](../templates/CHANGELOG.md)。原则：写给人看，不是给机器看；每个版本一条；同类改动放在一起；最新的在最上面；写上发布日期（[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/)）。
5. 发布时打 tag，用带说明的 annotated tag：`git tag -a v0.4.2 -m "v0.4.2"`。它会记录创建时间、打 tag 的人和说明（[git tag](https://git-scm.com/docs/git-tag)）。

## 检查

- 机器：发布脚本检查版本号格式，并检查 CHANGELOG 里有这个版本的条目。
- 人：发布前确认 CHANGELOG 写了用户能看懂的改动，而不是提交记录的复制。
