"""Retrieval over the small Markdown knowledge base.

Uses sentence-transformers (all-MiniLM-L6-v2) when installed. If it isn't available,
falls back to a simple TF-IDF search so the app still runs (and so the logic can be tested).
"""
import os
import re
from pathlib import Path

import numpy as np

SEARCH_API = 4  # bumped when search() gained min_score; app.py checks it
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_STOP = set("a an and are as at be but by can do does for from how i if in is it me my of on or so that the this to was what when which with you your about tell give show some any there would could should also get make me please".split())


def _tokens(text):
    return [w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in _STOP]


_META = re.compile(r"^(Category|Keywords|Summary):\s*(.*)$")


def _parse_note(raw, stem):
    """Split a note into (title, meta, body). Optional header lines after the title:
    Category: workout, wellness / Keywords: a, b, c / Summary: one sentence."""
    lines = raw.strip().splitlines()
    has_title = bool(lines) and lines[0].startswith("#")
    title = lines[0].lstrip("# ").strip() if has_title else stem
    meta, body, in_meta = {}, [], True
    for ln in (lines[1:] if has_title else lines):
        m = _META.match(ln.strip())
        if in_meta and m:
            meta[m.group(1).lower()] = m.group(2).strip()
        elif in_meta and not ln.strip():
            continue
        else:
            in_meta = False
            body.append(ln)
    return title, meta, "\n".join(body).strip()


def load_chunks(folder, max_words=180):
    """Split each .md note into passages of roughly max_words words."""
    chunks = []
    for path in sorted(Path(folder).glob("*.md")):
        title, meta, body = _parse_note(path.read_text(encoding="utf-8"), path.stem)
        cats = {c.strip() for c in meta.get("category", "").split(",") if c.strip()}
        head = f"{title}. " + (meta["summary"] + " " if meta.get("summary") else "")
        extra = meta.get("keywords", "")
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        cur, count = [], 0

        def flush():
            text = head + " ".join(cur)
            chunks.append({"source": title, "stem": path.stem, "categories": cats, "text": text, "index": text + " " + extra})

        for p in paras:
            w = len(p.split())
            if cur and count + w > max_words:
                flush()
                cur, count = [], 0
            cur.append(p)
            count += w
        if cur:
            flush()
    return chunks


class Retriever:
    def __init__(self, folder="knowledge", prefer_embeddings=True):
        self.chunks = load_chunks(folder)
        self.backend = "tfidf"
        self.threshold = 0.08
        if prefer_embeddings and os.environ.get("FITBUDDY_NO_EMBED") != "1":
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(EMBED_MODEL)
                self._vecs = self._model.encode([c["index"] for c in self.chunks], normalize_embeddings=True)
                self.backend, self.threshold = "embeddings", 0.25
            except Exception as e:
                print(f"[FitBuddy] Embedding model unavailable ({e}); using simple keyword search instead.", flush=True)
        if self.backend == "tfidf":
            self._build_tfidf()

    # --- TF-IDF fallback ---
    def _build_tfidf(self):
        docs = [_tokens(c["source"]) * 3 + _tokens(c["index"]) for c in self.chunks]  # title words count extra
        vocab = {}
        for d in docs:
            for w in set(d):
                vocab.setdefault(w, len(vocab))
        n = len(docs)
        df = np.zeros(len(vocab))
        for d in docs:
            for w in set(d):
                df[vocab[w]] += 1
        self._vocab = vocab
        self._idf = np.log((n + 1) / (df + 1)) + 1
        self._vecs = np.vstack([self._tfidf_vec(d) for d in docs])

    def _tfidf_vec(self, toks):
        v = np.zeros(len(self._vocab))
        for w in toks:
            if w in self._vocab:
                v[self._vocab[w]] += 1
        v = (1 + np.log(v, where=v > 0, out=np.zeros_like(v))) * (v > 0) * self._idf
        norm = np.linalg.norm(v)
        return v / norm if norm else v

    def get(self, ids):
        """Fetch passages by id (used to re-use the same notes for a follow-up like 'make it shorter')."""
        return [{"id": int(i), "source": self.chunks[i]["source"], "text": self.chunks[i]["text"], "score": 1.0}
                for i in ids if 0 <= i < len(self.chunks)]

    def search(self, query, k=3, category=None, min_score=None):
        """Return up to k passages above the relevance threshold, best first.
        With a category ('workout', 'meal', 'wellness') only notes tagged with it are considered.
        min_score overrides the relevance cutoff (0.0 = no cutoff, used for generic requests like 'Meal ideas')."""
        cutoff = self.threshold if min_score is None else min_score
        if self.backend == "embeddings":
            q = self._model.encode([query], normalize_embeddings=True)[0]
        else:
            q = self._tfidf_vec(_tokens(query))
        scores = self._vecs @ q
        out = []
        for i in np.argsort(-scores):
            if scores[i] < cutoff or len(out) >= k:
                break
            if category and category not in self.chunks[i]["categories"]:
                continue
            out.append({"id": int(i), "source": self.chunks[i]["source"], "text": self.chunks[i]["text"], "score": float(scores[i])})
        return out
