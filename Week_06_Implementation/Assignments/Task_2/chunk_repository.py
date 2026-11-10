import argparse
import json
import re
from pathlib import Path


CHUNK_SIZE = 750
OVERLAP_SIZE = 100
TEXT_EXTENSIONS = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SKIP_DIRECTORIES = {".git", ".pytest_cache", ".venv", "__pycache__", "node_modules"}
TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
STRUCTURE_PATTERN = re.compile(r"^\s*(?:(?:async\s+)?def\s+\w|class\s+\w|#{1,6}\s)")


def estimate_tokens(text):
    return len(TOKEN_PATTERN.findall(text))


def _make_block(lines, start_line):
    text = "".join(lines)
    return {
        "text": text,
        "start_line": start_line,
        "end_line": start_line + len(lines) - 1,
        "tokens": estimate_tokens(text),
    }


def _logical_blocks(lines):
    blocks = []
    current = []
    start_line = 1

    for line_number, line in enumerate(lines, start=1):
        structural_start = STRUCTURE_PATTERN.match(line) is not None
        if current and (not line.strip() or structural_start):
            if not structural_start:
                current.append(line)
            blocks.append(_make_block(current, start_line))
            current = []
            if not line.strip():
                start_line = line_number + 1
                continue

        if not current:
            start_line = line_number
        current.append(line)

    if current:
        blocks.append(_make_block(current, start_line))
    return blocks


def _split_long_line(line, line_number):
    matches = list(TOKEN_PATTERN.finditer(line))
    if len(matches) <= CHUNK_SIZE:
        return [_make_block([line], line_number)]

    pieces = []
    start = 0
    for token_index in range(CHUNK_SIZE, len(matches), CHUNK_SIZE):
        boundary = matches[token_index].start()
        pieces.append(_make_block([line[start:boundary]], line_number))
        start = boundary
    pieces.append(_make_block([line[start:]], line_number))
    return pieces


def _split_oversized_block(block):
    if block["tokens"] <= CHUNK_SIZE:
        return [block]

    pieces = []
    current_lines = []
    current_start = block["start_line"]
    current_tokens = 0
    for offset, line in enumerate(block["text"].splitlines(keepends=True)):
        line_number = block["start_line"] + offset
        line_tokens = estimate_tokens(line)
        if line_tokens > CHUNK_SIZE:
            if current_lines:
                pieces.append(_make_block(current_lines, current_start))
                current_lines = []
                current_tokens = 0
            pieces.extend(_split_long_line(line, line_number))
        elif current_lines and current_tokens + line_tokens > CHUNK_SIZE:
            pieces.append(_make_block(current_lines, current_start))
            current_lines = [line]
            current_start = line_number
            current_tokens = line_tokens
        else:
            if not current_lines:
                current_start = line_number
            current_lines.append(line)
            current_tokens += line_tokens

    if current_lines:
        pieces.append(_make_block(current_lines, current_start))
    return pieces


def _chunks_for_file(path, relative_path):
    text = path.read_text(encoding="utf-8")
    blocks = []
    for block in _logical_blocks(text.splitlines(keepends=True)):
        blocks.extend(_split_oversized_block(block))

    chunks = []
    start = 0
    while start < len(blocks):
        end = start
        token_count = 0
        while end < len(blocks) and token_count + blocks[end]["tokens"] <= CHUNK_SIZE:
            token_count += blocks[end]["tokens"]
            end += 1

        if end == start:
            raise RuntimeError(f"Unable to fit a text block into a chunk for {relative_path}")

        selected = blocks[start:end]
        chunks.append(
            {
                "file": relative_path,
                "start_line": selected[0]["start_line"],
                "end_line": selected[-1]["end_line"],
                "estimated_tokens": token_count,
                "text": "".join(block["text"] for block in selected),
            }
        )

        if end == len(blocks):
            break

        next_start = end
        overlap_tokens = 0
        while next_start > start and overlap_tokens + blocks[next_start - 1]["tokens"] <= OVERLAP_SIZE:
            next_start -= 1
            overlap_tokens += blocks[next_start]["tokens"]
        start = next_start if start < next_start < end else end

    for index, chunk in enumerate(chunks, start=1):
        chunk["chunk_index"] = index
    return chunks


def collect_chunks(source):
    chunks = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(source).parts
        if any(part in SKIP_DIRECTORIES for part in relative_parts[:-1]):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name != ".gitignore":
            continue
        chunks.extend(_chunks_for_file(path, path.relative_to(source).as_posix()))
    return chunks


def main():
    parser = argparse.ArgumentParser(description="Chunk a source repository for RAG indexing.")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "AI4SE_Playground",
        help="Repository directory to chunk.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "chunks.json",
        help="JSON file to write the chunks to.",
    )
    args = parser.parse_args()

    if not args.source.is_dir():
        parser.error(f"Source directory does not exist: {args.source}")

    chunks = collect_chunks(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(chunks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(chunks)} chunks from {args.source} to {args.output}")


if __name__ == "__main__":
    main()
