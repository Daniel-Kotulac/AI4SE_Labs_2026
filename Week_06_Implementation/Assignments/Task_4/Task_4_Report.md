# Retrieval design report

`retrieve_chunks.py` accepts a coding task as a query, embeds it with the same TF-IDF vocabulary and weights used for the stored chunks, then calculates cosine similarity against the chunk vectors in Task 3's CSV. It prints the top *k* matches with their similarity scores, source paths, line ranges, and text; `--top-k` controls how many are returned.

The script reuses Task 3's tokenizer, query-vector generation, and cosine-similarity implementation so retrieval stays consistent with the stored embeddings and avoids duplicating the algorithm. TF-IDF and cosine similarity are simple, dependency-free choices that work well for a small repository when query terms overlap code identifiers or text. Unlike semantic embedding models, TF-IDF may miss relevant chunks phrased with different terms.

Run the retriever from the repository root, for example:

```powershell
python "Week_06_Implementation\Assignments\Task_4\retrieve_chunks.py" "validate orders inventory" --top-k 5
```
