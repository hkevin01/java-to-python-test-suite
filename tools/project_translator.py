from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import re

from tools.java_analyzer import JavaClassInfo, parse_java_class
from tools.translation_tools import JAVA_TO_PYTHON_RULES


@dataclass
class FileEntry:
    filename: str
    source: str | None
    class_info: JavaClassInfo | None = None
    dependencies: list[str] = field(default_factory=list)
    order: int = 0


@dataclass
class ProjectTranslationPlan:
    ordered_files: list[FileEntry]
    class_map: dict[str, str]
    had_cycle: bool


def _parse_files(entries: list[FileEntry]) -> dict[str, str]:
    class_map: dict[str, str] = {}
    for entry in entries:
        info = parse_java_class(entry.source)
        entry.class_info = info
        if info and info.name:
            class_map[info.name] = entry.filename
    return class_map


def _extract_dependency_candidates(source: str | None) -> set[str]:
    if not source:
        return set()
    return set(re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", source))


def _build_dependency_graph(entries: list[FileEntry], class_map: dict[str, str]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}

    for entry in entries:
        if not entry.class_info:
            continue

        class_name = entry.class_info.name
        deps: set[str] = set()

        if entry.class_info.extends and entry.class_info.extends in class_map:
            deps.add(entry.class_info.extends)

        for iface in entry.class_info.implements:
            base_iface = iface.split("<", 1)[0]
            if base_iface in class_map:
                deps.add(base_iface)

        for imp in entry.class_info.imports:
            short_name = imp.rsplit(".", 1)[-1]
            short_name = short_name.split("<", 1)[0]
            if short_name in class_map:
                deps.add(short_name)

        for candidate in _extract_dependency_candidates(entry.source):
            if candidate in class_map and candidate != class_name:
                deps.add(candidate)

        deps.discard(class_name)
        entry.dependencies = sorted(deps)
        graph[class_name] = set(entry.dependencies)

    return graph


def _topological_sort(graph: dict[str, set[str]]) -> tuple[list[str], bool]:
    if not graph:
        return [], False

    nodes = sorted(graph.keys())
    indegree = {node: len(graph[node]) for node in nodes}
    dependents: dict[str, set[str]] = {node: set() for node in nodes}

    for node, deps in graph.items():
        for dep in deps:
            if dep in dependents:
                dependents[dep].add(node)

    queue = deque(sorted([node for node in nodes if indegree[node] == 0]))
    ordered: list[str] = []

    while queue:
        current = queue.popleft()
        ordered.append(current)
        for dep_node in sorted(dependents[current]):
            indegree[dep_node] -= 1
            if indegree[dep_node] == 0:
                queue.append(dep_node)

    had_cycle = len(ordered) != len(nodes)
    if had_cycle:
        remaining = sorted(node for node in nodes if node not in ordered)
        ordered.extend(remaining)

    return ordered, had_cycle


def plan_project_translation(files: dict[str, str | None]) -> ProjectTranslationPlan:
    if files is None:
        files = {}

    entries = [FileEntry(filename=filename, source=source) for filename, source in files.items()]
    class_map = _parse_files(entries)
    graph = _build_dependency_graph(entries, class_map)
    ordered_class_names, had_cycle = _topological_sort(graph)

    class_to_entry = {
        entry.class_info.name: entry
        for entry in entries
        if entry.class_info is not None
    }

    ordered_entries: list[FileEntry] = []
    seen_filenames: set[str] = set()

    for cls_name in ordered_class_names:
        entry = class_to_entry.get(cls_name)
        if entry and entry.filename not in seen_filenames:
            ordered_entries.append(entry)
            seen_filenames.add(entry.filename)

    for entry in sorted(entries, key=lambda e: e.filename):
        if entry.filename not in seen_filenames:
            ordered_entries.append(entry)
            seen_filenames.add(entry.filename)

    for idx, entry in enumerate(ordered_entries):
        entry.order = idx

    return ProjectTranslationPlan(
        ordered_files=ordered_entries,
        class_map=class_map,
        had_cycle=had_cycle,
    )


def build_project_file_prompt(file_entry: FileEntry, class_map: dict[str, str]) -> str:
    deps = ", ".join(file_entry.dependencies) if file_entry.dependencies else "None"
    class_name = file_entry.class_info.name if file_entry.class_info else file_entry.filename
    return (
        "Translate this Java file to Python with strict dependency awareness.\n\n"
        f"Filename: {file_entry.filename}\n"
        f"Class: {class_name}\n"
        f"Dependency order index: {file_entry.order}\n"
        f"Dependencies: {deps}\n"
        f"Known class map: {class_map}\n\n"
        f"JAVA -> PYTHON TRANSLATION RULES\n{JAVA_TO_PYTHON_RULES}\n\n"
        "JAVA SOURCE\n"
        "-----------\n"
        f"{file_entry.source or ''}\n"
    )
