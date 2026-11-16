#!/usr/bin/env python3
"""Fixture tests for per-project skill usage maps."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
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
        (project_a / "SKILL_MAP.md").symlink_to(project_b / "SKILL_MAP.md")
        code, _, err = self.sync(project_a, source)
        self.assertNotEqual(code, 0)
        self.assertIn("outside the project", err)
        self.assertEqual((project_b / "SKILL_MAP.md").read_bytes(), b_map)
        self.assertEqual((project_b / ".skill-map" / "usage.json").read_bytes(), b_usage)


class FailureTests(SkillMapTestCase):
    def test_missing_source_and_relative_project_do_not_write(self):
        project = self.project()
        before = list(project.iterdir())
        code, _, err = self.sync(project, self.tmp / "missing source")
        self.assertEqual(code, skill_map.EXIT_MISSING)
        self.assertIn("does not exist", err)
        self.assertEqual(list(project.iterdir()), before)
        code, _, err = run(["sync", "--project", "relative-project", "--source", "skills"], cwd=Path("/"))
        self.assertEqual(code, skill_map.EXIT_USAGE)
        self.assertIn("absolute", err)
        code, _, err = run(["sync", "--project", "relative-project", "--source", "skills"], cwd=Path("/tmp"))
        self.assertEqual(code, skill_map.EXIT_USAGE)
        self.assertIn("absolute", err)
        self.assertFalse((Path("/relative-project")).exists())
        self.assertFalse((Path("/tmp/relative-project")).exists())

    def test_missing_runtime_fails_before_any_write(self):
        project = self.project("runtime project")
        source = self.source_with(["alpha"])
        empty_path = self.tmp / "empty-path"
        empty_path.mkdir()
        env = os.environ.copy()
        env["PATH"] = str(empty_path)
        completed = subprocess.run(
            [
                str(REPO / "navigation" / "skill-map"),
                "sync",
                "--project",
                str(project),
                "--source",
                str(source),
            ],
            cwd="/",
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 127)
        self.assertIn("python3 was not found", completed.stderr)
        self.assertEqual(list(project.iterdir()), [])
        self.assertFalse((source / "SKILL_MAP.md").exists())

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
        skill_file.chmod(0)
        try:
            code, _, err = self.sync(project, source)
            self.assertEqual(code, skill_map.EXIT_UNREADABLE, err)
            self.assertIn("cannot read", err)
            self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), usage)
            self.assertEqual((project / "SKILL_MAP.md").read_bytes(), view)
        finally:
            skill_file.chmod(stat.S_IRUSR | stat.S_IWUSR)

        dangling = source / "gamma"
        dangling.mkdir()
        (dangling / "SKILL.md").symlink_to(source / "no-such-skill.md")
        code, _, err = self.sync(project, source)
        self.assertEqual(code, skill_map.EXIT_UNREADABLE, err)
        self.assertIn("dangling symlink", err)
        self.assertEqual((project / ".skill-map" / "usage.json").read_bytes(), usage)
        shutil.rmtree(dangling)

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

        usage_path.chmod(0)
        try:
            code, _, err = self.sync(project, source)
            self.assertEqual(code, skill_map.EXIT_UNREADABLE, err)
            self.assertIn("cannot read", err)
            self.assertEqual((project / "SKILL_MAP.md").read_bytes(), view)
        finally:
            usage_path.chmod(stat.S_IRUSR | stat.S_IWUSR)

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
                "import fcntl, os, sys, time; fd=os.open(sys.argv[1], os.O_RDONLY); fcntl.flock(fd, fcntl.LOCK_EX); time.sleep(30)",
                str(project),
            ]
        )
        acquired = False
        for _ in range(50):
            probe = os.open(project, os.O_RDONLY)
            try:
                import fcntl

                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(probe, fcntl.LOCK_UN)
            except BlockingIOError:
                acquired = True
                break
            finally:
                os.close(probe)
            time.sleep(0.05)
        self.assertTrue(acquired, "lock holder did not start")
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
        mandatory = (REPO / "skills" / "project-essentials" / "MANDATORY.md").read_bytes()
        self.assertEqual(hashlib.sha256(mandatory).hexdigest(), MANDATORY_SHA256)
        text = mandatory.decode("utf-8")
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


if __name__ == "__main__":
    unittest.main()
