"""
PROJECT TRANSLATOR - Multi-file Java to Python Translation Planning

MODULE INTENT:
    Orchestrates end-to-end translation planning for Java projects by:
    1. Parsing Java source files to extract class structure
    2. Building a dependency graph (which classes depend on which others)
    3. Computing translation order using topological sort
    4. Assigning deterministic processing indices to ensure base classes/interfaces
       are translated before dependent classes

MODULE INVARIANTS:
    - For every class A that depends on class B, order(B) < order(A)
    - All files are included in output (even if cycles exist)
    - If had_cycle=True, remaining cyclic nodes appended with no guaranteed order
    - Dependencies are never circular after stable sort phase

USE CASE:
    When translating a Java project, you cannot just translate files randomly.
    If PaymentProcessor extends AbstractProcessor, AbstractProcessor must be
    translated first so PaymentProcessor can reference the base contract.
    This module identifies that dependency and guarantees ordering.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import re

from tools.java_analyzer import JavaClassInfo, parse_java_class
from tools.translation_tools import JAVA_TO_PYTHON_RULES


@dataclass
class FileEntry:
    """
    ID: FILEENTRY_001
    REQUIREMENT: Represent a single Java source file with metadata needed for translation.
    PURPOSE: Encapsulates file context (name, source code, parsed structure) alongside
             computed translation properties (dependencies, order index).
    RATIONALE: Dataclass keeps file-level data co-located, simplifying graph algorithms
               and output construction. Single source of truth for file state.
    
    FIELDS:
        filename (str): Relative or absolute path to source file (e.g., "Order.java")
        source (str|None): Complete Java source code text; None for missing/unreadable files
        class_info (JavaClassInfo|None): Parsed class metadata (name, extends, implements, imports);
                                         populated by _parse_files()
        dependencies (list[str]): Sorted list of class names this file depends on;
                                 computed by _build_dependency_graph()
        order (int): Translation index (0-based); 0=first, higher=later;
                    computed by plan_project_translation()
    
    INVARIANT: If class_info is not None, class_info.name must be a valid identifier
    """
    filename: str
    source: str | None
    class_info: JavaClassInfo | None = None
    dependencies: list[str] = field(default_factory=list)
    order: int = 0


@dataclass
class ProjectTranslationPlan:
    """
    ID: PROJPLAN_001
    REQUIREMENT: Represent the complete translation plan for a multi-file Java project.
    PURPOSE: Bundles ordered file list, class-to-file mapping, and cycle detection flag
             into one immutable result for consumers (API endpoints, test harnesses).
    RATIONALE: Single-result pattern makes dependency passing explicit; flags like had_cycle
               allow calling code to adjust behavior (log warning, skip validation, etc.).
    
    FIELDS:
        ordered_files (list[FileEntry]): Files sorted by translation order (index 0 first).
                                         Every file in input appears exactly once.
                                         Guaranteed: if A depends on B, index(B) < index(A)
                                         unless had_cycle=True.
        class_map (dict[str, str]): Bidirectional mapping {class_name → filename} for
                                   quick lookup of which file defines a class. Built by
                                   _parse_files(). Used during graph building and prompt
                                   construction.
        had_cycle (bool): True if dependency graph contains circular edges (A→B→...→A).
                         If True, some nodes in ordered_files may not satisfy dependency
                         ordering (all files still included). False guarantees ordering
                         constraint holds for all pairs.
    
    POSTCONDITION: len(ordered_files) == len(input files from plan_project_translation)
    POSTCONDITION: All files in input appear exactly once in ordered_files
    """
    ordered_files: list[FileEntry]
    class_map: dict[str, str]
    had_cycle: bool



def _parse_files(entries: list[FileEntry]) -> dict[str, str]:
    """
    ID: PARSEFILES_001
    REQUIREMENT: Parse all Java source files and build class-to-file lookup map.
    PURPOSE: Initializes FileEntry.class_info for each file using javalang + regex parser,
             enabling downstream dependency graph building. Constructs bidirectional
             class_map for O(1) class lookup.
    RATIONALE: Separating parsing from graph building allows each step to focus on one
               transformation. Early mapping construction prevents repeated lookups.
    
    PRECONDITION: entries list is populated with FileEntry objects (source may be None)
    PRECONDITION: entries are not modified during execution
    
    ALGORITHM STEPS:
        1. For each FileEntry e in entries:
           a. Call parse_java_class(e.source) → JavaClassInfo or None
           b. Store result in e.class_info (modifies entry in-place)
           c. If parsed successfully and e.class_info.name exists, add to class_map
        2. Return class_map
    
    SIDE EFFECTS:
        - Modifies each FileEntry.class_info field (in-place mutation)
        - Does not modify FileEntry.dependencies or .order
    
    INPUTS:
        entries (list[FileEntry]): Mutable list of file entries. Each entry's source
                                  field may be None (unreadable file, missing content).
    
    OUTPUTS:
        dict[str, str]: {class_name → filename} map for all successfully parsed classes.
                       Does not include files with parse_java_class() → None.
                       Keys are unique (one class per file assumed in this project).
    
    FAILURE MODES:
        - parse_java_class() returns None: File entry skipped from class_map
        - entry.source is None: parse_java_class() returns None, entry skipped
        - Duplicate class names (2 files with same class): Later file overwrites in map
    
    CONSTRAINTS:
        - Time: O(n) where n = number of entries
        - No external I/O; all input in memory
    
    VERIFICATION:
        - class_map contains only entries with successful parse_java_class() call
        - class_map size <= len(entries)
        - Entries modified have class_info populated (not None on successful parse)
    """
    # INITIALIZATION: Prepare empty map to accumulate class definitions
    class_map: dict[str, str] = {}
    
    # MAIN LOOP: Iterate over each file entry and extract class metadata
    for entry in entries:
        # Guard: Attempt to parse Java source; may return None for malformed input
        info = parse_java_class(entry.source)
        # Store parsed metadata in entry (in-place mutation)
        entry.class_info = info
        
        # Guard: Check if parse was successful AND class has a valid name
        if info and info.name:
            # Record mapping: class name → filename for dependency resolution
            class_map[info.name] = entry.filename
    
    return class_map


def _extract_dependency_candidates(source: str | None) -> set[str]:
    """
    ID: EXTDEPS_001
    REQUIREMENT: Extract all potential class references from Java source code via pattern matching.
    PURPOSE: Identifies candidate identifiers that might be class names (start with uppercase).
             Used as fallback when explicit imports/extends/implements are insufficient.
    RATIONALE: Regex-based heuristic catches implicit references (local variables typed with
               unimported or same-package classes). Complements explicit declaration analysis.
    
    PRECONDITION: source may be None or empty string
    
    ALGORITHM:
        - Guard: If source is None or empty, return empty set
        - Extract all identifiers matching pattern [A-Z][A-Za-z0-9_]* (Java identifier starting uppercase)
        - Return set (uniqueness guaranteed)
    
    INPUTS:
        source (str|None): Complete Java source code. None treated as no content.
    
    OUTPUTS:
        set[str]: Candidate class names (strings starting with uppercase letter).
                 Empty set if source is None or has no matches.
    
    CONSTRAINTS:
        - Heuristic-based; may match non-class identifiers (constants in UPPER_CASE, keywords)
        - No scope analysis; matches names that appear anywhere in source
    
    SIDE EFFECTS: None; read-only operation
    """
    # Guard: Validate input; None or falsy input returns empty set
    if not source:
        return set()
    
    # Extract all uppercase-starting identifiers using regex
    # Pattern: [A-Z] (uppercase start) followed by [A-Za-z0-9_]* (identifier chars)
    return set(re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", source))


def _build_dependency_graph(entries: list[FileEntry], class_map: dict[str, str]) -> dict[str, set[str]]:
    """
    ID: BUILDGRAPH_001
    REQUIREMENT: Construct dependency graph from parsed Java classes and class map.
    PURPOSE: Maps each class to its immediate dependencies (extends, implements, imports, references).
             Graph edges represent "depends on" relationships (A depends on B).
             Later used by topological sort to enforce ordering.
    RATIONALE: Dependency graph is the data structure enabling deterministic translation order.
               Multiple sources of dependency info (extends, implements, imports, heuristic
               candidates) ensure robustness across different code patterns.
    
    PRECONDITION: entries have been processed by _parse_files() (class_info populated)
    PRECONDITION: class_map correctly maps all class names to filenames
    
    ALGORITHM STEPS (for each class_info in entries):
        1. Initialize empty dependency set (deps)
        2. Check extends relationship: if extends in class_map, add to deps
        3. Check implements relationships: for each interface, if in class_map, add to deps
        4. Check explicit imports: for each import, extract short name, if in class_map add to deps
        5. Check candidate identifiers: for each regex match in source, if in class_map add to deps
        6. Remove self-references (class depending on itself)
        7. Store deps as sorted list in entry.dependencies
        8. Record mapping: class_name → set of dependencies in output graph
    
    INPUTS:
        entries (list[FileEntry]): Files with class_info populated (from _parse_files)
        class_map (dict[str, str]): {class_name → filename} lookup table
    
    OUTPUTS:
        dict[str, set[str]]: {class_name → set of dependent class names}
                            Keys are all classes with class_info in entries
                            Values are dependencies within project (not external libs)
    
    SIDE EFFECTS:
        - Modifies each entry.dependencies field (populated with sorted list)
    
    FAILURE MODES:
        - entry.class_info is None: Entry skipped (no deps extracted)
        - class_map missing an import: Import silently ignored (external lib assumed)
    
    CONSTRAINTS:
        - Only dependencies in class_map are included (project-internal only)
        - Graph edges are directed: "A depends on B" means B must be translated first
    
    VERIFICATION:
        - All entries with class_info have entry.dependencies populated
        - graph keys match all class_name values from parsed class_info
        - graph values contain only classes present in class_map (no external libs)
    """
    # INITIALIZATION: Create empty graph to map class name → dependencies
    graph: dict[str, set[str]] = {}
    
    # MAIN LOOP: Process each Java class in project
    for entry in entries:
        # Guard: Skip entries with no parsed class info
        if not entry.class_info:
            continue
        
        # Extract class name and initialize empty dependency set
        class_name = entry.class_info.name
        deps: set[str] = set()
        
        # DEPENDENCY COLLECTION: Add explicit extends relationship
        # Guard: Only add if extends class is in project (not external lib)
        if entry.class_info.extends and entry.class_info.extends in class_map:
            deps.add(entry.class_info.extends)
        
        # DEPENDENCY COLLECTION: Add explicit implements relationships
        for iface in entry.class_info.implements:
            # Guard: Handle generics by stripping type parameters (e.g., List<String> → List)
            base_iface = iface.split("<", 1)[0]
            # Guard: Only add if interface is in project (not external lib)
            if base_iface in class_map:
                deps.add(base_iface)
        
        # DEPENDENCY COLLECTION: Add explicit imports that refer to project classes
        for imp in entry.class_info.imports:
            # Extract short name from fully qualified import (e.g., com.example.Order → Order)
            short_name = imp.rsplit(".", 1)[-1]
            # Guard: Handle generic imports by stripping type parameters
            short_name = short_name.split("<", 1)[0]
            # Guard: Only add if imported class is in project
            if short_name in class_map:
                deps.add(short_name)
        
        # DEPENDENCY COLLECTION: Add heuristic candidates (uppercase identifiers in source)
        # These catch implicit references not covered by explicit imports/extends/implements
        for candidate in _extract_dependency_candidates(entry.source):
            # Guard: Only add if candidate matches a known project class
            # Guard: Exclude self-reference to avoid circular dependency with same class
            if candidate in class_map and candidate != class_name:
                deps.add(candidate)
        
        # CLEANUP: Remove self-reference if somehow added
        deps.discard(class_name)
        
        # FINALIZATION: Store sorted dependencies in entry for consistent output
        entry.dependencies = sorted(deps)
        # Record in graph
        graph[class_name] = set(entry.dependencies)
    
    return graph


def _topological_sort(graph: dict[str, set[str]]) -> tuple[list[str], bool]:
    """
    ID: TOPOSORT_001
    REQUIREMENT: Sort dependency graph into valid translation order using Kahn's algorithm.
    PURPOSE: Transforms dependency graph into a linear sequence where for every edge
             "A depends on B", B appears before A in the sequence. This guarantees base
             classes and interfaces are translated before classes that inherit from them.
    RATIONALE: Kahn's algorithm uses in-degree (incoming edge count) to deterministically
               process nodes with no unmet dependencies first, avoiding cycle-prone
               depth-first approaches. Outputs partial order on cyclic input.
    
    BACKGROUND FOR JUNIOR DEVELOPERS:
    
    Think of a dependency graph like a task list with constraints:
    - Write Order class
    - Write OrderService (depends on Order; needs to know Order exists first)
    - Write OrderRepository (depends on both Order and OrderService)
    
    Kahn's algorithm works like this:
    1. COUNT: For each task, count how many other tasks must finish before it
       (this count is called "in-degree")
    2. QUEUE: Find all tasks with no prerequisites (in-degree = 0)
    3. PROCESS: Do one task, then reduce prerequisite count for all tasks waiting on it
    4. REPEAT: Steps 2-3 until all tasks done or you find a cycle
    5. DETECT: If any tasks remain with unmet prerequisites, a circular dependency exists
    
    For example:
    - Order: 0 prerequisites (do first)
    - OrderService: 1 prerequisite (Order) → reduce to 0 when Order done → can do now
    - OrderRepository: 2 prerequisites (Order, OrderService) → reduce as each completes
    
    Result: [Order, OrderService, OrderRepository] - dependencies satisfied in order!
    
    ALGORITHM DETAILED STEPS:
    
    STEP 1: GUARD AND INITIALIZATION
        - Guard: If graph is empty, return empty order list, no cycle
        - Initialize in-degree map: {node → count of nodes that depend on it}
          Wait, that's backwards. In-degree is count of edges pointing TO this node.
          If A depends on B, there's an edge B→A, so A has in-degree += 1.
          So: in-degree[A] = number of different classes A depends on
        - Initialize dependents map: {node → set of nodes that depend on THIS node}
          If A depends on B, then B is a dependency of A, so B is a dependent of B.
          Actually: if A depends on B, then A is a dependent of B.
          So: dependents[B] = set of all nodes that depend on B
    
    STEP 2: QUEUE INITIALIZATION
        - Collect all nodes with in-degree 0 (no unmet dependencies)
        - Sort these nodes alphabetically for deterministic ordering
        - Initialize processing queue
    
    STEP 3: MAIN PROCESSING LOOP
        For each node in queue (in order):
        a. Record this node as processed (append to output)
        b. For each node that depends on this node (from dependents):
           - Decrement its in-degree (one dependency now satisfied)
           - If in-degree becomes 0, add to queue (all deps now satisfied)
        c. Continue until queue is empty
    
    STEP 4: CYCLE DETECTION
        - If processed count < total node count, a cycle exists
        - Append remaining nodes to output anyway (for diagnostics)
    
    OUTPUTS:
        (ordered: list[str], had_cycle: bool)
        ordered: List of class names in valid translation order (all nodes included)
        had_cycle: True if circular dependency detected, False otherwise
    
    PRECONDITION: graph keys are all nodes; values are edges TO dependencies
    PRECONDITION: No self-loops (A depends on A) - should be filtered by caller
    
    INPUTS:
        graph (dict[str, set[str]]): {class_name → set of dependencies}
                                    Represents "A depends on {B, C, ...}"
    
    OUTPUTS:
        tuple[list[str], bool]: (ordered class names, cycle detected flag)
    
    SIDE EFFECTS: None; graph not modified; no external I/O
    
    CONSTRAINTS:
        - Time complexity: O(V + E) where V = nodes, E = edges
        - Space complexity: O(V) for queues and maps
        - Deterministic: same input always produces same output
    
    INVARIANTS MAINTAINED:
        - For every edge A→B (A depends on B), index(B) < index(A) in result
          UNLESS had_cycle=True (cycle breaks ordering guarantee)
        - All nodes from input graph appear in output list
    
    FAILURE MODES & RECOVERY:
        - Cycle detected: All nodes still in output, order may not satisfy deps
        - Empty graph: Returns ([], False)
        - Self-reference: Caller must filter; algorithm assumes no self-loops
    
    VERIFICATION:
        - Check len(ordered) == len(graph): All nodes included
        - Check all keys from graph appear in ordered: No nodes dropped
        - For each entry in ordered[i] with deps: all deps appear in ordered[0:i]
    """
    
    # GUARD & INITIALIZATION: Handle empty graph edge case
    if not graph:
        return [], False
    
    # Collect all node names and sort for deterministic processing
    nodes = sorted(graph.keys())
    
    # STEP 1: INITIALIZE IN-DEGREE MAP
    # in-degree[A] = how many nodes does A directly depend on
    # Example: If A depends on {B, C}, then in_degree[A] = 2
    indegree = {node: len(graph[node]) for node in nodes}
    
    # STEP 1: INITIALIZE DEPENDENTS MAP
    # dependents[B] = set of all nodes that depend on B
    # Example: If A depends on B and C depends on B, then dependents[B] = {A, C}
    # This lets us quickly find "who depends on me" when we process a node
    dependents: dict[str, set[str]] = {node: set() for node in nodes}
    
    # Build dependents by reversing the dependency direction
    # For each node and its dependencies, record that this node depends on those
    for node, deps in graph.items():
        for dep in deps:
            # dep is a dependency of node, so node is a dependent of dep
            if dep in dependents:
                dependents[dep].add(node)
    
    # STEP 2: INITIALIZE QUEUE WITH NODES HAVING NO UNMET DEPENDENCIES
    # These are nodes with in-degree 0 (no other nodes must be translated first)
    queue = deque(sorted([node for node in nodes if indegree[node] == 0]))
    
    # STEP 3: PROCESS NODES IN TOPOLOGICAL ORDER
    ordered: list[str] = []
    
    # Main loop: continue while there are nodes to process
    while queue:
        # Take next node with no unmet dependencies
        current = queue.popleft()
        # Record this node in the final order
        ordered.append(current)
        
        # For each node that depends on the current node:
        for dep_node in sorted(dependents[current]):
            # Decrement in-degree (one dependency now satisfied)
            indegree[dep_node] -= 1
            # If all dependencies are now satisfied, add to queue
            if indegree[dep_node] == 0:
                queue.append(dep_node)
    
    # STEP 4: CYCLE DETECTION AND FALLBACK
    # If we processed fewer nodes than exist, there's a cycle
    had_cycle = len(ordered) != len(nodes)
    
    # If a cycle was detected, append remaining nodes to output
    # (they couldn't be processed due to circular dependencies)
    # This ensures all input nodes are included in output for diagnostics
    if had_cycle:
        remaining = sorted(node for node in nodes if node not in ordered)
        ordered.extend(remaining)
    
    return ordered, had_cycle


def plan_project_translation(files: dict[str, str | None]) -> ProjectTranslationPlan:
    """
    ID: PLANPROJLATION_001
    REQUIREMENT: Generate complete translation plan for a Java project with proper ordering.
    PURPOSE: Orchestrates parsing, graph building, topological sorting, and final ordering
             to produce a ProjectTranslationPlan with files in dependency-first order.
    RATIONALE: Single public entry point for translation planning. Encapsulates all
               intermediate steps, reducing coupling and centralizing logic.
    
    ALGORITHM FLOW:
        1. GUARD: Handle None input files parameter
        2. CREATE: Build FileEntry objects for each file
        3. PARSE: Extract class metadata from sources (_parse_files)
        4. BUILD: Construct dependency graph (_build_dependency_graph)
        5. SORT: Topologically order classes using Kahn's algorithm (_topological_sort)
        6. MAP: Create class_name → FileEntry reverse mapping
        7. ORDER: Translate class order to file order (keeping filenames unique)
        8. FINALIZE: Assign order index to each FileEntry
        9. APPEND: Include any unordered files at the end
        10. RETURN: ProjectTranslationPlan with ordered files and metadata
    
    PRECONDITION: files dict may be None or contain None values (missing sources)
    
    INPUTS:
        files (dict[str, str|None]): {filename → source_code}
                                    filename is relative or absolute path
                                    source_code is Java source (None if missing)
    
    OUTPUTS:
        ProjectTranslationPlan: Immutable result with:
            ordered_files: Sorted FileEntry list (all input files included)
            class_map: {class_name → filename} for all successfully parsed classes
            had_cycle: True if circular dependencies detected
    
    POSTCONDITION: Every file in input dict appears exactly once in ordered_files
    POSTCONDITION: Ordering satisfies dependency-first (unless had_cycle=True)
    POSTCONDITION: All files get an order index (position in ordered_files)
    
    SIDE EFFECTS:
        - Creates FileEntry objects (new instances)
        - Modifies class_info, dependencies, order fields of entries
        - Does not modify input files dict
    
    FAILURE MODES:
        - files is None: Treated as empty dict
        - file source is None: parse_java_class returns None, file skipped from graph
        - Duplicate filenames: Later file overwrites in class_map (undefined behavior)
        - Duplicate class names: Later parse overwrites in class_map (undefined behavior)
    
    CONSTRAINTS:
        - Time: O(n + e) where n = files, e = edges in dependency graph
        - All files included in output regardless of parse success or cycles
    
    VERIFICATION:
        - Assert len(ordered_files) >= 0
        - Assert all input filenames appear in ordered_files
        - Assert all files have order index >= 0
        - Assert order indices are contiguous (0 to len-1) with possible duplicates
    """
    
    # GUARD: Handle None input gracefully
    if files is None:
        files = {}
    
    # STEP 1: CREATE: Build FileEntry objects wrapping each file
    entries = [FileEntry(filename=filename, source=source) for filename, source in files.items()]
    
    # STEP 2: PARSE: Extract Java class metadata from all sources
    class_map = _parse_files(entries)
    
    # STEP 3: BUILD: Construct dependency graph (which classes depend on which)
    graph = _build_dependency_graph(entries, class_map)
    
    # STEP 4: SORT: Order classes using Kahn's topological sort algorithm
    ordered_class_names, had_cycle = _topological_sort(graph)
    
    # STEP 5: MAP: Build reverse mapping for quick FileEntry lookup by class name
    class_to_entry = {
        entry.class_info.name: entry
        for entry in entries
        if entry.class_info is not None
    }
    
    # STEP 6-7: ORDER: Convert class order to file order (handling deduplication)
    # Process classes in topological order, but output each unique file only once
    ordered_entries: list[FileEntry] = []
    seen_filenames: set[str] = set()
    
    # For each class in dependency-first order:
    for cls_name in ordered_class_names:
        # Look up the file that defines this class
        entry = class_to_entry.get(cls_name)
        # Guard: Ensure entry exists and filename not already added
        if entry and entry.filename not in seen_filenames:
            ordered_entries.append(entry)
            seen_filenames.add(entry.filename)
    
    # STEP 8: APPEND: Include any files that weren't parsed (no class_info)
    # These files come after ordered files, sorted alphabetically for determinism
    for entry in sorted(entries, key=lambda e: e.filename):
        if entry.filename not in seen_filenames:
            ordered_entries.append(entry)
            seen_filenames.add(entry.filename)
    
    # STEP 9: FINALIZE: Assign sequential order index to each file
    # order[i] = position in ordered_entries (0 = first to translate)
    for idx, entry in enumerate(ordered_entries):
        entry.order = idx
    
    # STEP 10: RETURN: Package result
    return ProjectTranslationPlan(
        ordered_files=ordered_entries,
        class_map=class_map,
        had_cycle=had_cycle,
    )


def build_project_file_prompt(file_entry: FileEntry, class_map: dict[str, str]) -> str:
    """
    ID: BUILDPROMPT_001
    REQUIREMENT: Construct a detailed translation prompt for a single Java file.
    PURPOSE: Formats file metadata, dependencies, translation rules, and source code
             into a structured prompt suitable for an LLM to translate Java to Python.
    RATIONALE: Separates prompt construction from translation logic. Clear structure helps
               LLM understand context (order index, dependencies) and translation rules.
    
    ALGORITHM:
        1. Extract dependency names and format (comma-separated or "None")
        2. Extract class name from parsed class_info
        3. Construct multi-section prompt with:
           a. Instructions and metadata
           b. Dependency order index (position in translation sequence)
           c. Known class map (for reference)
           d. Java-to-Python translation rules
           e. Java source code to translate
    
    PRECONDITION: file_entry must have been processed by plan_project_translation()
    PRECONDITION: file_entry.order must be assigned (>= 0)
    PRECONDITION: class_map must match the graph used to create file_entry
    
    INPUTS:
        file_entry (FileEntry): Parsed file with class_info and dependencies populated
        class_map (dict[str, str]): {class_name → filename} reference for context
    
    OUTPUTS:
        str: Formatted multi-section prompt for LLM
    
    SIDE EFFECTS: None; read-only operation
    
    FAILURE MODES:
        - file_entry.class_info is None: class_name falls back to filename
        - file_entry.dependencies is empty: deps becomes "None"
        - file_entry.source is None: empty string used in source section
    
    CONSTRAINTS:
        - Output format is free-form text; no JSON or structured format
        - Order index is 0-based (0 = first file to translate)
        - Large source files produce large prompts (no truncation applied)
    
    VERIFICATION:
        - Check output contains filename, class name, order index, dependencies
        - Check output contains JAVA_TO_PYTHON_RULES content
        - Check output contains source code (if provided)
        - Check format matches structured sections pattern
    """
    
    # EXTRACTION: Prepare dependency list for prompt
    # Guard: Handle empty dependencies gracefully
    deps = ", ".join(file_entry.dependencies) if file_entry.dependencies else "None"
    
    # EXTRACTION: Prepare class name for prompt
    # Guard: Use filename as fallback if class parsing failed
    class_name = file_entry.class_info.name if file_entry.class_info else file_entry.filename
    
    # CONSTRUCTION: Build multi-section prompt
    return (
        "Translate this Java file to Python with strict dependency awareness.\n\n"
        # Section 1: File metadata and ordering context
        f"Filename: {file_entry.filename}\n"
        f"Class: {class_name}\n"
        f"Dependency order index: {file_entry.order}\n"
        f"Dependencies: {deps}\n"
        f"Known class map: {class_map}\n\n"
        # Section 2: Translation rules reference
        f"JAVA -> PYTHON TRANSLATION RULES\n{JAVA_TO_PYTHON_RULES}\n\n"
        # Section 3: Source code to translate
        "JAVA SOURCE\n"
        "-----------\n"
        f"{file_entry.source or ''}\n"
    )
