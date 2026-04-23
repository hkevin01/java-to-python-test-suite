from __future__ import annotations


JAVA_TO_PYTHON_RULES = """
JAVA -> PYTHON TRANSLATION RULES

TYPE MAPPING
- String -> str
- boolean / Boolean -> bool
- int / Integer -> int
- long / Long -> int
- double / Double / float / Float -> float
- void -> None
- Optional<T> -> T | None (or Optional[T])
- List<T> / ArrayList<T> -> list[T]
- Map<K, V> / HashMap<K, V> -> dict[K, V]

OBJECT MODEL MAPPING
- Java class -> Python class
- Java abstract class -> class extending ABC
- Java interface -> Protocol
- Java enum -> enum.Enum
- Java constructor -> __init__
- Java getter/setter pairs -> Pythonic property when appropriate

SYNTAX MAPPING
- this.field -> self.field
- null -> None
- true/false -> True/False
- System.out.println(...) -> print(...)
- static final constants -> UPPER_SNAKE_CASE module/class constants

CONTROL FLOW
- enhanced for loops map to Python for ... in ...
- indexed loops map to range(...) where needed
- switch/case maps to match/case or if/elif chains

EXCEPTION HANDLING
- Java throw new X(...) -> raise X(...)
- try/catch/finally -> try/except/finally
- checked exceptions should be represented with explicit raise behavior

IMPORTS AND PACKAGING
- Remove Java package imports (java.*, javax.*, org.springframework.*)
- Use Python stdlib and typing imports as needed
- Prefer explicit imports for local modules

QUALITY RULES
- Use type hints on method signatures
- Keep generated output valid Python syntax
- Avoid Java artifacts such as @Override, new, angle bracket generics syntax,
  and Java access modifiers keywords in Python output
- Preserve intent: base classes/interfaces before dependent subclasses/services
""".strip()


def build_java_to_python_prompt(java_source: str, class_name: str) -> str:
    return (
        "You are translating Java to Python with strict structural fidelity.\n\n"
        f"Class/File target: {class_name}\n\n"
        f"{JAVA_TO_PYTHON_RULES}\n\n"
        "JAVA SOURCE\n"
        "-----------\n"
        f"{java_source}\n\n"
        "Return only valid Python code."
    )
