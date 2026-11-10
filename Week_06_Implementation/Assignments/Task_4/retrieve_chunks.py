import argparse
import importlib.util
from pathlib import Path


TASK_3_DIRECTORY = Path(__file__).resolve().parents[1] / "Task_3"
TASK_3_SCRIPT = TASK_3_DIRECTORY / "embed_chunks.py"
EMBEDDINGS_PATH = TASK_3_DIRECTORY / "chunk_embeddings.csv"
VOCABULARY_PATH = TASK_3_DIRECTORY / "tfidf_vocabulary.csv"

spec = importlib.util.spec_from_file_location("task3_embed_chunks", TASK_3_SCRIPT)
if spec is None or spec.loader is None:
    raise ImportError(f"Unable to load Task 3 embedding module: {TASK_3_SCRIPT}")
task3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(task3)


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve repository chunks most relevant to a coding task."
    )
    parser.add_argument("query", help="Coding task or question to search for.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of matching chunks to display (default: 5).",
    )
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS_PATH)
    parser.add_argument("--vocabulary", type=Path, default=VOCABULARY_PATH)
    args = parser.parse_args()

    if not args.query.strip():
        parser.error("query must not be empty")
    if args.top_k < 1:
        parser.error("--top-k must be at least 1")
    if not args.embeddings.is_file():
        parser.error(f"Embedding CSV does not exist: {args.embeddings}")
    if not args.vocabulary.is_file():
        parser.error(f"Vocabulary CSV does not exist: {args.vocabulary}")

    results = task3.search_csv(
        args.query,
        args.embeddings,
        args.vocabulary,
        args.top_k,
    )
    if not results:
        print("No chunks found.")
        return

    for rank, (score, chunk) in enumerate(results, start=1):
        print(
            f"{rank}. similarity={score:.4f}  "
            f"{chunk['file']}:{chunk['start_line']}-{chunk['end_line']}"
        )
        print(chunk["text"].rstrip())
        print()

    if all(score == 0 for score, _ in results):
        print("No query terms matched the stored vocabulary; all scores are zero.")


if __name__ == "__main__":
    main()
