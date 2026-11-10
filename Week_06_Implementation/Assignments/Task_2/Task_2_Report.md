# Chunking report

The repository is split into JSON chunks, with each entry recording its source file, line range, estimated token count, and text. The chunker targets **750 tokens** per chunk, with up to **100 tokens of overlap** between adjacent chunks from the same file.

This medium-sized target balances focused retrieval against retaining enough surrounding code and explanation to be useful for coding tasks. The overlap helps preserve context when a relevant function or explanation falls near a chunk boundary.

The splitter groups content at blank lines and recognizable Python function/class or Markdown heading boundaries, then packs those groups up to the target size. Oversized groups are divided at line boundaries; exceptionally long lines are divided at token boundaries. It processes readable source and documentation files and skips common generated or dependency directories.

Token counts are estimates based on words and punctuation, not a model-specific tokenizer. This keeps the script dependency-free; the chosen chunk size is therefore an approximate RAG context budget.
