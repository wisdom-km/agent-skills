# Skill map command

**English** | 简体中文在下面。

This folder is the checker for the skill catalog. It is not an eighth skill, and it does not record whether a project has used a skill. That record belongs to the project.

The repository navigation is [`NAVIGATION.md`](../NAVIGATION.md). Relations live in [`catalog.json`](catalog.json). A skill folder's `SKILL.md` is the source for its name and description. The scanner does not hardcode the current seven skills.

## What actually runs

Nothing runs until a person or an agent invokes the command. There is no daemon, no timer inside this repository, and no network call. The command does not execute skill files; it only reads `SKILL.md` frontmatter as text.

Wire it into the consuming project's `AGENTS.md` (the template in `agent-constraint-docs` already has a short pointer). At the start of work, the agent runs one of the commands below. The exit code of that command is the result. A later successful print does not turn a failure into 0. On failure, report the exit code and stderr, and do not hand-write `SKILL_MAP.md`.

macOS or Linux:

```bash
/absolute/path/to/agent-skills/navigation/skill-map sync \
  --project /absolute/path/to/your-project \
  --source /absolute/path/to/agent-skills/skills
```

Windows cmd or PowerShell. The extension-less `skill-map` file is a POSIX shell script; cmd and PowerShell cannot run it. Do not call `python3` until it has printed a Python 3 version. The Microsoft Store alias exits 9009 and is not an interpreter.

```bat
py -3 C:\absolute\path\to\agent-skills\navigation\skill_map.py sync --project C:\absolute\path\to\your-project --source C:\absolute\path\to\agent-skills\skills
```

`navigation\skill-map.cmd` does the same lookup: `py -3`, then `python`, then `python3`. It uses `call`, so a `.cmd` alias that exits 9009 returns and the next name is tried; without `call` that alias would not return. It then returns the chosen program's exit code. The shell script tries `py -3`, then `python3`, then `python`, and keeps the interpreter's exit code. Quote paths that contain spaces.

`--project` is required and must be absolute. The command will not guess a project from the current working directory. `--source` may be absolute, or relative to that project root. The same relative source resolves to the same directory no matter which directory you ran the command from. Copy the command into the project; the skills directory can live outside the project.

You can also copy `navigation/skill-map`, `navigation/skill-map.cmd`, and `navigation/skill_map.py` into the project and pass `--catalog` as an absolute path to this `catalog.json`. If you omit `--catalog`, the command looks for `<source>/catalog.json` and then for `catalog.json` next to the script. If neither exists, every relationship stays unknown. A new skill still appears.

## What it writes

Only these usage paths, and only inside `--project`:

- `SKILL_MAP.md` — the view, including a Mermaid picture and a text fallback
- `.skill-map/usage.json` — status, notes, reason, evidence, and history

It also leaves `<project>/.skill-map.lock` in place. That file is the concurrency lock, not a usage record. A failed command may leave the lock file and still must not leave a partial map.

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
| 127 | No working Python 3. The wrappers try `py -3`, then `python3` or `python`, and reject a Store alias that exits 9009. Nothing is written. |

The runtime is the Python 3 standard library. No packages are installed. `py -3`, `python`, or `python3` all qualify only when the program actually starts and reports Python 3.

## Several agents, several projects

The command takes an exclusive, non-blocking lock on `<project>/.skill-map.lock` for the duration of one sync or set. It does not open the project directory to lock it. POSIX uses `fcntl.flock`. Windows uses `msvcrt.locking` on one byte of that file. If the lock is held, it exits 6 and does not change `SKILL_MAP.md` or `usage.json`. It does not merge two edits, and it does not delete the lock file out from under the holder. History is append-only, so a later status does not erase the earlier one; the latest status is the current row, and the old row remains in history.

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

把它写进使用方项目的 `AGENTS.md`（`agent-constraint-docs` 的模板里已经有一句指针）。开工时运行下面其中一条。这条命令自己的退出码就是结果；后面再打印一行成功，不能把失败变成 0。失败就报告退出码和 stderr，不要手写 `SKILL_MAP.md`。

macOS 或 Linux：

```bash
/绝对路径/agent-skills/navigation/skill-map sync \
  --project /绝对路径/你的项目 \
  --source /绝对路径/agent-skills/skills
```

Windows 的 cmd 或 PowerShell。不带扩展名的 `skill-map` 是 POSIX 脚本，cmd 和 PowerShell 不能跑。先确认 `python3` 能打出 Python 3 的版本；应用商店别名会退出 9009，那不是解释器。

```bat
py -3 C:\绝对路径\agent-skills\navigation\skill_map.py sync --project C:\绝对路径\你的项目 --source C:\绝对路径\agent-skills\skills
```

`navigation\skill-map.cmd` 按同样的顺序找解释器：`py -3`，然后 `python`，然后 `python3`。它用 `call` 调用。退出 9009 的 `.cmd` 别名会返回，才会试下一个名字；不加 `call` 时控制权交出去，不会回来。然后把选中的那个程序的退出码原样返回。壳脚本的顺序是 `py -3`、`python3`、`python`，同样保留解释器的退出码。路径里有空格时加上引号。

`--project` 必填，而且必须是绝对路径。命令不会根据当前工作目录猜测项目。`--source` 可以是绝对路径，也可以相对这个项目根。同一条相对路径，无论从哪个目录运行，都指向同一个技能目录。技能目录可以放在项目外面，把上面的命令抄进项目即可。

也可以把 `navigation/skill-map`、`navigation/skill-map.cmd` 和 `navigation/skill_map.py` 拷进项目，并用绝对路径把 `--catalog` 指到这份 `catalog.json`。不传 `--catalog` 时，先找 `<source>/catalog.json`，再找脚本旁边的 `catalog.json`。两处都没有，所有关系保持未知，新 Skill 仍会出现。

## 写到哪里

使用记录只写 `--project` 里面的这两个路径：

- `SKILL_MAP.md`：给人看的视图，含 Mermaid 图和文本回退
- `.skill-map/usage.json`：状态、备注、理由、证据和历史

另外会留下 `<项目>/.skill-map.lock`。那是并发锁，不是使用记录。失败时这个锁文件可以留着，地图仍然不能改到一半。

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
| 127 | 没有能用的 Python 3。包装脚本会试 `py -3`，再试 `python3` 或 `python`，并拒绝退出 9009 的商店别名。什么使用记录都不写。 |

运行时只需要 Python 3 标准库，不安装其他包。`py -3`、`python`、`python3` 只有在真的启动并报告 Python 3 时才算数。

## 多个 agent、多个项目

一次 sync 或 set 期间，命令对 `<项目>/.skill-map.lock` 加独占锁，而且不等待。它不会把项目目录打开来加锁。POSIX 用 `fcntl.flock`。Windows 用 `msvcrt.locking` 锁这个文件的一个字节。锁被占用就以 6 退出，不改 `SKILL_MAP.md` 和 `usage.json`。它不会把两份编辑合并，也不会在持有者还在用的时候删掉锁文件。历史只追加：后面的状态不会抹掉前面的记录；最新状态写在当前这一行，旧的留在历史里。

每个项目根运行一次。项目 A 和项目 B 可以共用一个技能目录。更新 A 不会打开 B 的文件。没有一份合并两边进度的文件。

## 以后再加 Skill

在 `skills/<name>/SKILL.md` 里写上和目录名相同的 `name`。项目下次 sync 会把它标成未核实。如果知道它和 `catalog.json` 里已有 Skill 的关系，就补上关系和分组，然后重新生成总导航：

```bash
navigation/skill-map render-library \
  --source /绝对路径/agent-skills/skills \
  --out /绝对路径/agent-skills/NAVIGATION.md
```

关系不清楚就不要改 catalog。地图会显示关系未知，并且不会编造箭头。
