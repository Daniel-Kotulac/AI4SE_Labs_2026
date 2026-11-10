import argparse
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path


TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|\d+")
CHUNKS_PATH = Path(__file__).resolve().parents[1] / "Task_2" / "chunks.json"
EMBEDDINGS_PATH = Path(__file__).resolve().parent / "chunk_embeddings.csv"
VOCABULARY_PATH = Path(__file__).resolve().parent / "tfidf_vocabulary.csv"
EMBEDDING_FIELDS = (
    "chunk_id",
    "file",
    "chunk_index",
    "start_line",
    "end_line",
    "text",
    "embedding",
)


def tokenize(text):
    return TOKEN_PATTERN.findall(text.lower())


def _normalized_vector(term_counts, token_count, idf):
    if not token_count:
        return {}

    weights = {
        term: count / token_count * idf[term]
        for term, count in term_counts.items()
        if term in idf
    }
    magnitude = math.sqrt(sum(weight * weight for weight in weights.values()))
    if not magnitude:
        return {}
    return {term: weight / magnitude for term, weight in weights.items()}


def build_embeddings(chunks):
    tokenized_chunks = [tokenize(chunk["text"]) for chunk in chunks]
    document_frequencies = Counter(
        term for tokens in tokenized_chunks for term in set(tokens)
    )
    document_count = len(chunks)
    idf = {
        term: math.log((document_count + 1) / (frequency + 1)) + 1
        for term, frequency in sorted(document_frequencies.items())
    }

    vectors = []
    for tokens in tokenized_chunks:
        vectors.append(_normalized_vector(Counter(tokens), len(tokens), idf))
    return vectors, idf


def embed_query(query, idf):
    tokens = tokenize(query)
    return _normalized_vector(Counter(tokens), len(tokens), idf)


def cosine_similarity(first, second):
    if len(first) > len(second):
        first, second = second, first
    return sum(weight * second.get(term, 0.0) for term, weight in first.items())


def write_csv_files(chunks, vectors, idf, embeddings_path, vocabulary_path):
    embeddings_path.parent.mkdir(parents=True, exist_ok=True)
    vocabulary_path.parent.mkdir(parents=True, exist_ok=True)

    with embeddings_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=EMBEDDING_FIELDS)
        writer.writeheader()
        for index, (chunk, vector) in enumerate(zip(chunks, vectors), start=1):
            writer.writerow(
                {
                    "chunk_id": index,
                    "file": chunk["file"],
                    "chunk_index": chunk["chunk_index"],
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                    "text": chunk["text"],
                    "embedding": json.dumps(vector, sort_keys=True),
                }
            )

    with vocabulary_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=("term", "idf"))
        writer.writeheader()
        writer.writerows({"term": term, "idf": value} for term, value in idf.items())


def search_csv(query, embeddings_path, vocabulary_path, top_k):
    with vocabulary_path.open(encoding="utf-8", newline="") as source:
        idf = {row["term"]: float(row["idf"]) for row in csv.DictReader(source)}
    query_vector = embed_query(query, idf)

    results = []
    with embeddings_path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            vector = json.loads(row["embedding"])
            score = cosine_similarity(query_vector, vector)
            results.append((score, row))
    return sorted(results, key=lambda result: result[0], reverse=True)[:top_k]


def main():
    parser = argparse.ArgumentParser(
        description="Build TF-IDF embeddings for repository chunks and store them as CSV."
    )
    parser.add_argument("--chunks", type=Path, default=CHUNKS_PATH)
    parser.add_argument("--output", type=Path, default=EMBEDDINGS_PATH)
    parser.add_argument("--vocabulary", type=Path, default=VOCABULARY_PATH)
    parser.add_argument("--query", help="Optionally search the generated embeddings.")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if not args.chunks.is_file():
        parser.error(f"Chunk data file does not exist: {args.chunks}")
    if args.top_k < 1:
        parser.error("--top-k must be at least 1")

    with args.chunks.open(encoding="utf-8") as source:
        chunks = json.load(source)
    if not chunks:
        parser.error(f"No chunks found in {args.chunks}")

    vectors, idf = build_embeddings(chunks)
    write_csv_files(chunks, vectors, idf, args.output, args.vocabulary)
    print(
        f"Wrote {len(chunks)} chunk embeddings to {args.output} "
        f"and {len(idf)} vocabulary terms to {args.vocabulary}"
    )

    if args.query:
        for score, row in search_csv(args.query, args.output, args.vocabulary, args.top_k):
            print(f"{score:.4f}  {row['file']}:{row['start_line']}-{row['end_line']}")


if __name__ == "__main__":
    main()
