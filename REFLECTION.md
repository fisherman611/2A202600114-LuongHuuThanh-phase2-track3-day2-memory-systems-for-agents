# Reflection: Privacy and Limitations

## Which memory helps most?

Semantic memory helps most for technical QA because it retrieves exact chunks from docs/FAQ and reduces hallucination.

## Which memory is most sensitive?

Long-term profile memory is most sensitive because it may store personal facts (name, location, allergy). If retrieved into wrong prompt context, it can leak PII.

## Privacy risks identified

1. PII retention risk: user profile and episodes can persist longer than needed.
2. Cross-session leakage risk: profile facts may be injected into unrelated conversations.
3. Wrong retrieval risk: incorrect semantic hit may produce unsafe advice.

## Deletion / TTL / Consent policy

1. Deletion:
   - Profile: delete or overwrite key in `data/profile.json`.
   - Episodic: remove entries in `data/episodes.json`.
   - Semantic: delete chunk from `data/semantic_docs.json` and rebuild FAISS index.
2. TTL:
   - Episodic entries should have TTL (for example 30 days) unless explicitly pinned.
3. Consent:
   - Ask user before storing sensitive facts (health, identity, contact, finance).

## Technical limitations of current solution

1. Extraction is regex-based, so complex language can be missed or parsed incorrectly.
2. Token budget uses word-count heuristic, not true tokenizer counting.
3. FAISS embedding is deterministic hash embedding; it is lightweight but less accurate than model-based embeddings.
4. No concurrency control for simultaneous writes to JSON files.
5. No full access-control layer; memory scope is local-process only.
