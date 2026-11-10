import argparse
import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


TASK_DIRECTORY = Path(__file__).resolve().parent
ASSIGNMENTS_DIRECTORY = TASK_DIRECTORY.parent
IMPLEMENTATION_DIRECTORY = ASSIGNMENTS_DIRECTORY.parent
REPOSITORY_DIRECTORY = IMPLEMENTATION_DIRECTORY / "AI4SE_Playground"
PROJECT_DIRECTORY = REPOSITORY_DIRECTORY / "playground"
TASKS_PATH = ASSIGNMENTS_DIRECTORY / "missing_code.json"
EMBEDDINGS_PATH = ASSIGNMENTS_DIRECTORY / "Task_3" / "chunk_embeddings.csv"
VOCABULARY_PATH = ASSIGNMENTS_DIRECTORY / "Task_3" / "tfidf_vocabulary.csv"
REPORT_PATH = TASK_DIRECTORY / "Task_5_Report.md"
ALLOWED_MODELS = (
    "gpt-6-luna",
    "gpt-5.6-luna",
    "gpt-5.4-nano",
    "gpt-5-nano",
    "gpt-5-mini",
    "gpt-4.1-nano",
    "gpt-4o-mini",
)
MAX_RESPONSE_ATTEMPTS = 3


def load_task3_module():
    module_path = ASSIGNMENTS_DIRECTORY / "Task_3" / "embed_chunks.py"
    spec = importlib.util.spec_from_file_location("task3_embed_chunks", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load Task 3 embedding module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_settings(path):
    if not path.is_file():
        return {}
    settings = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid setting at {path}:{line_number}; expected KEY=VALUE.")
        name, value = (part.strip() for part in line.split("=", 1))
        if name not in {"OPENAI_API_KEY", "OPENAI_BASE_URL"}:
            raise ValueError(f"Unsupported setting name at {path}:{line_number}: {name}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        settings[name] = value
    return settings


def load_tasks(path):
    with path.open(encoding="utf-8") as source:
        tasks = json.load(source)
    if not isinstance(tasks, list) or not tasks:
        raise ValueError(f"Expected a non-empty task list in {path}")
    required = {"file", "class", "method", "docstring"}
    for index, task in enumerate(tasks, 1):
        if not isinstance(task, dict) or not required.issubset(task):
            raise ValueError(f"Task {index} must contain {', '.join(sorted(required))}")
    return tasks


def locate_method(source, class_name, method_name):
    tree = ast.parse(source)
    matches = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            matches.extend(
                member
                for member in node.body
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                and member.name == method_name
            )
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one {class_name}.{method_name} method; found {len(matches)}"
        )
    return matches[0]


def method_source(source, method):
    lines = source.splitlines()
    return "\n".join(lines[method.lineno - 1 : method.end_lineno])


def matching_test_context(project_directory, task):
    test_path = project_directory / "tests" / f"test_{Path(task['file']).stem}.py"
    if not test_path.is_file():
        return "No matching test module was found."

    source = test_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    class_name = re.sub(r"[^a-z0-9]", "", task["class"].lower())
    method_name = re.sub(r"[^a-z0-9]", "", task["method"].lower())
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    matching_classes = [
        node
        for node in classes
        if class_name in re.sub(r"[^a-z0-9]", "", node.name.lower())
        and any(
            method_name
            in re.sub(r"[^a-z0-9]", "", member.name.lower())
            for member in node.body
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
    ]
    if not matching_classes:
        matching_classes = [
            node
            for node in classes
            if class_name in re.sub(r"[^a-z0-9]", "", node.name.lower())
        ]
    if not matching_classes:
        return f"No test class matching {task['class']}.{task['method']} was found in {test_path.name}."

    lines = source.splitlines()
    return "\n\n".join(
        "\n".join(lines[node.lineno - 1 : node.end_lineno])
        for node in matching_classes
    )


def clean_body(response, method_name):
    if not isinstance(response, str):
        raise TypeError("The model response must be text.")
    candidate = response.strip("\r\n")
    if candidate.lstrip().startswith("```"):
        candidate = re.sub(
            r"\A[ \t]*```(?:python)?[ \t]*\r?\n?",
            "",
            candidate,
            count=1,
            flags=re.IGNORECASE,
        )
        candidate = re.sub(r"\s*```\Z", "", candidate, count=1)
    candidate = textwrap.dedent(candidate).strip()
    if not candidate:
        raise ValueError(f"The model returned an empty body for {method_name}.")
    if re.match(r"^(?:async\s+)?def\s+" + re.escape(method_name) + r"\b", candidate):
        raise ValueError(
            f"The model returned a full method instead of a body for {method_name}."
        )

    try:
        wrapper = ast.parse("def _generated_method():\n" + textwrap.indent(candidate, "    "))
    except SyntaxError as error:
        raise ValueError(f"Invalid generated body for {method_name}: {error}") from error
    body = wrapper.body[0].body
    if not body or all(
        isinstance(statement, ast.Pass)
        or (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and statement.value.value is Ellipsis
        )
        for statement in body
    ):
        raise ValueError(f"The model returned an empty placeholder for {method_name}.")
    return candidate


def replace_method_body(source, class_name, method_name, body):
    method = locate_method(source, class_name, method_name)
    lines = source.splitlines(keepends=True)
    docstring = (
        method.body[0]
        if method.body
        and isinstance(method.body[0], ast.Expr)
        and isinstance(method.body[0].value, ast.Constant)
        and isinstance(method.body[0].value.value, str)
        else None
    )
    body_start = docstring.end_lineno if docstring else method.lineno
    body_indent = " " * (
        method.body[1].col_offset if docstring and len(method.body) > 1
        else method.body[0].col_offset
    )
    generated_lines = [
        body_indent + line if line else ""
        for line in body.splitlines()
    ]
    if not generated_lines:
        raise ValueError(f"Generated body for {class_name}.{method_name} is empty.")
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += "\n"
    lines[body_start : method.end_lineno] = [line + "\n" for line in generated_lines]
    updated = "".join(lines)
    ast.parse(updated)
    return updated


def generate_valid_method(model, prompt, source, class_name, method_name):
    retry_prompt = prompt
    for attempt in range(1, MAX_RESPONSE_ATTEMPTS + 1):
        response = response_text(model.invoke(retry_prompt))
        try:
            body = clean_body(response, method_name)
            updated_source = replace_method_body(
                source, class_name, method_name, body
            )
            return body, updated_source
        except (SyntaxError, ValueError) as error:
            if attempt == MAX_RESPONSE_ATTEMPTS:
                raise ValueError(
                    f"Could not generate valid code for {class_name}.{method_name} "
                    f"after {MAX_RESPONSE_ATTEMPTS} attempts: {error}"
                ) from error
            print(
                f"  Invalid Python response for {class_name}.{method_name}; "
                f"requesting a correction ({attempt + 1}/{MAX_RESPONSE_ATTEMPTS})."
            )
            retry_prompt = (
                f"{prompt}\n\n"
                "Your previous response was rejected because it was not valid Python "
                f"for the method body: {error}\n"
                "Correct the indentation and syntax. Return only the corrected method "
                "body, with consistent indentation and no Markdown fences."
            )


def task_prompt(task, original_method, retrieved_chunks, test_context):
    context = "\n\n".join(
        f"### Retrieved chunk: {chunk['file']}:{chunk['start_line']}-{chunk['end_line']}\n"
        f"{chunk['text']}"
        for _, chunk in retrieved_chunks
    )
    return (
        f"Implement {task['class']}.{task['method']} in the target Python module.\n"
        f"Task description: {task['docstring'].strip()}\n\n"
        "Existing method signature and documentation (preserve both):\n"
        f"```python\n{original_method}\n```\n\n"
        "Relevant repository context retrieved by TF-IDF:\n"
        f"{context}\n\n"
        "Relevant existing unit tests; treat their assertions as the expected behavior:\n"
        f"```python\n{test_context}\n```\n\n"
        "When prose documentation and a test assertion seem to differ, preserve "
        "the explicit tested behavior unless it conflicts with another test.\n\n"
        "Return only the method body as valid Python, without a method definition, "
        "Markdown fences, or explanation. Preserve the method's documented behavior "
        "and follow the project's existing conventions. Do not modify other methods."
    )


def create_model(model_name, settings):
    key = os.environ.get("OPENAI_API_KEY") or settings.get("OPENAI_API_KEY")
    if not key or key == "PASTE_YOUR_KEY_HERE":
        raise EnvironmentError(
            f"Set OPENAI_API_KEY in {TASK_DIRECTORY / '.env'} or in the environment."
        )
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as error:
        raise ImportError(
            "Missing dependency langchain-openai. Install it with "
            "`python -m pip install langchain-openai`."
        ) from error

    base_url = os.environ.get("OPENAI_BASE_URL") or settings.get("OPENAI_BASE_URL")
    options = {"model": model_name, "api_key": key}
    if base_url:
        options["base_url"] = base_url
    return ChatOpenAI(**options)


def response_text(response):
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text = [part["text"] for part in content if isinstance(part, dict) and "text" in part]
        if text:
            return "\n".join(text)
    raise TypeError("The LLM returned no text content.")


def validate_task_path(repository, relative_path):
    path = (repository / relative_path).resolve()
    try:
        path.relative_to(repository.resolve())
    except ValueError as error:
        raise ValueError(f"Task target is outside the cloned repository: {relative_path}") from error
    if not path.is_file():
        raise FileNotFoundError(f"Task target file does not exist: {path}")
    return path


def write_atomically(path, contents):
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(contents)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def write_test_report(result, command):
    output = (result.stdout + result.stderr).strip()
    status = "PASSED" if result.returncode == 0 else "FAILED"
    report = (
        "# Task 5 test report\n\n"
        f"- **Command:** `{command}`\n"
        f"- **Result:** {status} (exit code {result.returncode})\n\n"
        "## Output\n\n"
        "```text\n"
        f"{output or '(no test output)'}\n"
        "```\n"
    )
    REPORT_PATH.write_text(report, encoding="utf-8")


def run(tasks_path, repository, embeddings_path, vocabulary_path, model_name):
    if not repository.is_dir():
        raise NotADirectoryError(f"Repository directory does not exist: {repository}")
    if not embeddings_path.is_file() or not vocabulary_path.is_file():
        raise FileNotFoundError(
            "Task 3 embeddings are missing. Generate them with "
            "`Week_06_Implementation\\Assignments\\Task_3\\embed_chunks.py`."
        )
    tasks = load_tasks(tasks_path)
    settings = read_settings(TASK_DIRECTORY / ".env")
    model = create_model(model_name, settings)
    retriever = load_task3_module()
    staged_sources = {}

    for index, task in enumerate(tasks, 1):
        target = validate_task_path(repository, task["file"])
        original_source = staged_sources.get(target, target.read_text(encoding="utf-8"))
        method = locate_method(original_source, task["class"], task["method"])
        current_method = method_source(original_source, method)
        query = f"{task['class']} {task['method']} {task['docstring']}"
        retrieved = retriever.search_csv(query, embeddings_path, vocabulary_path, 5)
        tests = matching_test_context(PROJECT_DIRECTORY, task)
        prompt = task_prompt(task, current_method, retrieved, tests)
        print(f"[{index}/{len(tasks)}] Generating {task['class']}.{task['method']} ({task['file']})")
        _, updated_source = generate_valid_method(
            model, prompt, original_source, task["class"], task["method"]
        )
        staged_sources[target] = updated_source

    for path, contents in staged_sources.items():
        write_atomically(path, contents)
        print(f"Updated {path.relative_to(repository)}")

    command = f"{sys.executable} -m pytest -q"
    print(f"Running tests: {command}")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=PROJECT_DIRECTORY,
        capture_output=True,
        text=True,
        check=False,
    )
    write_test_report(result, command)
    print(f"Tests {'passed' if result.returncode == 0 else 'failed'}; report: {REPORT_PATH}")
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Implement the listed coding tasks using TF-IDF retrieval and an allowed LLM."
    )
    parser.add_argument("--tasks", type=Path, default=TASKS_PATH)
    parser.add_argument("--repository", type=Path, default=REPOSITORY_DIRECTORY)
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS_PATH)
    parser.add_argument("--vocabulary", type=Path, default=VOCABULARY_PATH)
    parser.add_argument("--model", choices=ALLOWED_MODELS, default="gpt-4o-mini")
    args = parser.parse_args()
    try:
        return run(
            args.tasks,
            args.repository,
            args.embeddings,
            args.vocabulary,
            args.model,
        )
    except (EnvironmentError, FileNotFoundError, ImportError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
