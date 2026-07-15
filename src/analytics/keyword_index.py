"""Build own keyword rankings and reverse word search from repo/content corpus."""
import re
from collections import Counter, defaultdict
from typing import List, Optional


STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "are", "was", "were", "been", "have", "has", "had",
    "will", "would", "could", "should", "may", "might", "must", "can", "cannot", "not", "but", "than", "then",
    "they", "them", "their", "there", "these", "those", "you", "your", "our", "its", "his", "her", "she", "he",
    "into", "onto", "upon", "about", "above", "below", "under", "over", "again", "further", "once", "here", "when",
    "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "only",
    "own", "same", "so", "than", "too", "very", "just", "now", "also", "use", "using", "used", "one", "two", "new",
    "make", "made", "get", "got", "add", "added", "need", "needs", "like", "want", "way", "work", "works"
}


class KeywordIndex:
    def __init__(self):
        self.term_counts = Counter()
        self.term_locations = defaultdict(list)
        self.doc_count = 0

    def _tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        return [t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]{2,}", text.lower())
                if t not in STOPWORDS and len(t) < 40]

    def add_document(self, doc_id: str, text: str, doc_type: str, weight: float = 1.0):
        """Index a document. weight boosts score for title/README vs body."""
        tokens = self._tokenize(text)
        counts = Counter(tokens)
        self.doc_count += 1
        for term, c in counts.items():
            self.term_counts[term] += c * weight
            self.term_locations[term].append({"id": doc_id, "type": doc_type, "count": c})

    def add_repo(self, repo: dict, weight: float = 1.5):
        text = " ".join(filter(None, [
            repo.get("name", ""),
            repo.get("next", ""),
            repo.get("description", ""),
            repo.get("readme", "")[:2000],
        ]))
        self.add_document(repo.get("name", "unknown"), text, "repo", weight)

    def add_walkthrough(self, wt: dict, weight: float = 1.0):
        text = " ".join(filter(None, [
            wt.get("title", ""),
            wt.get("description", ""),
            " ".join(wt.get("tags", [])),
            wt.get("content", "")[:5000],
        ]))
        self.add_document(wt.get("title", "unknown"), text, "walkthrough", weight)

    def add_card(self, card: dict, weight: float = 1.2):
        text = " ".join(filter(None, [
            card.get("name", ""),
            card.get("tagline", ""),
            card.get("category", ""),
            card.get("why_use", ""),
            " ".join(card.get("tags", []) if isinstance(card.get("tags"), list) else []),
        ]))
        self.add_document(card.get("name", "unknown"), text, "workflow_card", weight)

    def rankings(self, top_n: int = 50) -> List[dict]:
        total = sum(self.term_counts.values()) or 1
        ranked = sorted(self.term_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {"term": term, "score": round(count / total * 100, 2), "mentions": len(self.term_locations[term])}
            for term, count in ranked[:top_n]
        ]

    def reverse_search(self, query: str) -> List[dict]:
        query_terms = self._tokenize(query)
        if not query_terms:
            return []
        # Score documents by sum of matched term counts
        doc_scores = defaultdict(float)
        doc_meta = {}
        for term in query_terms:
            for loc in self.term_locations.get(term, []):
                doc_scores[loc["id"]] += loc["count"]
                doc_meta[loc["id"]] = loc["type"]
        return [
            {"id": doc_id, "type": doc_meta.get(doc_id, "unknown"), "relevance": round(score, 2)}
            for doc_id, score in sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        ]
