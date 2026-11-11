import ast
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

PUBLIC_JAVA_TYPE = re.compile(
    r"\bpublic\s+(?:(?:final|abstract|sealed|static)\s+)*(?:class|interface|enum|record)\s+([A-Za-z_$][\w$]*)"
)

def check_python_syntax(source_code: str) -> dict:
    try:
        ast.parse(source_code)
        return {"valid": True, "message": "Python syntax is valid.", "line": None}
    except SyntaxError as error:
        return {"valid": False, "message": error.msg, "line": error.lineno}

def check_sql_structure(source_code: str) -> dict:
    """Basic structure check only. Skips comments and quoted text; SQL is never executed."""
    quote, depth, index, length = None, 0, 0, len(source_code)
    while index < length:
        char = source_code[index]
        if quote:
            if char == quote:
                quote = None
        elif source_code.startswith("--", index):
            end = source_code.find("\n", index)
            index = length if end == -1 else end
            continue
        elif source_code.startswith("/*", index):
            end = source_code.find("*/", index + 2)
            if end == -1:
                return {"valid": False, "message": "Unclosed /* comment.", "line": None}
            index = end + 2
            continue
        elif char in ("'", '"', "`"):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return {"valid": False, "message": "Unmatched closing parenthesis.", "line": None}
        index += 1
    if quote:
        return {"valid": False, "message": "Unclosed quote.", "line": None}
    if depth != 0:
        return {"valid": False, "message": "Unbalanced parentheses.", "line": None}
    return {"valid": True, "message": "Basic SQL structure check passed; SQL was not executed.", "line": None}

def _run_external_check(args: list[str], filename: str, source_code: str, tool: str) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / filename
        path.write_text(source_code, encoding="utf-8")
        try:
            result = subprocess.run(args + [str(path)], capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            return {"valid": None, "message": f"{tool} check timed out after 20 seconds.", "line": None}
        detail = (result.stderr or result.stdout).strip()
        return {"valid": result.returncode == 0, "message": detail or f"{tool} syntax check passed.", "line": None}

def check_code_syntax(source_code: str, language: str) -> dict:
    language = language.strip().lower()
    if language in {"python", "py"}:
        return check_python_syntax(source_code)
    if language in {"javascript", "js"}:
        node = shutil.which("node")
        if not node:
            return {"valid": None, "message": "Node.js was not found; local check was skipped.", "line": None}
        # .mjs accepts both import/export and CommonJS-style code, so the check is not too strict.
        return _run_external_check([node, "--check"], "snippet.mjs", source_code, "Node.js")
    if language == "java":
        javac = shutil.which("javac")
        if not javac:
            return {"valid": None, "message": "JDK javac was not found; local check was skipped.", "line": None}
        # javac requires the public top-level type to match the filename.
        match = PUBLIC_JAVA_TYPE.search(source_code)
        filename = f"{match.group(1)}.java" if match else "Snippet.java"
        return _run_external_check([javac], filename, source_code, "javac")
    if language == "sql":
        return check_sql_structure(source_code)
    return {"valid": None, "message": f"Unsupported language: {language}", "line": None}
