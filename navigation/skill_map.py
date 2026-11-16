#!/usr/bin/env python3
"""Discover skills and keep a per-project usage map.

The skills source and the catalog are read-only. Usage status, notes,
evidence, and history are written only under the explicit project root:
SKILL_MAP.md and .skill-map/usage.json.

This process does not start a daemon, does not use the network, and does
not execute skill files. It only reads them as text.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 3
EXIT_UNREADABLE = 4
EXIT_MALFORMED = 5
EXIT_LOCK = 6
EXIT_CONFLICT = 7

STATUSES = (
    "unverified",
    "using",
    "used",
    "next",
    "conditional",
    "inapplicable",
)
NEEDS_EVIDENCE = {"using", "used"}
NEEDS_REASON = {"next", "conditional", "inapplicable"}
AVAILABILITY = ("available", "unavailable")
RELATION_KINDS = ("typical-next", "conditional", "only-when", "repeatable")
ROLES = (
    "chain",
    "chain-repeatable",
    "cross-cutting",
    "conditional-repeatable",
    "only-when",
    "unknown",
)

ROLE_LABELS = {
    "chain": ("Typical chain step", "常见顺序中的一步"),
    "chain-repeatable": (
        "Typical chain step, repeatable per task",
        "常见顺序中的一步，每个任务可再用",
    ),
    "cross-cutting": (
        "Cross-cutting, not a station",
        "贯穿各项，不是顺序里的一站",
    ),
    "conditional-repeatable": (
        "Conditional and repeatable",
        "有条件才用，而且可以重复用",
    ),
    "only-when": ("Only when this kind of work", "只有这类工作才用"),
    "unknown": ("Relationship unknown", "关系未知"),
}

STATUS_LABELS = {
    "unverified": "未核实",
    "using": "正在用",
    "used": "用过",
    "next": "下一步",
    "conditional": "有条件",
    "inapplicable": "不适用",
}

SCRIPT_DIR = Path(__file__).resolve().parent


class SkillMapError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dumps(data: object) -> bytes:
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    return (text + "\n").encode("utf-8")


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def same_or_within(child: Path, parent: Path) -> bool:
    try:
        return child.resolve() == parent.resolve() or is_within(child, parent)
    except OSError:
        return False


def unquote(raw: str) -> str:
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {"'", '"'}:
        return raw[1:-1]
    return raw


def collapse(text: str) -> str:
    return " ".join(text.split())


def excerpt(text: str, limit: int = 280) -> str:
    text = collapse(text)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut or text[:limit]) + "…"


def cell(text: str) -> str:
    return collapse(text).replace("|", "\\|")


def mermaid_id(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not safe or safe[0].isdigit():
        safe = "n_" + safe
    return "s_" + safe


def mermaid_label(text: str) -> str:
    cleaned = text.replace("\r", " ").replace("\n", " ")
    cleaned = cleaned.replace('"', "#quot;").replace("[", "(").replace("]", ")")
    return cleaned


def parse_frontmatter(text: str, path: Path) -> dict:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed skill metadata: {path}: missing opening ---",
        )
    end = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = index
            break
    if end is None:
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed skill metadata: {path}: missing closing ---",
        )
    body = lines[1:end]
    data: dict[str, str] = {}
    index = 0
    while index < len(body):
        line = body[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line[:1].isspace():
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed skill metadata: {path}: indented line outside a value",
            )
        if ":" not in line:
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed skill metadata: {path}: expected key: value",
            )
        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()
        if not key:
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed skill metadata: {path}: empty key",
            )
        if raw in {">", ">-", "|", "|-"}:
            index += 1
            chunks: list[str] = []
            while index < len(body):
                chunk = body[index]
                if chunk.startswith((" ", "\t")):
                    chunks.append(chunk.strip())
                    index += 1
                elif chunk.strip() == "":
                    chunks.append("")
                    index += 1
                else:
                    break
            if raw.startswith(">"):
                data[key] = collapse(" ".join(chunks))
            else:
                data[key] = "\n".join(chunks).strip()
        elif raw == "":
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed skill metadata: {path}: unsupported nested value for {key}",
            )
        else:
            data[key] = unquote(raw)
            index += 1
    if not data.get("name", "").strip():
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed skill metadata: {path}: missing name",
        )
    if not data.get("description", "").strip():
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed skill metadata: {path}: missing description",
        )
    return data


def read_text(path: Path, label: str) -> str:
    try:
        if path.is_symlink() and not path.exists():
            raise SkillMapError(
                EXIT_UNREADABLE,
                f"cannot read {label}: {path}: dangling symlink",
            )
        return path.read_text(encoding="utf-8")
    except SkillMapError:
        raise
    except UnicodeError as exc:
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed {label}: {path}: not utf-8 ({exc})",
        ) from exc
    except OSError as exc:
        raise SkillMapError(
            EXIT_UNREADABLE,
            f"cannot read {label}: {path}: {exc.strerror or exc}",
        ) from exc


def discover_skills(source: Path) -> dict[str, dict]:
    if not source.exists():
        raise SkillMapError(
            EXIT_MISSING,
            f"skills source does not exist: {source}",
        )
    if not source.is_dir():
        raise SkillMapError(
            EXIT_MISSING,
            f"skills source is not a directory: {source}",
        )
    try:
        children = sorted(source.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise SkillMapError(
            EXIT_UNREADABLE,
            f"cannot read skills source: {source}: {exc.strerror or exc}",
        ) from exc
    found: dict[str, dict] = {}
    for child in children:
        try:
            is_dir = child.is_dir()
        except OSError as exc:
            raise SkillMapError(
                EXIT_UNREADABLE,
                f"cannot read skills source entry: {child}: {exc.strerror or exc}",
            ) from exc
        if not is_dir:
            continue
        skill_file = child / "SKILL.md"
        if skill_file.is_symlink() and not skill_file.exists():
            raise SkillMapError(
                EXIT_UNREADABLE,
                f"cannot read skill file: {skill_file}: dangling symlink",
            )
        if not skill_file.exists():
            continue
        meta = parse_frontmatter(read_text(skill_file, "skill file"), skill_file)
        name = meta["name"].strip()
        if name != child.name:
            raise SkillMapError(
                EXIT_MALFORMED,
                "malformed skill metadata: "
                f"{skill_file}: name {name!r} does not match directory {child.name!r}",
            )
        if name in found:
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed skill metadata: duplicate skill name {name}",
            )
        found[name] = {
            "name": name,
            "description": collapse(meta["description"]),
            "path": f"{name}/SKILL.md",
        }
    return found


def empty_catalog() -> dict:
    return {"version": 1, "groups": [], "relations": [], "skills": {}}


def load_catalog(path: Path | None) -> dict:
    if path is None:
        return empty_catalog()
    try:
        data = json.loads(read_text(path, "catalog"))
    except SkillMapError:
        raise
    except json.JSONDecodeError as exc:
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed catalog: {path}: {exc}",
        ) from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed catalog: {path}: version must be 1",
        )
    groups = data.get("groups")
    skills = data.get("skills")
    relations = data.get("relations")
    if not isinstance(groups, list) or not isinstance(skills, dict) or not isinstance(relations, list):
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed catalog: {path}: groups, skills, and relations have the wrong type",
        )
    seen: set[str] = set()
    for group in groups:
        if not isinstance(group, dict):
            raise SkillMapError(EXIT_MALFORMED, f"malformed catalog: {path}: group is not an object")
        for field in ("id", "title", "title_zh", "skills"):
            if field not in group:
                raise SkillMapError(
                    EXIT_MALFORMED,
                    f"malformed catalog: {path}: group missing {field}",
                )
        if not isinstance(group["skills"], list) or not all(isinstance(item, str) for item in group["skills"]):
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed catalog: {path}: group skills must be strings",
            )
        for name in group["skills"]:
            if name in seen:
                raise SkillMapError(
                    EXIT_MALFORMED,
                    f"malformed catalog: {path}: skill {name} is in more than one group",
                )
            seen.add(name)
    for name, info in skills.items():
        if not isinstance(name, str) or not isinstance(info, dict):
            raise SkillMapError(EXIT_MALFORMED, f"malformed catalog: {path}: bad skill entry")
        if info.get("role") not in ROLES or not isinstance(info.get("source"), str):
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed catalog: {path}: skill {name} needs a known role and source",
            )
        if name not in seen:
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed catalog: {path}: skill {name} has a role but is not in a group",
            )
    for name in seen:
        if name not in skills:
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed catalog: {path}: grouped skill {name} has no role entry",
            )
    for relation in relations:
        if not isinstance(relation, dict):
            raise SkillMapError(EXIT_MALFORMED, f"malformed catalog: {path}: relation is not an object")
        for field in ("from", "to", "kind", "when", "source"):
            if not isinstance(relation.get(field), str) or not relation[field].strip():
                raise SkillMapError(
                    EXIT_MALFORMED,
                    f"malformed catalog: {path}: relation missing {field}",
                )
        if relation["kind"] not in RELATION_KINDS:
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed catalog: {path}: unknown relation kind {relation['kind']}",
            )
        if relation["from"] not in skills or relation["to"] not in skills:
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed catalog: {path}: relation endpoints must be catalog skills",
            )
    return data


def resolve_catalog_path(explicit: str | None, source: Path) -> Path | None:
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            raise SkillMapError(
                EXIT_USAGE,
                "catalog path must be absolute so it does not depend on the current working directory: "
                + explicit,
            )
        resolved = path.resolve(strict=False)
        if not resolved.is_file():
            raise SkillMapError(EXIT_MISSING, f"catalog does not exist: {resolved}")
        return resolved
    for candidate in (source / "catalog.json", SCRIPT_DIR / "catalog.json"):
        if candidate.is_file():
            return candidate.resolve()
    return None


def require_project(raw: str) -> Path:
    if not raw or raw == ".":
        raise SkillMapError(
            EXIT_USAGE,
            "project root is required and must be an explicit absolute path. "
            "This command does not guess a project from the current working directory.",
        )
    path = Path(raw)
    if not path.is_absolute():
        raise SkillMapError(
            EXIT_USAGE,
            "project root must be an absolute path. A relative path is ambiguous because it "
            f"depends on the current working directory. Got: {raw}",
        )
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise SkillMapError(EXIT_MISSING, f"project root does not exist: {path}") from exc
    except OSError as exc:
        raise SkillMapError(
            EXIT_UNREADABLE,
            f"cannot read project root: {path}: {exc.strerror or exc}",
        ) from exc
    if not resolved.is_dir():
        raise SkillMapError(EXIT_USAGE, f"project root is not a directory: {resolved}")
    return resolved


def resolve_source(raw: str, project: Path) -> Path:
    if not raw:
        raise SkillMapError(EXIT_USAGE, "skills source path is required")
    path = Path(raw)
    if raw.startswith("~"):
        raise SkillMapError(
            EXIT_USAGE,
            "skills source must be absolute, or relative to the project root. Home shortcuts are not expanded.",
        )
    if path.is_absolute():
        return path.resolve(strict=False)
    return (project / path).resolve(strict=False)


def require_absolute_output(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        raise SkillMapError(
            EXIT_USAGE,
            "output path must be absolute so it does not depend on the current working directory: "
            + raw,
        )
    return path.resolve(strict=False)


def refuse_library_project(project: Path, source: Path) -> None:
    if same_or_within(project, source):
        raise SkillMapError(
            EXIT_USAGE,
            "refusing to write usage state into the skills source. "
            "The shared library is read-only for usage. "
            "Pass the consuming project's own root as --project.",
        )


def assert_write_stays_inside(project: Path, target: Path) -> None:
    real_project = project.resolve()
    if target.is_symlink() or target.exists():
        real = target.resolve()
        if not is_within(real, real_project):
            raise SkillMapError(
                EXIT_USAGE,
                f"refusing to write {target}: it resolves outside the project root ({real})",
            )
    ancestor = target.parent
    while not ancestor.exists():
        if ancestor == ancestor.parent:
            break
        ancestor = ancestor.parent
    real_ancestor = ancestor.resolve()
    if real_ancestor != real_project and not is_within(real_ancestor, real_project):
        raise SkillMapError(
            EXIT_USAGE,
            f"refusing to write {target}: its directory resolves outside the project root ({real_ancestor})",
        )


@contextmanager
def project_lock(project: Path):
    try:
        fd = os.open(project, os.O_RDONLY)
    except OSError as exc:
        raise SkillMapError(
            EXIT_UNREADABLE,
            f"cannot lock project root: {project}: {exc.strerror or exc}",
        ) from exc
    try:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(fd)
        raise SkillMapError(
            EXIT_LOCK,
            "another skill-map update holds the lock on this project. "
            "Rerun after it finishes. Concurrent updates are not merged, and this command "
            "does not write to any other project or to the skills source.",
        ) from exc
    except OSError as exc:
        os.close(fd)
        raise SkillMapError(
            EXIT_UNREADABLE,
            f"cannot lock project root: {project}: {exc.strerror or exc}",
        ) from exc
    try:
        yield
    finally:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def usage_path(project: Path) -> Path:
    return project / ".skill-map" / "usage.json"


def map_path(project: Path) -> Path:
    return project / "SKILL_MAP.md"


def commit_outputs(files: list[tuple[Path, bytes]]) -> bool:
    """Atomically replace files. On failure, restore files already replaced."""
    if files and all(
        path.exists() and not path.is_symlink() and path.read_bytes() == data for path, data in files
    ):
        return False
    temps: list[tuple[Path, str]] = []
    replaced: list[tuple[Path, Path | None]] = []
    created_dirs: list[Path] = []
    try:
        for path, data in files:
            parent = path.parent
            if not parent.exists():
                parent.mkdir(parents=True)
                created_dirs.append(parent)
            fd, tmpname = tempfile.mkstemp(prefix="." + path.name + ".", dir=str(parent))
            try:
                os.write(fd, data)
                os.fsync(fd)
            finally:
                os.close(fd)
            temps.append((path, tmpname))
        for path, tmpname in temps:
            backup = None
            try:
                if path.exists() or path.is_symlink():
                    backup = path.with_name(path.name + ".bak-skill-map")
                    if backup.exists() or backup.is_symlink():
                        backup.unlink()
                    os.replace(path, backup)
                os.replace(tmpname, path)
            except Exception:
                if backup is not None and (backup.exists() or backup.is_symlink()) and not (
                    path.exists() or path.is_symlink()
                ):
                    os.replace(backup, path)
                raise
            replaced.append((path, backup))
        for _path, backup in replaced:
            if backup is not None and (backup.exists() or backup.is_symlink()):
                backup.unlink()
        return True
    except SkillMapError:
        raise
    except Exception as exc:
        for path, backup in reversed(replaced):
            if backup is not None and (backup.exists() or backup.is_symlink()):
                if path.exists() or path.is_symlink():
                    path.unlink()
                os.replace(backup, path)
            elif backup is None and (path.exists() or path.is_symlink()):
                path.unlink()
        for _path, tmpname in temps:
            if os.path.exists(tmpname):
                os.unlink(tmpname)
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise SkillMapError(
            EXIT_UNREADABLE,
            "update failed before completion; previous project files were restored and no other "
            f"project was modified: {exc}",
        ) from exc


def fresh_state(project: Path, source: Path) -> dict:
    return {
        "project_root": str(project),
        "revision": 0,
        "skills": {},
        "source": str(source),
        "source_history": [],
        "version": 1,
    }


def validate_record(name: str, record: object, path: Path) -> dict:
    if not isinstance(record, dict):
        raise SkillMapError(EXIT_MALFORMED, f"malformed usage map: {path}: skill {name} is not an object")
    required = {
        "availability": str,
        "description": str,
        "evidence": list,
        "history": list,
        "name": str,
        "notes": str,
        "reason": str,
        "status": str,
    }
    for key, kind in required.items():
        if key not in record or not isinstance(record[key], kind):
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed usage map: {path}: skill {name} is missing or has a bad {key}",
            )
    if record["status"] not in STATUSES:
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed usage map: {path}: skill {name} has unknown status {record['status']!r}",
        )
    if record["availability"] not in AVAILABILITY:
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed usage map: {path}: skill {name} has unknown availability",
        )
    if record["name"] != name:
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed usage map: {path}: skill key {name} does not match name {record['name']}",
        )
    if not all(isinstance(item, str) for item in record["evidence"]):
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed usage map: {path}: skill {name} evidence must be strings",
        )
    if not all(isinstance(item, dict) and isinstance(item.get("event"), str) and isinstance(item.get("at"), str) for item in record["history"]):
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed usage map: {path}: skill {name} history is malformed",
        )
    if record["status"] in NEEDS_EVIDENCE and not any(item.strip() for item in record["evidence"]):
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed usage map: {path}: skill {name} is {record['status']} without evidence. "
            "Reading a skill is not evidence. Refusing to rewrite the map.",
        )
    if record["status"] in NEEDS_REASON and not record["reason"].strip():
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed usage map: {path}: skill {name} is {record['status']} without a reason. "
            "Refusing to rewrite the map.",
        )
    return record


def validate_state(data: object, path: Path, project: Path | None) -> dict:
    if not isinstance(data, dict) or data.get("version") != 1:
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed usage map: {path}: version must be 1. Refusing to rewrite it.",
        )
    for key, kind in (
        ("project_root", str),
        ("revision", int),
        ("skills", dict),
        ("source", str),
        ("source_history", list),
    ):
        if not isinstance(data.get(key), kind):
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed usage map: {path}: missing or bad {key}. Refusing to rewrite it.",
            )
    if isinstance(data["revision"], bool) or data["revision"] < 0:
        raise SkillMapError(EXIT_MALFORMED, f"malformed usage map: {path}: bad revision")
    for item in data["source_history"]:
        if not isinstance(item, dict) or not isinstance(item.get("event"), str):
            raise SkillMapError(EXIT_MALFORMED, f"malformed usage map: {path}: bad source history")
    for name, record in data["skills"].items():
        validate_record(name, record, path)
    if project is not None:
        try:
            recorded = Path(data["project_root"]).resolve(strict=False)
        except OSError as exc:
            raise SkillMapError(
                EXIT_MALFORMED,
                f"malformed usage map: {path}: bad project_root ({exc})",
            ) from exc
        if recorded != project.resolve():
            raise SkillMapError(
                EXIT_CONFLICT,
                "usage state belongs to a different project root "
                f"({data['project_root']}). Refusing to mix histories or write this project's "
                "status into that map.",
            )
    return data


def load_state(project: Path) -> dict | None:
    path = usage_path(project)
    view = map_path(project)
    if path.exists() or path.is_symlink():
        assert_write_stays_inside(project, path)
    if view.exists() or view.is_symlink():
        assert_write_stays_inside(project, view)
        read_text(view, "usage map")
    if not path.exists():
        if view.exists():
            raise SkillMapError(
                EXIT_CONFLICT,
                f"{view} exists but {path} is missing. Refusing to invent new usage state over an existing map.",
            )
        return None
    try:
        data = json.loads(read_text(path, "usage map"))
    except json.JSONDecodeError as exc:
        raise SkillMapError(
            EXIT_MALFORMED,
            f"malformed usage map: {path}: {exc}. Refusing to rewrite it.",
        ) from exc
    return validate_state(data, path, project)


def blank_skill(name: str, description: str, at: str) -> dict:
    return {
        "availability": "available",
        "description": description,
        "evidence": [],
        "history": [{"at": at, "event": "discovered", "status": "unverified"}],
        "name": name,
        "notes": "",
        "reason": "",
        "status": "unverified",
    }


def merge_discovered(state: dict, discovered: dict[str, dict], source: Path, at: str) -> bool:
    changed = False
    source_text = str(source)
    if state["source"] != source_text:
        state["source_history"].append(
            {"at": at, "event": "source-changed", "from": state["source"], "to": source_text}
        )
        state["source"] = source_text
        changed = True
    for name in sorted(discovered):
        meta = discovered[name]
        current = state["skills"].get(name)
        if current is None:
            state["skills"][name] = blank_skill(name, meta["description"], at)
            changed = True
            continue
        if current["availability"] != "available":
            current["availability"] = "available"
            current["history"].append(
                {"at": at, "event": "source-returned", "status": current["status"]}
            )
            changed = True
        if current["description"] != meta["description"]:
            current["description"] = meta["description"]
            changed = True
    for name, current in state["skills"].items():
        if name in discovered or current["availability"] == "unavailable":
            continue
        current["availability"] = "unavailable"
        current["history"].append(
            {"at": at, "event": "source-missing", "status": current["status"]}
        )
        changed = True
    if changed:
        state["revision"] = int(state["revision"]) + 1
    return changed


def role_of(catalog: dict, name: str) -> str:
    info = catalog.get("skills", {}).get(name)
    if isinstance(info, dict) and info.get("role") in ROLE_LABELS:
        return info["role"]
    return "unknown"


def present_names(state: dict) -> set[str]:
    return set(state["skills"])


def display_groups(catalog: dict, names: set[str]) -> list[tuple[dict, list[str]]]:
    grouped: list[tuple[dict, list[str]]] = []
    seen: set[str] = set()
    for group in catalog.get("groups", []):
        members = [name for name in group["skills"] if name in names]
        seen.update(members)
        if members:
            grouped.append((group, members))
    unknown = sorted(name for name in names if name not in seen)
    if unknown:
        grouped.append(
            (
                {
                    "id": "unknown",
                    "title": "Relationship unknown",
                    "title_zh": "关系未知",
                    "skills": unknown,
                },
                unknown,
            )
        )
    return grouped


def chain_edges(catalog: dict, names: set[str]) -> list[tuple[str, str]]:
    edges = []
    for group in catalog.get("groups", []):
        if group.get("id") != "chain":
            continue
        members = [name for name in group["skills"] if name in names]
        for left, right in zip(members, members[1:]):
            if any(
                item["from"] == left and item["to"] == right and item["kind"] == "typical-next"
                for item in catalog.get("relations", [])
            ):
                edges.append((left, right))
    return edges


def hint_edges(catalog: dict, names: set[str]) -> list[dict]:
    """One dotted incoming hint per non-chain skill, so the picture stays readable."""
    chain_members = set()
    for group in catalog.get("groups", []):
        if group.get("id") == "chain":
            chain_members.update(name for name in group["skills"] if name in names)
    chosen = []
    seen_targets = set()
    for relation in catalog.get("relations", []):
        target = relation["to"]
        if target in chain_members or target not in names or relation["from"] not in names:
            continue
        if target in seen_targets:
            continue
        if relation["kind"] not in {"conditional", "only-when", "repeatable"}:
            continue
        chosen.append(relation)
        seen_targets.add(target)
    return chosen


def status_class(record: dict) -> str:
    if record["availability"] == "unavailable":
        return "unavailable"
    return {
        "using": "current",
        "next": "next",
        "used": "used",
        "unverified": "unverified",
    }.get(record["status"], "other")


def node_label(name: str, record: dict | None, catalog: dict, with_status: bool) -> str:
    if with_status and record is not None:
        label = STATUS_LABELS[record["status"]]
        text = f"{name}<br/>{label} ({record['status']})"
        if record["availability"] == "unavailable":
            text += "<br/>源已不在 (unavailable)"
        return text
    _en, zh = ROLE_LABELS[role_of(catalog, name)]
    return f"{name}<br/>{zh}"


def render_mermaid(state: dict | None, catalog: dict, with_status: bool) -> str:
    names = set(state["skills"]) if state is not None else set(catalog.get("skills", {}))
    if state is not None:
        names = set(state["skills"])
    lines = ["flowchart TB"]
    if with_status:
        lines.extend(
            [
                "  classDef current fill:#ffe08a,stroke:#8a5a00,color:#111111;",
                "  classDef next fill:#d6ecff,stroke:#1d4e89,color:#111111;",
                "  classDef used fill:#e7f6e7,stroke:#1e7a32,color:#111111;",
                "  classDef unverified fill:#f7f7f7,stroke:#666666,color:#111111;",
                "  classDef other fill:#ffffff,stroke:#444444,color:#111111;",
                "  classDef unavailable fill:#fde8e8,stroke:#8a1f1f,color:#111111,stroke-dasharray: 4 3;",
            ]
        )
    groups = display_groups(catalog, names)
    for group, members in groups:
        title = mermaid_label(group["title_zh"])
        lines.append(f'  subgraph {mermaid_id("group_" + group["id"])}["{title}"]')
        if group["id"] == "chain":
            lines.append("    direction LR")
        for name in members:
            record = None if state is None else state["skills"][name]
            label = mermaid_label(node_label(name, record, catalog, with_status))
            if with_status and record is not None:
                lines.append(
                    f'    {mermaid_id(name)}["{label}"]:::{status_class(record)}'
                )
            else:
                lines.append(f'    {mermaid_id(name)}["{label}"]')
        lines.append("  end")
    for left, right in chain_edges(catalog, names):
        lines.append(f"  {mermaid_id(left)} --> {mermaid_id(right)}")
    for relation in hint_edges(catalog, names):
        kind = mermaid_label(relation["kind"])
        lines.append(
            f'  {mermaid_id(relation["from"])} -. "{kind}" .-> {mermaid_id(relation["to"])}'
        )
    if not groups:
        lines.append('  empty["no skills discovered"]')
    return "\n".join(lines)


def relation_rows(catalog: dict, names: set[str]) -> list[str]:
    rows = []
    for relation in catalog.get("relations", []):
        if relation["from"] not in names and relation["to"] not in names:
            continue
        rows.append(
            "| {from_name} | {to_name} | {kind} | {when} | {source} |".format(
                from_name=cell(relation["from"]),
                to_name=cell(relation["to"]),
                kind=cell(relation["kind"]),
                when=cell(relation["when"]),
                source=cell(relation["source"]),
            )
        )
    return rows


def names_with_status(state: dict, status: str) -> list[str]:
    return sorted(name for name, record in state["skills"].items() if record["status"] == status)


def sentence_list(names: list[str]) -> str:
    return ", ".join(f"`{name}`" for name in names) if names else "（无 / none）"


def render_project_map(state: dict, catalog: dict) -> str:
    current = names_with_status(state, "using")
    upcoming = names_with_status(state, "next")
    unverified = names_with_status(state, "unverified")
    unknown = sorted(name for name in state["skills"] if role_of(catalog, name) == "unknown")
    missing = sorted(
        name for name, record in state["skills"].items() if record["availability"] == "unavailable"
    )
    next_bits = []
    for name in upcoming:
        reason = state["skills"][name]["reason"].strip() or "（没有填写理由）"
        next_bits.append(f"`{name}`：{reason}")
    next_text = "；".join(next_bits) if next_bits else "（无 / none）"
    lines = [
        "# Skills usage map / Skills 使用地图",
        "",
        "This file records which skills **this project** has used. It is not feature progress and not a system architecture.",
        "本文件只记录**这个项目**用过哪些 Skill。它不是功能进度，也不是系统架构。",
        "",
        f"- Project root / 项目根目录：`{state['project_root']}`",
        f"- Skills source / Skills 目录：`{state['source']}`",
        "- Usage record / 使用记录：`.skill-map/usage.json`（只属于这个项目）",
        f"- Revision / 修订号：{state['revision']}",
        "",
        "The shared skill library is not modified by this file. Reading or loading a skill only proves that it was read. Without evidence, the status stays `unverified`.",
        "同步不会修改共享技能库。只读过 Skill 只说明读过了。没有证据，状态保持 `unverified`（未核实）。",
        "",
        "Edit notes, status, and evidence with `navigation/skill-map set`, or edit `.skill-map/usage.json` and keep this file's fields valid. The next sync replaces this view and keeps that record. Do not delete a skill block to hide history.",
        "要改备注、状态和证据，用 `navigation/skill-map set`，或改 `.skill-map/usage.json` 并保持字段有效。下次 sync 会重写这份视图，并保留那份记录。不要靠删掉一节来清掉历史。",
        "",
        "## Current and next / 当前和下一步",
        "",
        f"- Current / 正在用：{sentence_list(current)}",
        f"- Next / 下一步：{next_text}",
        f"- Unverified / 未核实：{sentence_list(unverified)}",
        f"- Relationship unknown / 关系未知：{sentence_list(unknown)}",
        f"- Source unavailable, history kept / 源已不在，历史仍在：{sentence_list(missing)}",
        "",
        "Text fallback / 文本回退：看不清下面的图时，以这几句为准。",
        f"当前正在用 {sentence_list(current)}。",
        f"下一步是 {next_text}。",
        f"未核实的是 {sentence_list(unverified)}。",
        f"关系未知的是 {sentence_list(unknown)}。",
        f"目录里已经没有、但历史还留着的是 {sentence_list(missing)}。",
        "",
        "Diagram colors, when the picture renders: 正在用 is the `current` style (amber), 下一步 is the `next` style (blue), 用过 is green, 未核实 is gray, and a skill whose source disappeared has a dashed red border. Several skills may be 正在用 at the same time.",
        "",
        "## Map / 地图",
        "",
        "```mermaid",
        render_mermaid(state, catalog, with_status=True),
        "```",
        "",
        "The solid arrows are the typical chain only. Dotted arrows are one conditional or only-when hint per skill, chosen so the picture stays readable. Every recorded relation is in the table below. Unknown skills have no invented arrow.",
        "实线只表示常见顺序。虚线每个 Skill 最多一条，用来提示「有条件」或「只有这时才用」，避免图线缠在一起。全部关系见下面的表。关系未知的 Skill 不会被画上编造的箭头。",
        "",
        "## Text fallback / 文本地图",
        "",
        "| Skill | Status | Availability | Role | Evidence | Reason | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name in sorted(state["skills"]):
        record = state["skills"][name]
        role = role_of(catalog, name)
        _en, zh = ROLE_LABELS[role]
        evidence = "; ".join(record["evidence"]) if record["evidence"] else "（无证据 / no evidence）"
        lines.append(
            "| `{name}` | {status_zh} ({status}) | {availability} | {role} | {evidence} | {reason} | {notes} |".format(
                name=name,
                status_zh=STATUS_LABELS[record["status"]],
                status=record["status"],
                availability=record["availability"],
                role=cell(f"{zh} ({role})"),
                evidence=cell(evidence),
                reason=cell(record["reason"]) or "—",
                notes=cell(record["notes"]) or "—",
            )
        )
    lines.extend(
        [
            "",
            "## Relations / 关系提示（不是本项目的使用结论）",
            "",
            "These rows come from the skill catalog. They do not mark a skill as used, and they are not this project's next action unless a row above says `next`.",
            "这些行来自技能目录。它们不表示本项目已经用过，也不等于本项目的下一步，除非上面的状态写了 `next`。",
            "",
            "| From | To | Kind | When | Source |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    rows = relation_rows(catalog, set(state["skills"]))
    lines.extend(rows or ["| — | — | — | 没有已知关系 / no known relations | — |"])
    lines.extend(["", "## Evidence and history / 证据和历史", ""])
    lines.append(
        "History stays when a skill disappears from the source directory. A later sync marks it unavailable and does not delete these entries."
    )
    lines.append("Skill 从目录里消失以后，历史仍留在这里。之后的 sync 只把它标成源已不在，不删除这些记录。")
    lines.append("")
    for name in sorted(state["skills"]):
        record = state["skills"][name]
        lines.append(f"### `{name}`")
        lines.append("")
        lines.append(f"- When / 什么时候用：{excerpt(record['description'], 360)}")
        lines.append(f"- Status / 状态：{STATUS_LABELS[record['status']]} ({record['status']})")
        lines.append(f"- Availability / 是否还在目录：{record['availability']}")
        lines.append(f"- Reason / 理由：{record['reason'] or '—'}")
        lines.append(f"- Notes / 备注：{record['notes'] or '—'}")
        if record["evidence"]:
            lines.append("- Evidence / 证据：")
            for item in record["evidence"]:
                lines.append(f"  - {item}")
        else:
            lines.append("- Evidence / 证据：（无。没有证据就是未核实，只读过不算用过。）")
        lines.append("- History / 历史：")
        for event in record["history"]:
            parts = [event.get("at", ""), event.get("event", "")]
            for key in ("from", "to", "status"):
                if key in event:
                    parts.append(f"{key}={event[key]}")
            lines.append("- " + " ".join(parts))
        lines.append("")
    lines.append(
        "Repeated skills stay reusable. `using` may apply to more than one skill. `used` is not task completion."
    )
    lines.append("可以重复使用的 Skill 不会被用完。多个 Skill 可以同时是正在用。用过不等于任务完成。")
    lines.append("")
    return "\n".join(lines)


def library_header() -> str:
    return "\n".join(
        [
            "# Skills navigation / Skills 总导航",
            "",
            "This page is the catalog of skills in this repository: what each one is for, and how they relate. It is not a project's progress, and it is not a system architecture.",
            "这一页是本仓库的 Skill 目录：每个 Skill 做什么、它们怎么关联。它不是某个项目的进度，也不是系统架构。",
            "",
            "Usage status is not stored here. Each consuming project keeps its own `SKILL_MAP.md` and `.skill-map/usage.json` in that project's root. Two projects can share this source and still have different histories.",
            "使用状态不写在这里。每个使用方项目在自己的根目录保存 `SKILL_MAP.md` 和 `.skill-map/usage.json`。两个项目可以共用这份技能目录，历史仍然各记各的。",
            "",
            "The check does not run by itself, and there is no background process. At the start of work, the agent runs this command because the project's `AGENTS.md` tells it to. `--project` must be that project's absolute root. A relative project path is rejected so the current working directory cannot redirect the write.",
            "这条命令不会自己跑，也没有后台服务。开工时由 agent 按项目 `AGENTS.md` 里的说明来运行。`--project` 必须是那个项目根目录的绝对路径。相对的项目路径会被拒绝，避免当前工作目录把写入指到别处。",
            "",
            "```bash",
            "/absolute/path/to/agent-skills/navigation/skill-map sync \\",
            "  --project /absolute/path/to/your-project \\",
            "  --source /absolute/path/to/agent-skills/skills",
            "```",
            "",
            "`--source` may be absolute, or relative to the project root (not to the current working directory). The command reads the source and writes only `<project>/SKILL_MAP.md` and `<project>/.skill-map/usage.json`.",
            "`--source` 可以是绝对路径，或者相对项目根（不是相对当前工作目录）。命令只读技能目录，只写 `<项目>/SKILL_MAP.md` 和 `<项目>/.skill-map/usage.json`。",
            "",
            "On failure it prints the reason to stderr, exits non-zero, and leaves the previous map in place. A missing source, an unreadable file, or a malformed map, catalog, or skill file does not partially update the project. New skills are added as `unverified`. A skill removed from the source stays in the map as unavailable, with its notes, evidence, and history. Relationships that are not in `navigation/catalog.json` stay unknown. Setup, exit codes, and conflicts: [navigation/README.md](navigation/README.md).",
            "失败时把原因写到 stderr，以非 0 退出，并留下原来的地图。技能目录不存在、文件读不了，或地图、目录、技能文件格式坏了，都不会把项目改到一半。新 Skill 以 `unverified`（未核实）加入。从目录里删掉的 Skill 仍留在地图里，标成源已不在，备注、证据和历史都还在。`navigation/catalog.json` 里没有的关系保持未知。安装、退出码和冲突的说明见 [navigation/README.md](navigation/README.md)。",
            "",
            "Current-location highlighting (正在用 / 下一步) lives in the project's `SKILL_MAP.md`, not on this page. The picture below has no \"you are here\" mark.",
            "「正在用 / 下一步」的高亮在项目自己的 `SKILL_MAP.md` 里，不在这一页。下面这张图没有「你在这里」的标记。",
            "",
            "Regenerate this page after adding a skill or a relation:",
            "加了 Skill 或关系之后，重新生成这一页：",
            "",
            "```bash",
            "navigation/skill-map render-library \\",
            "  --source /absolute/path/to/agent-skills/skills \\",
            "  --out /absolute/path/to/agent-skills/NAVIGATION.md",
            "```",
            "",
            "Do not hand-edit the generated lists below. Change `navigation/catalog.json` or the skill folder, then run the command again.",
            "不要手改下面生成的列表。改 `navigation/catalog.json` 或 Skill 文件夹，然后重新运行上面的命令。",
            "",
        ]
    )


def render_library(discovered: dict[str, dict], catalog: dict, source: Path) -> str:
    names = set(discovered)
    unknown = sorted(name for name in names if role_of(catalog, name) == "unknown")
    lines = [
        library_header().rstrip(),
        "",
        "## Map / 地图",
        "",
        "```mermaid",
        render_mermaid(_library_state(discovered), catalog, with_status=False),
        "```",
        "",
        "Text fallback / 文本回退：看不清图时读下面的句子和表。实线只连接常见顺序里相邻、且目录里写了 typical-next 的 Skill。没有把七个 Skill 排成必经站。有条件的、可重复的、以及只有特定 agent 才用的，分开画。关系未知的 Skill 单独成组，不给它编造箭头。",
        "",
        _chain_sentence(catalog, names),
        "",
        f"Relationship unknown / 关系未知：{sentence_list(unknown)}。",
        "",
        "## Skills / 技能",
        "",
        "| Skill | Role | When the description says to use it | File |",
        "| --- | --- | --- | --- |",
    ]
    order = []
    seen = set()
    for _group, members in display_groups(catalog, names):
        for name in members:
            if name not in seen:
                order.append(name)
                seen.add(name)
    for name in order:
        meta = discovered[name]
        role = role_of(catalog, name)
        _en, zh = ROLE_LABELS[role]
        lines.append(
            f"| `{name}` | {cell(zh + ' (' + role + ')')} | {cell(excerpt(meta['description']))} | `{name}/SKILL.md` |"
        )
    lines.extend(
        [
            "",
            "## Relations / 关系",
            "",
            "A relation is a hint from the skill text cited in Source. It is not a usage record, and it does not mean every project takes that step.",
            "关系是技能正文里的提示，出处写在 Source。它不是使用记录，也不表示每个项目都要走这一步。",
            "",
            "| From | To | Kind | When | Source |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(relation_rows(catalog, names) or ["| — | — | — | 没有已知关系 / no known relations | — |"])
    lines.extend(
        [
            "",
            "## What this scan saw / 这次扫到的目录",
            "",
            f"- Skill count / Skill 数量：{len(discovered)}",
            f"- Source label / 来源：`{source.name}` (the directory passed to render-library; this file does not store a machine-specific path)",
            "",
            "Skills present in this scan:",
            "",
        ]
    )
    for name in sorted(discovered):
        lines.append(f"- `{name}`")
    if not discovered:
        lines.append("- （无 / none）")
    lines.append("")
    return "\n".join(lines)


def _library_state(discovered: dict[str, dict]) -> dict:
    """A display-only state so group placement includes discovered skills.

    Labels ignore status because render_mermaid is called with with_status=False.
    The blank records are not written to a project.
    """
    return {
        "skills": {
            name: blank_skill(name, meta["description"], "")
            for name, meta in discovered.items()
        }
    }


def _chain_sentence(catalog: dict, names: set[str]) -> str:
    members = []
    for group in catalog.get("groups", []):
        if group.get("id") == "chain":
            members = [name for name in group["skills"] if name in names]
    if not members:
        return "Typical chain / 常见顺序：（这次扫描里没有 / none in this scan）。"
    joined = " → ".join(f"`{name}`" for name in members)
    return (
        "Typical chain / 常见顺序（不是每个项目都要走完）："
        + joined
        + "。project-essentials stays cross-cutting. "
        "architecture-guardrails and debug-with-logs are conditional and can be used again. "
        "always-on-agents applies only when the project is that kind of agent."
    )


def project_outputs(state: dict, catalog: dict) -> list[tuple[Path, bytes]]:
    project = Path(state["project_root"])
    files = [
        (usage_path(project), dumps(state)),
        (map_path(project), render_project_map(state, catalog).encode("utf-8")),
    ]
    for path, _data in files:
        assert_write_stays_inside(project, path)
    return files


def write_state(state: dict, catalog: dict) -> bool:
    return commit_outputs(project_outputs(state, catalog))


def print_summary(prefix: str, state: dict, wrote: bool) -> None:
    current = ", ".join(names_with_status(state, "using")) or "none"
    upcoming = ", ".join(names_with_status(state, "next")) or "none"
    print(
        f"skill-map: {prefix} project={state['project_root']} source={state['source']} "
        f"skills={len(state['skills'])} revision={state['revision']} "
        f"unchanged={'no' if wrote else 'yes'}"
    )
    print(f"current: {current}")
    print(f"next: {upcoming}")


def cmd_sync(args: argparse.Namespace) -> int:
    project = require_project(args.project)
    source = resolve_source(args.source, project)
    refuse_library_project(project, source)
    catalog_path = resolve_catalog_path(args.catalog, source)
    with project_lock(project):
        discovered = discover_skills(source)
        catalog = load_catalog(catalog_path)
        state = load_state(project)
        if state is None:
            state = fresh_state(project, source)
        at = now_iso()
        merge_discovered(state, discovered, source, at)
        wrote = write_state(state, catalog)
    print_summary("sync ok", state, wrote)
    return EXIT_OK


def cmd_set(args: argparse.Namespace) -> int:
    project = require_project(args.project)
    with project_lock(project):
        state = load_state(project)
        if state is None:
            raise SkillMapError(
                EXIT_MISSING,
                "this project has no usage state yet. Run sync against this project root first. "
                "Refusing to invent a skill list.",
            )
        if args.expect_revision is not None and int(state["revision"]) != args.expect_revision:
            raise SkillMapError(
                EXIT_CONFLICT,
                f"revision is {state['revision']}, expected {args.expect_revision}. "
                "Another update landed. History was not changed. Read the current revision and rerun.",
            )
        skills = state["skills"]
        if args.skill not in skills:
            raise SkillMapError(
                EXIT_USAGE,
                f"skill {args.skill} is not in this project's map. Run sync to discover it. "
                "Refusing to invent a skill or to write another project.",
            )
        record = skills[args.skill]
        evidence = list(record["evidence"]) if args.evidence is None else [item.strip() for item in args.evidence if item.strip()]
        notes = record["notes"] if args.note is None else args.note.strip()
        reason = record["reason"] if args.reason is None else args.reason.strip()
        status = args.status
        if status in NEEDS_EVIDENCE and not evidence:
            raise SkillMapError(
                EXIT_USAGE,
                f"status {status} needs evidence of actual use. Reading or loading the skill is not evidence. "
                "Refusing to write.",
            )
        if status in NEEDS_REASON and not reason:
            raise SkillMapError(
                EXIT_USAGE,
                f"status {status} needs a reason: why this is next, conditional, or inapplicable. Refusing to write.",
            )
        if (
            record["status"] == status
            and record["notes"] == notes
            and record["reason"] == reason
            and list(record["evidence"]) == evidence
        ):
            catalog = load_catalog(resolve_catalog_path(args.catalog, Path(state["source"])))
            wrote = write_state(state, catalog)
            print_summary("set unchanged", state, wrote)
            return EXIT_OK
        record["history"].append(
            {
                "at": now_iso(),
                "event": "status-set",
                "evidence": evidence,
                "from": record["status"],
                "notes": notes,
                "reason": reason,
                "to": status,
            }
        )
        record["status"] = status
        record["notes"] = notes
        record["reason"] = reason
        record["evidence"] = evidence
        state["revision"] = int(state["revision"]) + 1
        catalog = load_catalog(resolve_catalog_path(args.catalog, Path(state["source"])))
        wrote = write_state(state, catalog)
    print_summary("set ok", state, wrote)
    return EXIT_OK


def cmd_render_library(args: argparse.Namespace) -> int:
    if not args.source or not Path(args.source).is_absolute():
        raise SkillMapError(
            EXIT_USAGE,
            "render-library --source must be an absolute path so it does not depend on the current working directory",
        )
    source = Path(args.source).resolve(strict=False)
    discovered = discover_skills(source)
    catalog = load_catalog(resolve_catalog_path(args.catalog, source))
    text = render_library(discovered, catalog, source).encode("utf-8")
    if not args.out:
        sys.stdout.buffer.write(text)
        return EXIT_OK
    out = require_absolute_output(args.out)
    if same_or_within(out, source):
        raise SkillMapError(
            EXIT_USAGE,
            "refusing to write the library navigation inside the skills source. "
            "Usage state does not belong there, and this catalog page does not either.",
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    commit_outputs([(out, text)])
    print(f"skill-map: wrote library navigation {out}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill-map",
        description=(
            "Check a skills directory and update one project's SKILL_MAP.md. "
            "Does not run unless you invoke it. Does not modify the skills source."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sync = sub.add_parser("sync", help="discover skills and update one project's map")
    sync.add_argument("--project", required=True, help="absolute path of the consuming project root")
    sync.add_argument("--source", required=True, help="skills directory, absolute or relative to --project")
    sync.add_argument("--catalog", help="absolute catalog.json; default is source then this tool's catalog")
    sync.set_defaults(func=cmd_sync)
    setter = sub.add_parser("set", help="record status, notes, reason, and evidence for one skill")
    setter.add_argument("--project", required=True)
    setter.add_argument("--skill", required=True)
    setter.add_argument("--status", required=True, choices=STATUSES)
    setter.add_argument("--note")
    setter.add_argument("--reason")
    setter.add_argument("--evidence", action="append")
    setter.add_argument("--expect-revision", type=int)
    setter.add_argument("--catalog")
    setter.set_defaults(func=cmd_set)
    render = sub.add_parser("render-library", help="write the repository navigation from the skills directory")
    render.add_argument("--source", required=True)
    render.add_argument("--catalog")
    render.add_argument("--out", help="absolute output path; stdout if omitted")
    render.set_defaults(func=cmd_render_library)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return int(args.func(args))
    except SkillMapError as exc:
        print(f"skill-map: {exc.message}", file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
