from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Optional

import javalang


@dataclass
class JavaClassInfo:
    name: str
    package: str = ""
    fields: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    is_interface: bool = False
    is_abstract: bool = False
    extends: Optional[str] = None
    implements: list[str] = field(default_factory=list)


_CLASS_RE = re.compile(r"\b(class|interface|enum)\s+([A-Za-z_][A-Za-z0-9_]*)")
_PACKAGE_RE = re.compile(r"\bpackage\s+([A-Za-z0-9_.]+)\s*;")
_IMPORT_RE = re.compile(r"\bimport\s+([A-Za-z0-9_.*]+)\s*;")
_EXTENDS_RE = re.compile(r"\bextends\s+([A-Za-z_][A-Za-z0-9_]*)")
_IMPLEMENTS_RE = re.compile(r"\bimplements\s+([^\{]+)")
_FIELD_RE = re.compile(
    r"\b(?:private|protected|public)\s+"
    r"(?:final\s+)?(?:static\s+)?[A-Za-z0-9_<>,\[\]?]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|;)"
)
_METHOD_RE = re.compile(
    r"\b(?:public|protected|private)?\s*(?:static\s+)?(?:abstract\s+)?"
    r"[A-Za-z0-9_<>,\[\]?]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)


def _fallback_parse(source: str) -> Optional[JavaClassInfo]:
    kind_match = _CLASS_RE.search(source)
    if not kind_match:
        return None

    kind = kind_match.group(1)
    name = kind_match.group(2)
    package_match = _PACKAGE_RE.search(source)
    package = package_match.group(1) if package_match else ""

    imports = _IMPORT_RE.findall(source)
    fields = _FIELD_RE.findall(source)

    methods = []
    for method in _METHOD_RE.findall(source):
        if method in {"if", "for", "while", "switch", "catch", "return", "new"}:
            continue
        methods.append(method)

    extends_match = _EXTENDS_RE.search(source)
    extends = extends_match.group(1) if extends_match else None

    implements: list[str] = []
    implements_match = _IMPLEMENTS_RE.search(source)
    if implements_match:
        raw = implements_match.group(1)
        implements = [part.strip().split("<", 1)[0] for part in raw.split(",") if part.strip()]

    is_interface = kind == "interface"
    is_abstract = ("abstract class" in source) and not is_interface

    return JavaClassInfo(
        name=name,
        package=package,
        fields=sorted(set(fields)),
        methods=sorted(set(methods)),
        imports=imports,
        is_interface=is_interface,
        is_abstract=is_abstract,
        extends=extends,
        implements=implements,
    )


def parse_java_class(source: str | None) -> Optional[JavaClassInfo]:
    """Parse Java source into a lightweight class metadata structure."""
    if source is None:
        return None

    text = str(source)
    if not text.strip():
        return None

    try:
        tree = javalang.parse.parse(text)
        if not tree.types:
            return None

        type_decl = tree.types[0]
        package = tree.package.name if tree.package else ""
        imports = [imp.path for imp in tree.imports]

        fields: list[str] = []
        methods: list[str] = []

        for fld in getattr(type_decl, "fields", []) or []:
            for decl in fld.declarators:
                fields.append(decl.name)

        for m in getattr(type_decl, "methods", []) or []:
            methods.append(m.name)

        for ctor in getattr(type_decl, "constructors", []) or []:
            methods.append(ctor.name)

        if not imports:
            inferred_types = set(re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", text))
            inferred_types.discard(type_decl.name)
            inferred_types.discard("String")
            inferred_types.discard("Integer")
            inferred_types.discard("Long")
            inferred_types.discard("Double")
            inferred_types.discard("Float")
            inferred_types.discard("Boolean")
            inferred_types.discard("Object")
            imports.extend(sorted(inferred_types))

        is_interface = isinstance(type_decl, javalang.tree.InterfaceDeclaration)
        is_abstract = ("abstract" in getattr(type_decl, "modifiers", set())) and not is_interface

        extends = None
        if getattr(type_decl, "extends", None) is not None:
            ext = type_decl.extends
            extends = ext.name if hasattr(ext, "name") else str(ext)

        implements: list[str] = []
        for impl in getattr(type_decl, "implements", []) or []:
            implements.append(impl.name if hasattr(impl, "name") else str(impl))

        return JavaClassInfo(
            name=type_decl.name,
            package=package,
            fields=sorted(set(fields)),
            methods=sorted(set(methods)),
            imports=imports,
            is_interface=is_interface,
            is_abstract=is_abstract,
            extends=extends,
            implements=implements,
        )
    except Exception:
        return _fallback_parse(text)
