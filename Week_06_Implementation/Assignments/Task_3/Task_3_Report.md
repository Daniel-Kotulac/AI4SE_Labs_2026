# Embedding and storage report

The script `embed_chunks.py` creates **TF-IDF** vectors from each chunk's text using a lowercase word/identifier tokenizer. It calculates term frequency and smoothed inverse document frequency across the chunk collection, then L2-normalizes each vector. The resulting vectors can be compared with cosine similarity; the script also supports a simple `--query` search.

Chunk text, source path, line range, and each sparse term-weight vector are stored in `chunk_embeddings.csv`. The companion `tfidf_vocabulary.csv` stores each term's IDF weight, which is needed to vectorize future queries using the same feature space. The script uses only the Python standard library, so it avoids model downloads, API keys, and additional dependencies.

TF-IDF was chosen as a lightweight traditional text-feature approach that runs locally and is easy to inspect. It works well when queries and code chunks share meaningful words or identifiers, but it does not understand synonyms or deeper semantic similarity like a pretrained embedding model. Sparse vectors are encoded as JSON inside a CSV field for portability; this is convenient at this repository's scale, but is less efficient than a dedicated vector index for large collections.
