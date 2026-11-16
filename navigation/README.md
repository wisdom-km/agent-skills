# Skill map command

**English** | 简体中文在下面。

This folder is the checker for the skill catalog. It is not an eighth skill, and it does not record whether a project has used a skill. That record belongs to the project.

The repository navigation is [`NAVIGATION.md`](../NAVIGATION.md). Relations live in [`catalog.json`](catalog.json). A skill folder's `SKILL.md` is the source for its name and description. The scanner does not hardcode the current seven skills.

## What actually runs

Nothing runs until a person or an agent invokes the command. There is no daemon, no timer inside this repository, and no network call. The command does not execute skill files; it only reads `SKILL.md` frontmatter as text.

Wire it into the consuming project's `AGENTS.md` (the template in `agent-constraint-docs` already has a short pointer). At the start of work, the agent runs:

```bash
/absolute/path/to/agent-skills/navigation/skill-map sync \
  --project /absolute/path/to/your-project \
  --source /absolute/path/to/agent-skills/skills
```

`--project` is required and must be absolute. The command will not guess a project from the current working directory. `--source` may be absolute, or relative to that project root. The same relative source resolves to the same directory no matter which directory you ran the command from. Copy the command into the project; the skills directory can live outside the project.

You can also copy `navigation/skill-map` and `navigation/skill_map.py` into the project and pass `--catalog` as an absolute path to this `catalog.json`. If you omit `--catalog`, the command looks for `<source>/catalog.json` and then for `catalog.json` next to the script. If neither exists, every relationship stays unknown. A new skill still appears.

## What it writes

Only these two paths, and only inside `--project`:

- `SKILL_MAP.md` — the view, including a Mermaid picture and a text fallback
- `.skill-map/usage.json` — status, notes, reason, evidence, and history

It does not modify the skills source, the catalog, or any other project. If `--project` is the skills directory or a folder inside it, the command refuses to write.

## Status

| Status | Meaning |
| --- | --- |
| `unverified` | Seen, not yet judged. This is the status of a newly discovered skill. |
| `using` | In use now. More than one skill may be `using`. Requires evidence. |
| `used` | Used before. Requires evidence. This is not task completion. |
| `next` | The next skill to open, with a reason. |
| `conditional` | Applies only in some cases, with a reason. |
| `inapplicable` | Does not apply to this project, with a reason. |

Reading or loading a skill is not evidence. `used` and `using` without evidence are rejected and the files are left unchanged. A skill removed from the source stays in the map with `availability: unavailable`; notes, evidence, and history stay. If the folder comes back, the old status is kept.

Record a change with:

```bash
navigation/skill-map set \
  --project /absolute/path/to/your-project \
  --skill vibe-coding-loop \
  --status using \
  --evidence "the command you ran and its exit code" \
  --note "optional project note" \
  --expect-revision 3
```

`--expect-revision` is optional. Pass the revision printed in `SKILL_MAP.md` when more than one agent may update the same project. If the revision does not match, nothing is written.

## Failure behavior

The command exits non-zero, prints one reason to stderr, and does not leave a half-updated map. A crash during the replace restores the previous `SKILL_MAP.md` and `usage.json`.

| Exit | When |
| --- | --- |
| 0 | The check finished. `unchanged=yes` means a second run wrote nothing. |
| 2 | The project path is missing, relative, or ambiguous, or the requested status has no evidence or reason. |
| 3 | The project, the skills source, or an explicit catalog does not exist. |
| 4 | A file or directory cannot be read, or the replace failed and the previous files were restored. |
| 5 | The usage map, catalog, or skill frontmatter is malformed. |
| 6 | Another update holds the lock on this project. |
| 7 | The usage file belongs to a different project root, or `--expect-revision` does not match. |
| 127 | `python3` is not on `PATH`. The shell wrapper exits before Python starts. |

`python3` from the standard library is the only runtime. No packages are installed.

## Several agents, several projects

The command takes an exclusive, non-blocking lock on the project directory for the duration of one sync or set. If the lock is held, it exits 6 and writes nothing. It does not merge two edits. History is append-only, so a later status does not erase the earlier one; the latest status is the current row, and the old row remains in history.

Run the command once per project root. Project A and project B can share one skills directory. Updating A does not open B's files. There is no combined progress file.

## Adding a skill later

Add `skills/<name>/SKILL.md` with `name` equal to the directory name. The next sync on a project adds it as `unverified`. If you know how it relates to skills already in `catalog.json`, add a relation and a group entry, then regenerate the repository page:

```bash
navigation/skill-map render-library \
  --source /absolute/path/to/agent-skills/skills \
  --out /absolute/path/to/agent-skills/NAVIGATION.md
```

If you do not know the relationship, leave the catalog alone. The map shows 关系未知 / relationship unknown and does not invent an arrow.

---

# 使用地图命令

这个目录是技能目录的核对命令，不是第八个 Skill，也不记录某个项目用过没有。使用记录属于那个项目。

仓库总导航是 [`NAVIGATION.md`](../NAVIGATION.md)。关系写在 [`catalog.json`](catalog.json)。每个 Skill 的名字和说明以该文件夹的 `SKILL.md` 为准。扫描器没有把现在这七个 Skill 的名字写死。

## 实际会跑什么

人和 agent 不调用，它就不跑。本仓库没有守护进程，没有定时器，也不访问网络。命令不执行 Skill 文件，只把 `SKILL.md` 开头的 frontmatter 当文本读。

把它写进使用方项目的 `AGENTS.md`（`agent-constraint-docs` 的模板里已经有一句指针）。开工时运行：

```bash
/绝对路径/agent-skills/navigation/skill-map sync \
  --project /绝对路径/你的项目 \
  --source /绝对路径/agent-skills/skills
```

`--project` 必填，而且必须是绝对路径。命令不会根据当前工作目录猜测项目。`--source` 可以是绝对路径，也可以相对这个项目根。同一条相对路径，无论从哪个目录运行，都指向同一个技能目录。技能目录可以放在项目外面，把上面的命令抄进项目即可。

也可以把 `navigation/skill-map` 和 `navigation/skill_map.py` 拷进项目，并用绝对路径把 `--catalog` 指到这份 `catalog.json`。不传 `--catalog` 时，先找 `<source>/catalog.json`，再找脚本旁边的 `catalog.json`。两处都没有，所有关系保持未知，新 Skill 仍会出现。

## 写到哪里

只写 `--project` 里面的这两个路径：

- `SKILL_MAP.md`：给人看的视图，含 Mermaid 图和文本回退
- `.skill-map/usage.json`：状态、备注、理由、证据和历史

不改技能目录，不改目录文件，也不改别的项目。`--project` 如果就是技能目录，或者在技能目录里面，命令拒绝写入。

## 状态

| 状态 | 含义 |
| --- | --- |
| `unverified` | 看到了，还没判断。新发现的 Skill 用这个状态。 |
| `using` | 现在正在用。可以同时有多个。必须有证据。 |
| `used` | 以前用过。必须有证据。这不是任务完成。 |
| `next` | 下一步要打开的 Skill，要写理由。 |
| `conditional` | 只有某些情况才用，要写理由。 |
| `inapplicable` | 这个项目用不上，要写理由。 |

只读过或加载过 Skill，不是证据。`used` 和 `using` 没有证据时，命令拒绝写入，文件保持原样。Skill 从目录里删除后，仍留在地图里，`availability` 为 `unavailable`；备注、证据和历史都还在。文件夹回来以后，原来的状态还在。

记录一次变化：

```bash
navigation/skill-map set \
  --project /绝对路径/你的项目 \
  --skill vibe-coding-loop \
  --status using \
  --evidence "你跑过的命令和退出码" \
  --note "可选备注" \
  --expect-revision 3
```

`--expect-revision` 可选。多个 agent 可能改同一个项目时，把 `SKILL_MAP.md` 里印出的修订号传进去。对不上就不写。

## 失败时

命令以非 0 退出，把一条原因写到 stderr，不会留下改了一半的地图。替换过程中失败的话，会把原来的 `SKILL_MAP.md` 和 `usage.json` 放回去。

| 退出码 | 什么时候 |
| --- | --- |
| 0 | 核对完成。`unchanged=yes` 表示再跑一次没有写文件。 |
| 2 | 项目路径缺失、是相对路径、含糊，或者这个状态缺证据或理由。 |
| 3 | 项目、技能目录，或显式指定的 catalog 不存在。 |
| 4 | 文件或目录读不了，或者替换失败且旧文件已恢复。 |
| 5 | 使用地图、catalog 或 Skill frontmatter 格式坏了。 |
| 6 | 另一个更新正锁着这个项目。 |
| 7 | 使用记录属于别的项目根，或者 `--expect-revision` 对不上。 |
| 127 | `PATH` 里没有 `python3`。壳脚本在启动 Python 之前退出。 |

运行时只需要系统自带的 `python3`，不安装其他包。

## 多个 agent、多个项目

一次 sync 或 set 期间，命令对项目目录加独占锁，而且不等待。锁被占用就以 6 退出，什么都不写。它不会把两份编辑合并。历史只追加：后面的状态不会抹掉前面的记录；最新状态写在当前这一行，旧的留在历史里。

每个项目根运行一次。项目 A 和项目 B 可以共用一个技能目录。更新 A 不会打开 B 的文件。没有一份合并两边进度的文件。

## 以后再加 Skill

在 `skills/<name>/SKILL.md` 里写上和目录名相同的 `name`。项目下次 sync 会把它标成未核实。如果知道它和 `catalog.json` 里已有 Skill 的关系，就补上关系和分组，然后重新生成总导航：

```bash
navigation/skill-map render-library \
  --source /绝对路径/agent-skills/skills \
  --out /绝对路径/agent-skills/NAVIGATION.md
```

关系不清楚就不要改 catalog。地图会显示关系未知，并且不会编造箭头。
