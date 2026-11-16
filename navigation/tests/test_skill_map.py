#!/usr/bin/env python3
"""Fixture tests for per-project skill usage maps."""

from __future__ import annotations

import builtins
import errno
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "navigation"))
import skill_map  # noqa: E402

SEVEN = {
    "architecture-from-idea",
    "agent-constraint-docs",
    "vibe-coding-loop",
    "architecture-guardrails",
    "debug-with-logs",
    "project-essentials",
    "always-on-agents",
}
MANDATORY_SHA256 = "a153b243dab10df7de9e564146ad9a2f7d14c0d6c5b8b0ead1b6109bdc3aeac4"
MANDATORY_SECTION = """## 强制项（MUST）

编号和细则来自 `project-essentials` 的 MANDATORY.md，这里只写本项目用到的结论。

- 档位：_原型 / 曳光弹 / 长期_（未确认时写「档位未确认，按曳光弹」）
- 条件：[D] 存真实用户数据 _是 / 否_；[P] 别人能访问 _是 / 否_
- 本档 MUST：_例如原型：M-01 git 小步提交；M-02 一条命令跑 + README；M-03 密钥不进仓库；M-04 出错带上下文打印到一处；M-05 不吞错；M-07 提交前 AI 用人话讲改动；M-09 锁文件已提交_
- 条件 MUST：_[D] 时 M-11；[P] 时 M-10（长期另有 M-14）_
- 本档 SHOULD：_例如原型：M-06 冒烟检查；M-08 CI；M-12 DECISIONS.md_
- 红线（不可豁免）：R-1 密钥不进仓库；R-2 不对真实数据做没有备份的不可逆操作；R-3 不编造测试或检查结果
- 全量检查命令：`scripts/check`_（Windows：`scripts/check.ps1`；没装模板时写实际命令）_。退出码非 0 就是「未满足」
- 豁免：只认用户原话，记在 `docs/WAIVERS.md`_（长期：另写 ADR）_
- 关口：开工前 G0；说「完成」前 G1；合入前 G2；发布前 G3。到关口输出门禁表，每项 PASS（附证据）/ FAIL / WAIVED / N/A。
- **任一 MUST 是 FAIL：报告「未满足：M-xx」和补法，不说「完成」，不合入，不发布。**
"""


def quote_cmd(value):
    return '"' + str(value).replace('"', '""') + '"'


def run_launcher(args, env, cwd):
    """Run the launcher this OS can execute.

    Windows CreateProcess rejects the extensionless POSIX script (WinError 193).
    cmd.exe runs skill-map.cmd there. POSIX runs navigation/skill-map.
    """
    if os.name == "nt":
        script = REPO / "navigation" / "skill-map.cmd"
        command = " ".join(quote_cmd(part) for part in [script, *args])
        return subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
    return subprocess.run(
        [str(REPO / "navigation" / "skill-map"), *args],
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8", newline="\n")
    path.chmod(0o755)


def write_cmd_file(path: Path, body: str) -> None:
    path.write_bytes(body.replace("\n", "\r\n").encode("ascii"))


def windows_py_launcher():
    candidates = []
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    candidates.append(Path(system_root) / "py.exe")
    candidates.append(Path(system_root) / "System32" / "py.exe")
    local = os.environ.get("LocalAppData")
    if local:
        candidates.append(Path(local) / "Programs" / "Python" / "Launcher" / "py.exe")
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if directory:
            candidates.append(Path(directory) / "py.exe")
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def symlink_or_skip(test, link: Path, target: Path) -> None:
    """Create link. If this account cannot, skip only this symlink assertion."""
    try:
        link.symlink_to(target)
    except OSError as exc:
        winerror = getattr(exc, "winerror", None)
        denied = winerror == 1314 or (os.name == "nt" and exc.errno in {errno.EPERM, errno.EACCES})
        if not denied:
            raise
        test.skipTest(
            "OS symlink was not created "
            f"({exc}). Symlink refusal is NOT verified on this run. "
            "The file lock, unreadable-input failure, and the non-symlink outside-path guard still run."
        )


class _DenyRead:
    """Make one file's read raise PermissionError for the duration of a command.

    POSIX first uses chmod(0) when that actually denies read. Windows chmod(0)
    leaves the file readable, so the same OSError is injected at Path.read_text,
    which is the read skill_map.py performs. Either way the command must exit
    unreadable and leave the previous map bytes alone.
    """

    def __init__(self, path: Path):
        self.path = path
        self.mode = path.stat().st_mode
        self.real_read_text = None
        self.used = ""

    def __enter__(self):
        self.path.chmod(0)
        try:
            self.path.read_bytes()
        except OSError:
            self.used = "chmod"
            return self
        self.path.chmod(self.mode)
        target = self.path.resolve()
        real = Path.read_text

        def wrapped(path_self, *args, **kwargs):
            try:
                if path_self.resolve() == target:
                    raise PermissionError(13, "Permission denied")
            except PermissionError:
                raise
            except OSError:
                pass
            return real(path_self, *args, **kwargs)

        self.real_read_text = real
        Path.read_text = wrapped
        self.used = "injected"
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.used == "chmod":
            self.path.chmod(self.mode)
        elif self.real_read_text is not None:
            Path.read_text = self.real_read_text
        return False


def run(argv, cwd=None):
    previous = os.getcwd()
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        if cwd is not None:
            os.chdir(cwd)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = skill_map.main(argv)
    finally:
        os.chdir(previous)
    return code, stdout.getvalue(), stderr.getvalue()


def write_skill(source: Path, name: str, description: str = "Use when the fixture says so.") -> None:
    folder = source / name
    folder.mkdir(parents=True, exist_ok=True)
    text = textwrap.dedent(
        f"""\
        ---
        name: {name}
        description: >-
          {description}
        ---

        # {name}
        """
    )
    (folder / "SKILL.md").write_text(text, encoding="utf-8")


def tree_hashes(root: Path) -> dict[str, str]:
    found = {}
    if not root.exists():
        return found
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            found[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


class SkillMapTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skill-map-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def project(self, name="project"):
        path = self.tmp / name
        path.mkdir()
        return path.resolve()

    def source_with(self, names, root_name="skills"):
        source = self.tmp / root_name
        source.mkdir()
        for name in names:
            write_skill(source, name, f"Use when working on {name}.")
        return source.resolve()

    def sync(self, project, source, cwd=None, extra=None):
        argv = ["sync", "--project", str(project), "--source", str(source)]
        if extra:
            argv.extend(extra)
        return run(argv, cwd=cwd)

    def state(self, project):
        return json.loads((project / ".skill-map" / "usage.json").read_text(encoding="utf-8"))


class DiscoverTests(SkillMapTestCase):
    def test_real_seven_are_discovered_from_source_not_a_hardcoded_list(self):
        found = skill_map.discover_skills((REPO / "skills").resolve())
        self.assertEqual(set(found), SEVEN)
        for name, meta in found.items():
            self.assertEqual(meta["name"], name)
            self.assertTrue(meta["description"].startswith("Use "))
            self.assertNotIn("os.system", meta["description"])

    def test_real_seven_sync_is_idempotent_and_records_paths(self):
        project = self.project("real project")
        source = (REPO / "skills").resolve()
        before = tree_hashes(source)
        catalog_before = (REPO / "navigation" / "catalog.json").read_bytes()
        code, out, err = self.sync(project, source)
        self.assertEqual(code, 0, err)
        self.assertIn(str(project), out)
        self.assertIn(str(source), out)
        view = (project / "SKILL_MAP.md").read_text(encoding="utf-8")
        usage = (project / ".skill-map" / "usage.json").read_bytes()
        self.assertIn(f"`{project}`", view)
        self.assertIn(f"`{source}`", view)
        for name in SEVEN:
            self.assertEqual(self.state(project)["skills"][name]["status"], "unverified")
            self.assertEqual(self.state(project)["skills"][name]["evidence"], [])
            self.assertIn(name, view)
        code, out2, err = self.sync(project, source, cwd=Path("/"))
        self.assertEqual(code, 0, err)
        self.assertIn("unchanged=yes", out2)
        self.assertEqual((project / "SKILL_MAP.md").read_text(encoding="utf-8"), view)
        self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), usage)
        self.assertEqual(tree_hashes(source), before)
        self.assertEqual((REPO / "navigation" / "catalog.json").read_bytes(), catalog_before)

    def test_arbitrary_new_skill_is_unverified_and_relationship_unknown(self):
        project = self.project()
        source = self.source_with(["architecture-from-idea"])
        code, _, err = self.sync(project, source)
        self.assertEqual(code, 0, err)
        write_skill(source, "extra-skill", "Use when a skill is added later. Touch nothing.")
        marker = self.tmp / "should-not-be-created-by-skill-text"
        write_skill(
            source,
            "odd skill",
            f"Use when the name has a space. $(touch {marker}) os.system('no')",
        )
        code, _, err = self.sync(project, source)
        self.assertEqual(code, 0, err)
        state = self.state(project)
        self.assertEqual(state["skills"]["extra-skill"]["status"], "unverified")
        self.assertEqual(state["skills"]["extra-skill"]["evidence"], [])
        self.assertEqual(state["skills"]["architecture-from-idea"]["status"], "unverified")
        self.assertEqual(len(state["skills"]["architecture-from-idea"]["history"]), 1)
        view = (project / "SKILL_MAP.md").read_text(encoding="utf-8")
        self.assertIn("extra-skill", view)
        self.assertIn("odd skill", view)
        self.assertIn("关系未知", view)
        self.assertIn("Relationship unknown", view)
        mermaid = view.split("```mermaid", 1)[1].split("```", 1)[0]
        self.assertIn('s_extra_skill["extra-skill', mermaid)
        self.assertNotIn("s_extra_skill -->", mermaid)
        self.assertNotIn("--> s_extra_skill", mermaid)
        self.assertNotIn(".-> s_extra_skill", mermaid)
        self.assertFalse(marker.exists())


class SyncTests(SkillMapTestCase):
    def test_repeat_sync_keeps_notes_status_evidence_and_bytes(self):
        project = self.project("notes project")
        source = self.source_with(["alpha", "beta"])
        self.assertEqual(self.sync(project, source)[0], 0)
        code, _, err = run(
            [
                "set",
                "--project",
                str(project),
                "--skill",
                "alpha",
                "--status",
                "used",
                "--note",
                "keep this note",
                "--evidence",
                "ran tests; exit 0",
                "--reason",
                "not required for used",
            ]
        )
        self.assertEqual(code, 0, err)
        code, _, err = run(
            [
                "set",
                "--project",
                str(project),
                "--skill",
                "beta",
                "--status",
                "using",
                "--evidence",
                "editing beta now",
                "--note",
                "second note",
            ]
        )
        self.assertEqual(code, 0, err)
        before = (project / "SKILL_MAP.md").read_bytes()
        usage = (project / ".skill-map" / "usage.json").read_bytes()
        mtime = (project / ".skill-map" / "usage.json").stat().st_mtime_ns
        code, out, err = self.sync(project, source)
        self.assertEqual(code, 0, err)
        self.assertIn("unchanged=yes", out)
        self.assertEqual((project / "SKILL_MAP.md").read_bytes(), before)
        self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), usage)
        self.assertEqual((project / ".skill-map" / "usage.json").stat().st_mtime_ns, mtime)
        state = self.state(project)
        self.assertEqual(state["skills"]["alpha"]["notes"], "keep this note")
        self.assertEqual(state["skills"]["alpha"]["evidence"], ["ran tests; exit 0"])
        self.assertEqual(state["skills"]["alpha"]["status"], "used")
        self.assertEqual(state["skills"]["beta"]["status"], "using")

    def test_removed_source_keeps_history_and_stays_idempotent(self):
        project = self.project()
        source = self.source_with(["alpha", "beta"])
        self.assertEqual(self.sync(project, source)[0], 0)
        self.assertEqual(
            run(
                [
                    "set",
                    "--project",
                    str(project),
                    "--skill",
                    "alpha",
                    "--status",
                    "used",
                    "--evidence",
                    "alpha was used",
                    "--note",
                    "do not drop",
                ]
            )[0],
            0,
        )
        shutil.rmtree(source / "alpha")
        code, _, err = self.sync(project, source)
        self.assertEqual(code, 0, err)
        state = self.state(project)
        alpha = state["skills"]["alpha"]
        self.assertEqual(alpha["status"], "used")
        self.assertEqual(alpha["notes"], "do not drop")
        self.assertEqual(alpha["evidence"], ["alpha was used"])
        self.assertEqual(alpha["availability"], "unavailable")
        self.assertTrue(any(event["event"] == "source-missing" for event in alpha["history"]))
        view = (project / "SKILL_MAP.md").read_text(encoding="utf-8")
        self.assertIn("alpha", view)
        self.assertIn("源已不在", view)
        self.assertIn("do not drop", view)
        snapshot = (project / "SKILL_MAP.md").read_bytes()
        usage = (project / ".skill-map" / "usage.json").read_bytes()
        code, out, err = self.sync(project, source)
        self.assertEqual(code, 0, err)
        self.assertIn("unchanged=yes", out)
        self.assertEqual((project / "SKILL_MAP.md").read_bytes(), snapshot)
        self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), usage)
        write_skill(source, "alpha", "Use when alpha comes back.")
        code, _, err = self.sync(project, source)
        self.assertEqual(code, 0, err)
        alpha = self.state(project)["skills"]["alpha"]
        self.assertEqual(alpha["availability"], "available")
        self.assertEqual(alpha["status"], "used")
        self.assertEqual(alpha["evidence"], ["alpha was used"])
        self.assertTrue(any(event["event"] == "source-returned" for event in alpha["history"]))

    def test_reading_is_not_use_and_two_skills_can_be_current(self):
        project = self.project()
        source = self.source_with(["alpha", "beta", "gamma"])
        self.assertEqual(self.sync(project, source)[0], 0)
        code, _, err = run(
            [
                "set",
                "--project",
                str(project),
                "--skill",
                "alpha",
                "--status",
                "unverified",
                "--note",
                "read SKILL.md only",
            ]
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(self.state(project)["skills"]["alpha"]["status"], "unverified")
        before = (project / ".skill-map" / "usage.json").read_bytes()
        code, _, err = run(
            ["set", "--project", str(project), "--skill", "beta", "--status", "used"]
        )
        self.assertNotEqual(code, 0)
        self.assertIn("needs evidence", err)
        self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), before)
        self.assertEqual(
            run(
                [
                    "set",
                    "--project",
                    str(project),
                    "--skill",
                    "beta",
                    "--status",
                    "using",
                    "--evidence",
                    "beta command exit 0",
                ]
            )[0],
            0,
        )
        self.assertEqual(
            run(
                [
                    "set",
                    "--project",
                    str(project),
                    "--skill",
                    "gamma",
                    "--status",
                    "using",
                    "--evidence",
                    "gamma command exit 0",
                ]
            )[0],
            0,
        )
        self.assertEqual(
            run(
                [
                    "set",
                    "--project",
                    str(project),
                    "--skill",
                    "alpha",
                    "--status",
                    "next",
                    "--reason",
                    "docs exist, so the next coding task uses alpha",
                ]
            )[0],
            0,
        )
        view = (project / "SKILL_MAP.md").read_text(encoding="utf-8")
        mermaid = view.split("```mermaid", 1)[1].split("```", 1)[0]
        self.assertIn("正在用 (using)", mermaid)
        self.assertGreaterEqual(mermaid.count(":::current"), 2)
        self.assertIn("下一步 (next)", mermaid)
        self.assertIn(":::next", mermaid)
        self.assertIn("Text fallback / 文本回退", view)
        self.assertIn("`beta`", view)
        self.assertIn("`gamma`", view)
        self.assertIn("docs exist, so the next coding task uses alpha", view)
        for line in mermaid.splitlines():
            self.assertLess(len(line), 180, line)
            self.assertNotRegex(line, r"^\s*[A-Z]$")
        self.assertIn("beta", mermaid)
        self.assertIn("gamma", mermaid)
        self.assertIn("alpha", mermaid)

    def test_relative_source_is_stable_across_working_directories(self):
        project = self.project("proj")
        source = self.source_with(["alpha"])
        relative = os.path.relpath(source, project)
        self.assertFalse(Path(relative).is_absolute())
        code, _, err = self.sync(project, relative, cwd=Path("/tmp"))
        self.assertEqual(code, 0, err)
        recorded = self.state(project)["source"]
        self.assertEqual(recorded, str(source))
        first = (project / "SKILL_MAP.md").read_bytes()
        code, out, err = self.sync(project, relative, cwd=Path("/"))
        self.assertEqual(code, 0, err)
        self.assertIn("unchanged=yes", out)
        self.assertEqual((project / "SKILL_MAP.md").read_bytes(), first)
        self.assertEqual(self.state(project)["source"], str(source))

    def test_paths_with_spaces(self):
        project = self.project("project A")
        source = self.source_with(["alpha"], root_name="skill source")
        code, _, err = self.sync(project, source, cwd=self.tmp)
        self.assertEqual(code, 0, err)
        view = (project / "SKILL_MAP.md").read_text(encoding="utf-8")
        self.assertIn(str(project), view)
        self.assertIn(str(source), view)
        self.assertIn("alpha", self.state(project)["skills"])


class IsolationTests(SkillMapTestCase):
    def test_two_projects_share_a_source_without_cross_writing(self):
        source = self.tmp / "shared skills"
        shutil.copytree(REPO / "skills", source)
        project_a = self.project("project A")
        project_b = self.project("project B")
        source_before = tree_hashes(source)
        catalog_before = (REPO / "navigation" / "catalog.json").read_bytes()
        self.assertEqual(self.sync(project_a, source)[0], 0)
        self.assertEqual(self.sync(project_b, source)[0], 0)
        self.assertEqual(set(self.state(project_a)["skills"]), SEVEN)
        ordered = sorted(SEVEN)
        code, _, err = run(
            [
                "set",
                "--project",
                str(project_a),
                "--skill",
                ordered[0],
                "--status",
                "used",
                "--evidence",
                "A used one skill",
                "--note",
                "history A",
            ]
        )
        self.assertEqual(code, 0, err)
        for name in ordered[:6]:
            code, _, err = run(
                [
                    "set",
                    "--project",
                    str(project_b),
                    "--skill",
                    name,
                    "--status",
                    "used",
                    "--evidence",
                    f"B evidence {name}",
                    "--note",
                    f"history B {name}",
                ]
            )
            self.assertEqual(code, 0, err)
        self.assertEqual(self.sync(project_a, source)[0], 0)
        self.assertEqual(self.sync(project_b, source)[0], 0)
        b_map = (project_b / "SKILL_MAP.md").read_bytes()
        b_usage = (project_b / ".skill-map" / "usage.json").read_bytes()
        b_histories = {
            name: record["history"]
            for name, record in self.state(project_b)["skills"].items()
        }
        code, _, err = run(
            [
                "set",
                "--project",
                str(project_a),
                "--skill",
                ordered[0],
                "--status",
                "using",
                "--evidence",
                "A used one skill",
                "--note",
                "A changed after the snapshot",
                "--reason",
                "still the same skill",
            ]
        )
        self.assertEqual(code, 0, err)
        self.assertEqual((project_b / "SKILL_MAP.md").read_bytes(), b_map)
        self.assertEqual((project_b / ".skill-map" / "usage.json").read_bytes(), b_usage)
        self.assertEqual(tree_hashes(source), source_before)
        self.assertEqual((REPO / "navigation" / "catalog.json").read_bytes(), catalog_before)
        write_skill(source, "extra-skill", "Use when a later skill appears.")
        code, _, err = self.sync(project_a, source)
        self.assertEqual(code, 0, err)
        code, _, err = self.sync(project_b, source)
        self.assertEqual(code, 0, err)
        state_a = self.state(project_a)
        state_b = self.state(project_b)
        self.assertEqual(state_a["skills"]["extra-skill"]["status"], "unverified")
        self.assertEqual(state_b["skills"]["extra-skill"]["status"], "unverified")
        self.assertEqual(state_a["skills"]["extra-skill"]["notes"], "")
        self.assertEqual(state_b["skills"]["extra-skill"]["notes"], "")
        self.assertEqual(state_a["skills"][ordered[0]]["notes"], "A changed after the snapshot")
        self.assertEqual(state_a["skills"][ordered[0]]["evidence"], ["A used one skill"])
        for name in ordered[:6]:
            self.assertEqual(state_b["skills"][name]["status"], "used")
            self.assertEqual(state_b["skills"][name]["evidence"], [f"B evidence {name}"])
            self.assertEqual(state_b["skills"][name]["notes"], f"history B {name}")
            self.assertEqual(state_b["skills"][name]["history"][: len(b_histories[name])], b_histories[name])
        self.assertEqual(state_b["skills"][ordered[6]]["status"], "unverified")
        self.assertNotEqual(state_a["project_root"], state_b["project_root"])
        self.assertNotIn("history B", (project_a / "SKILL_MAP.md").read_text(encoding="utf-8"))
        self.assertNotIn("A changed after the snapshot", (project_b / "SKILL_MAP.md").read_text(encoding="utf-8"))

    def test_symlink_cannot_redirect_a_write_into_another_project(self):
        source = self.source_with(["alpha"])
        project_a = self.project("A")
        project_b = self.project("B")
        self.assertEqual(self.sync(project_a, source)[0], 0)
        self.assertEqual(self.sync(project_b, source)[0], 0)
        b_map = (project_b / "SKILL_MAP.md").read_bytes()
        b_usage = (project_b / ".skill-map" / "usage.json").read_bytes()
        (project_a / "SKILL_MAP.md").unlink()
        symlink_or_skip(self, project_a / "SKILL_MAP.md", project_b / "SKILL_MAP.md")
        code, _, err = self.sync(project_a, source)
        self.assertNotEqual(code, 0)
        self.assertIn("outside the project", err)
        self.assertEqual((project_b / "SKILL_MAP.md").read_bytes(), b_map)
        self.assertEqual((project_b / ".skill-map" / "usage.json").read_bytes(), b_usage)

    def test_sync_refuses_a_map_path_outside_the_project_without_a_symlink(self):
        project = self.project("guard")
        source = self.source_with(["alpha"])
        outside = self.tmp / "outside map.md"
        outside.write_bytes(b"keep-outside")
        real_map_path = skill_map.map_path

        def outside_map(_project):
            return outside

        skill_map.map_path = outside_map
        try:
            code, _, err = self.sync(project, source)
        finally:
            skill_map.map_path = real_map_path
        self.assertEqual(code, skill_map.EXIT_USAGE, err)
        self.assertIn("outside the project", err)
        self.assertEqual(outside.read_bytes(), b"keep-outside")
        self.assertFalse((project / "SKILL_MAP.md").exists())
        self.assertFalse((project / ".skill-map" / "usage.json").exists())


class FailureTests(SkillMapTestCase):
    def test_missing_source_and_relative_project_do_not_write(self):
        project = self.project()
        code, _, err = self.sync(project, self.tmp / "missing source")
        self.assertEqual(code, skill_map.EXIT_MISSING)
        self.assertIn("does not exist", err)
        self.assertFalse((project / "SKILL_MAP.md").exists())
        self.assertFalse((project / ".skill-map").exists())
        names = {path.name for path in project.iterdir()}
        self.assertTrue(names <= {".skill-map.lock"})
        code, _, err = run(["sync", "--project", "relative-project", "--source", "skills"], cwd=Path("/"))
        self.assertEqual(code, skill_map.EXIT_USAGE)
        self.assertIn("absolute", err)
        code, _, err = run(["sync", "--project", "relative-project", "--source", "skills"], cwd=Path("/tmp"))
        self.assertEqual(code, skill_map.EXIT_USAGE)
        self.assertIn("absolute", err)
        self.assertFalse((Path("/relative-project")).exists())
        self.assertFalse((Path("/tmp/relative-project")).exists())

    def test_launcher_missing_runtime_writes_nothing(self):
        project = self.project("runtime project")
        source = self.source_with(["alpha"])
        empty_path = self.tmp / "empty-path"
        empty_path.mkdir()
        env = os.environ.copy()
        env["PATH"] = str(empty_path)
        completed = run_launcher(
            ["sync", "--project", str(project), "--source", str(source)],
            env,
            self.tmp,
        )
        self.assertEqual(completed.returncode, 127, completed.stderr)
        self.assertIn("no working Python 3", completed.stderr)
        self.assertIn("9009", completed.stderr)
        self.assertIn("Nothing was written", completed.stderr)
        self.assertEqual(list(project.iterdir()), [])
        self.assertFalse((source / "SKILL_MAP.md").exists())

    def test_launcher_skips_bad_alias_and_keeps_the_interpreter_exit_code(self):
        project = self.project("alias project")
        missing = self.tmp / "missing source"
        env = os.environ.copy()
        if os.name == "nt":
            python_dir = str(Path(sys.executable).resolve().parent)
            fallback = self.tmp / "fallback-stubs"
            fallback.mkdir()
            write_cmd_file(fallback / "py.cmd", "@echo off\nexit /b 9009\n")
            env["PATH"] = str(fallback) + os.pathsep + python_dir
        else:
            bindir = self.tmp / "bin"
            bindir.mkdir()
            stub = "#!/bin/sh\nexit 9009\n"
            write_executable(bindir / "py", stub)
            write_executable(bindir / "python3", stub)
            write_executable(bindir / "python", f'#!/bin/sh\nexec {sys.executable} "$@"\n')
            env["PATH"] = str(bindir)
        completed = run_launcher(
            ["sync", "--project", str(project), "--source", str(missing)],
            env,
            self.tmp,
        )
        self.assertEqual(completed.returncode, skill_map.EXIT_MISSING, completed.stderr + completed.stdout)
        self.assertNotEqual(completed.returncode, 9009)
        self.assertIn("does not exist", completed.stderr)
        self.assertFalse((project / "SKILL_MAP.md").exists())
        self.assertFalse((project / ".skill-map").exists())

        blocked_project = self.project("blocked project")
        if os.name == "nt":
            only = self.tmp / "stub-only"
            only.mkdir()
            for name in ("py", "python", "python3"):
                write_cmd_file(only / f"{name}.cmd", "@echo off\nexit /b 9009\n")
            env["PATH"] = str(only)
        else:
            only = self.tmp / "stub-only"
            only.mkdir()
            stub = "#!/bin/sh\nexit 9009\n"
            for name in ("py", "python3", "python"):
                write_executable(only / name, stub)
            env["PATH"] = str(only)
        blocked = run_launcher(
            ["sync", "--project", str(blocked_project), "--source", str(self.source_with(["alpha"]))],
            env,
            self.tmp,
        )
        self.assertEqual(blocked.returncode, 127, blocked.stderr + blocked.stdout)
        self.assertIn("9009", blocked.stderr)
        self.assertIn("Nothing was written", blocked.stderr)
        self.assertEqual(list(blocked_project.iterdir()), [])

    def test_launcher_prefers_its_first_real_interpreter(self):
        project = self.project("prefer project")
        missing = self.tmp / "missing source 2"
        env = os.environ.copy()
        if os.name == "nt":
            py_launcher = windows_py_launcher()
            self.assertIsNotNone(
                py_launcher,
                "Windows cmd selection was not tested: py.exe was not found. "
                "Refusing to report a pass without the py -3 candidate.",
            )
            bad = self.tmp / "bad-later"
            bad.mkdir()
            for name in ("python", "python3"):
                write_cmd_file(bad / f"{name}.cmd", "@echo off\nexit /b 17\n")
            python_dir = str(Path(sys.executable).resolve().parent)
            env["PATH"] = os.pathsep.join([str(bad), str(py_launcher.parent), python_dir])
        else:
            bindir = self.tmp / "prefer-bin"
            bindir.mkdir()
            stub = "#!/bin/sh\nexit 9009\n"
            write_executable(
                bindir / "py",
                "#!/bin/sh\n"
                'if [ "$1" = "-3" ]; then shift; fi\n'
                f'exec {sys.executable} "$@"\n',
            )
            write_executable(bindir / "python3", stub)
            write_executable(bindir / "python", stub)
            env["PATH"] = str(bindir)
        completed = run_launcher(
            ["sync", "--project", str(project), "--source", str(missing)],
            env,
            self.tmp,
        )
        self.assertEqual(completed.returncode, skill_map.EXIT_MISSING, completed.stderr + completed.stdout)
        self.assertNotIn(completed.returncode, (0, 17, 9009))
        self.assertIn("does not exist", completed.stderr)
        self.assertFalse((project / "SKILL_MAP.md").exists())
        self.assertFalse((project / ".skill-map").exists())

    def test_malformed_and_unreadable_inputs_leave_the_project_unchanged(self):
        project = self.project()
        source = self.source_with(["alpha", "beta"])
        self.assertEqual(self.sync(project, source)[0], 0)
        view = (project / "SKILL_MAP.md").read_bytes()
        usage = (project / ".skill-map" / "usage.json").read_bytes()

        bad_catalog = self.tmp / "bad catalog.json"
        bad_catalog.write_text("{", encoding="utf-8")
        code, _, err = self.sync(project, source, extra=["--catalog", str(bad_catalog)])
        self.assertEqual(code, skill_map.EXIT_MALFORMED, err)
        self.assertIn("malformed catalog", err)
        self.assertEqual((project / "SKILL_MAP.md").read_bytes(), view)
        self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), usage)

        (source / "beta" / "SKILL.md").write_text("---\nname: beta\n", encoding="utf-8")
        code, _, err = self.sync(project, source)
        self.assertEqual(code, skill_map.EXIT_MALFORMED, err)
        self.assertIn("malformed skill metadata", err)
        self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), usage)
        write_skill(source, "beta", "Use when beta is valid again.")

        skill_file = source / "alpha" / "SKILL.md"
        skill_denial = _DenyRead(skill_file)
        with skill_denial:
            code, _, err = self.sync(project, source)
            self.assertEqual(code, skill_map.EXIT_UNREADABLE, err)
            self.assertIn("cannot read", err)
            self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), usage)
            self.assertEqual((project / "SKILL_MAP.md").read_bytes(), view)
        if os.name != "nt":
            self.assertEqual(skill_denial.used, "chmod")

        usage_path = project / ".skill-map" / "usage.json"
        usage_path.write_text("{", encoding="utf-8")
        code, _, err = self.sync(project, source)
        self.assertEqual(code, skill_map.EXIT_MALFORMED, err)
        self.assertIn("malformed usage map", err)
        self.assertEqual(usage_path.read_text(encoding="utf-8"), "{")
        self.assertEqual((project / "SKILL_MAP.md").read_bytes(), view)
        usage_path.write_bytes(usage)

        (project / "SKILL_MAP.md").write_bytes(b"\xff\xfe not utf-8")
        code, _, err = self.sync(project, source)
        self.assertEqual(code, skill_map.EXIT_MALFORMED, err)
        self.assertIn("not utf-8", err)
        self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), usage)
        self.assertEqual((project / "SKILL_MAP.md").read_bytes(), b"\xff\xfe not utf-8")
        (project / "SKILL_MAP.md").write_bytes(view)

        usage_denial = _DenyRead(usage_path)
        with usage_denial:
            code, _, err = self.sync(project, source)
            self.assertEqual(code, skill_map.EXIT_UNREADABLE, err)
            self.assertIn("cannot read", err)
            self.assertEqual((project / "SKILL_MAP.md").read_bytes(), view)
        if os.name != "nt":
            self.assertEqual(usage_denial.used, "chmod")

    def test_dangling_skill_symlink_is_unreadable_and_does_not_write(self):
        project = self.project()
        source = self.source_with(["alpha"])
        self.assertEqual(self.sync(project, source)[0], 0)
        usage = (project / ".skill-map" / "usage.json").read_bytes()
        view = (project / "SKILL_MAP.md").read_bytes()
        dangling = source / "gamma"
        dangling.mkdir()
        symlink_or_skip(self, dangling / "SKILL.md", source / "no-such-skill.md")
        code, _, err = self.sync(project, source)
        self.assertEqual(code, skill_map.EXIT_UNREADABLE, err)
        self.assertIn("dangling symlink", err)
        self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), usage)
        self.assertEqual((project / "SKILL_MAP.md").read_bytes(), view)

    def test_lock_and_revision_conflict_do_not_write(self):
        project = self.project()
        source = self.source_with(["alpha"])
        self.assertEqual(self.sync(project, source)[0], 0)
        before_map = (project / "SKILL_MAP.md").read_bytes()
        before_usage = (project / ".skill-map" / "usage.json").read_bytes()
        holder = subprocess.Popen(
            [
                sys.executable,
                "-c",
                textwrap.dedent(
                    """\
                    import sys, time
                    from pathlib import Path
                    sys.path.insert(0, sys.argv[2])
                    import skill_map
                    project = Path(sys.argv[1])
                    while True:
                        try:
                            held = skill_map.project_lock(project)
                            held.__enter__()
                            break
                        except skill_map.SkillMapError:
                            time.sleep(0.02)
                    time.sleep(30)
                    """
                ),
                str(project),
                str(REPO / "navigation"),
            ]
        )
        acquired = False
        holder_note = "lock holder did not start"
        for _ in range(50):
            if holder.poll() is not None:
                holder_note = f"holder exited {holder.returncode}"
                break
            try:
                with skill_map.project_lock(project):
                    pass
            except skill_map.SkillMapError as exc:
                if exc.code != skill_map.EXIT_LOCK:
                    raise
                acquired = True
                break
            time.sleep(0.05)
        self.assertTrue(acquired, holder_note)
        try:
            code, _, err = self.sync(project, source)
        finally:
            holder.terminate()
            holder.wait(timeout=5)
        self.assertEqual(code, skill_map.EXIT_LOCK)
        self.assertIn("holds the lock", err)
        self.assertEqual((project / "SKILL_MAP.md").read_bytes(), before_map)
        self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), before_usage)
        code, _, err = run(
            [
                "set",
                "--project",
                str(project),
                "--skill",
                "alpha",
                "--status",
                "next",
                "--reason",
                "because the docs exist",
                "--expect-revision",
                "999",
            ]
        )
        self.assertEqual(code, skill_map.EXIT_CONFLICT)
        self.assertIn("revision", err)
        self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), before_usage)

    def test_windows_backend_locks_a_file_and_does_not_open_the_directory(self):
        project = self.project()
        source = self.source_with(["alpha"])
        opened = []
        real_open = os.open

        def spy(path, flags, *args, **kwargs):
            if not isinstance(path, int):
                opened.append(Path(os.fsdecode(path)))
            return real_open(path, flags, *args, **kwargs)

        class FakeMsvcrt:
            LK_NBLCK = 2
            LK_UNLCK = 0

            def __init__(self):
                self.held = set()
                self.calls = []

            def locking(self, fd, mode, nbytes):
                self.calls.append((mode, nbytes))
                inode = os.fstat(fd).st_ino
                if mode == self.LK_NBLCK:
                    if inode in self.held:
                        raise PermissionError(13, "Permission denied")
                    self.held.add(inode)
                    return
                self.held.discard(inode)

        fake = FakeMsvcrt()
        real_import = builtins.__import__

        def guard(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "fcntl":
                raise AssertionError("Windows lock path imported fcntl")
            return real_import(name, globals, locals, fromlist, level)

        sys.modules["msvcrt"] = fake
        previous = skill_map.select_lock_backend
        skill_map.select_lock_backend = lambda: "msvcrt"
        skill_map.os.open = spy
        builtins.__import__ = guard
        try:
            code, _, err = self.sync(project, source)
            self.assertEqual(code, 0, err)
            self.assertTrue((project / "SKILL_MAP.md").is_file())
            self.assertTrue(any(path.name == ".skill-map.lock" for path in opened))
            self.assertFalse(any(path.resolve() == project for path in opened))
            self.assertIn((fake.LK_NBLCK, 1), fake.calls)
            held = skill_map.project_lock(project)
            held.__enter__()
            try:
                with self.assertRaises(skill_map.SkillMapError) as ctx:
                    with skill_map.project_lock(project):
                        pass
                self.assertEqual(ctx.exception.code, skill_map.EXIT_LOCK)
                self.assertIn("holds the lock", str(ctx.exception))
            finally:
                held.__exit__(None, None, None)
            self.assertFalse((project / "SKILL_MAP.md").read_bytes() == b"")
        finally:
            builtins.__import__ = real_import
            skill_map.select_lock_backend = previous
            skill_map.os.open = real_open
            sys.modules.pop("msvcrt", None)

    def test_symlink_lock_file_is_refused_without_touching_its_target(self):
        project = self.project()
        source = self.source_with(["alpha"])
        self.assertEqual(self.sync(project, source)[0], 0)
        before = (project / "SKILL_MAP.md").read_bytes()
        outside = self.tmp / "outside-lock"
        outside.write_bytes(b"keep")
        lock = project / ".skill-map.lock"
        lock.unlink()
        symlink_or_skip(self, lock, outside)
        code, _, err = self.sync(project, source)
        self.assertEqual(code, skill_map.EXIT_USAGE, err)
        self.assertIn("symlink", err)
        self.assertEqual(outside.read_bytes(), b"keep")
        self.assertEqual((project / "SKILL_MAP.md").read_bytes(), before)

    def test_failed_replace_restores_both_files(self):
        project = self.project()
        source = self.source_with(["alpha"])
        self.assertEqual(self.sync(project, source)[0], 0)
        (source / "alpha" / "SKILL.md").write_text(
            textwrap.dedent(
                """\
                ---
                name: alpha
                description: >-
                  Use when the description has changed.
                ---

                # alpha
                """
            ),
            encoding="utf-8",
        )
        before_map = (project / "SKILL_MAP.md").read_bytes()
        before_usage = (project / ".skill-map" / "usage.json").read_bytes()
        real_replace = os.replace
        calls = {"n": 0}

        def boom(src, dst):
            calls["n"] += 1
            if calls["n"] == 4:
                raise OSError("injected failure")
            return real_replace(src, dst)

        os.replace = boom
        skill_map.os.replace = boom
        try:
            code, _, err = self.sync(project, source)
        finally:
            os.replace = real_replace
            skill_map.os.replace = real_replace
        self.assertNotEqual(code, 0)
        self.assertIn("previous project files were restored", err)
        self.assertEqual((project / "SKILL_MAP.md").read_bytes(), before_map)
        self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), before_usage)
        self.assertFalse(list((project / ".skill-map").glob("*.bak-skill-map")))
        self.assertFalse(list(project.glob("*.bak-skill-map")))

    def test_refuses_to_write_usage_into_the_skill_source(self):
        source = self.source_with(["alpha"])
        code, _, err = self.sync(source, source)
        self.assertEqual(code, skill_map.EXIT_USAGE)
        self.assertIn("read-only", err)
        self.assertFalse((source / "SKILL_MAP.md").exists())
        self.assertFalse((source / ".skill-map").exists())


class RenderTests(SkillMapTestCase):
    def test_library_navigation_matches_generator_and_lists_every_skill(self):
        source = (REPO / "skills").resolve()
        out = self.tmp / "NAVIGATION.md"
        code, _, err = run(
            [
                "render-library",
                "--source",
                str(source),
                "--out",
                str(out),
            ]
        )
        self.assertEqual(code, 0, err)
        generated = out.read_text(encoding="utf-8")
        committed = (REPO / "NAVIGATION.md").read_text(encoding="utf-8")
        self.assertEqual(generated, committed)
        for name in SEVEN:
            self.assertIn(f"`{name}`", generated)
        mermaid = generated.split("```mermaid", 1)[1].split("```", 1)[0]
        for name in SEVEN:
            self.assertIn(name, mermaid)
        self.assertIn("文本回退", generated)
        self.assertIn("关系未知", generated)
        self.assertIn("不是每个项目都要走完", generated)
        self.assertNotIn(str(source), generated)
        for line in mermaid.splitlines():
            self.assertLess(len(line), 180, line)

    def test_render_library_refuses_to_write_inside_the_source(self):
        source = self.source_with(["alpha"])
        code, _, err = run(
            [
                "render-library",
                "--source",
                str(source),
                "--out",
                str(source / "NAVIGATION.md"),
            ]
        )
        self.assertEqual(code, skill_map.EXIT_USAGE)
        self.assertIn("skills source", err)
        self.assertFalse((source / "NAVIGATION.md").exists())


class DocsTests(unittest.TestCase):
    def test_gates_and_public_pages_stay_within_bounds(self):
        raw = (REPO / "skills" / "project-essentials" / "MANDATORY.md").read_bytes()
        normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        self.assertEqual(hashlib.sha256(normalized).hexdigest(), MANDATORY_SHA256)
        crlf = normalized.replace(b"\n", b"\r\n")
        self.assertNotEqual(hashlib.sha256(crlf).hexdigest(), MANDATORY_SHA256)
        self.assertEqual(
            hashlib.sha256(crlf.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest(),
            MANDATORY_SHA256,
        )
        text = normalized.decode("utf-8")
        for token in [f"M-{number:02d}" for number in range(1, 16)]:
            self.assertIn(token, text)
        for token in ("G0 开工门", "G1 任务完成门", "G2 合入门", "G3 发布门", "R-1", "R-2", "R-3"):
            self.assertIn(token, text)
        agents = (REPO / "skills" / "agent-constraint-docs" / "templates" / "AGENTS.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(MANDATORY_SECTION, agents)
        self.assertIn("SKILL_MAP.md", agents)
        self.assertLess(agents.count("\n"), 90)
        root_agents = (REPO / "AGENTS.md").read_text(encoding="utf-8")
        self.assertLess(len(root_agents.splitlines()), 40)
        self.assertIn("NAVIGATION.md", root_agents)
        for name in SEVEN:
            skill = (REPO / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("红线 R-1 到 R-3 不可豁免", skill)
            self.assertIn("skill-map sync", skill)
            self.assertIn("没有证据", skill)
        for readme_name in ("README.md", "README.zh-CN.md", "NAVIGATION.md", "AGENTS.md"):
            page = (REPO / readme_name).read_text(encoding="utf-8")
            self.assertNotIn("Asia/Shanghai", page)
            self.assertNotIn("14:12", page)
            self.assertNotIn("approval log", page.lower())
        self.assertIn("SKILL_MAP.md", (REPO / "README.md").read_text(encoding="utf-8"))
        self.assertIn("SKILL_MAP.md", (REPO / "README.zh-CN.md").read_text(encoding="utf-8"))
        self.assertIn("9009", agents)
        self.assertIn("py -3", agents)
        self.assertIn(MANDATORY_SECTION, agents)
        cmd = (REPO / "navigation" / "skill-map.cmd").read_bytes()
        self.assertTrue(cmd.endswith(b"\r\n"))
        self.assertNotIn(b"\n", cmd.replace(b"\r\n", b""))
        cmd_text = cmd.decode("ascii")
        self.assertIn("py -3", cmd_text)
        self.assertIn("exit /b %ERRORLEVEL%", cmd_text)
        self.assertIn("9009", cmd_text)
        self.assertNotIn("exit /b 0", cmd_text)
        wrapper = (REPO / "navigation" / "skill-map").read_text(encoding="utf-8")
        self.assertIn("python_ok py -3", wrapper)
        self.assertIn("exec ", wrapper)
        self.assertIn("9009", wrapper)


if __name__ == "__main__":
    unittest.main()
