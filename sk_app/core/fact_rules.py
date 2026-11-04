"""Pure matching for known facts (no Frappe imports; tests in tests/test_fact_rules.py)."""

import re

STOP = {"the", "and", "for", "with", "what", "which", "who", "how", "are", "was", "this", "that", "please", "pl", "can", "should",
	"from", "has", "have", "you", "our", "any", "all", "not", "but", "his", "her", "its", "will", "there", "where", "when"}


def words(text: str) -> list[str]:
	out = [w for w in re.findall(r"[\wऀ-ॿ]+", (text or "").lower()) if len(w) > 2 and w not in STOP]
	return list(dict.fromkeys(out))[:12]


def score(query_words: list[str], topic: str, text: str) -> int:
	"""0 = no match. Short queries (1-2 words) need every word; longer ones a third of them. Topic words count double."""
	if not query_words:
		return 1
	low_topic, low = (topic or "").lower(), f"{topic} {text}".lower()
	hits = [w for w in query_words if w in low]
	need = len(query_words) if len(query_words) <= 2 else max(2, len(query_words) // 3)
	if len(hits) < need:
		return 0
	return len(hits) + sum(w in low_topic for w in hits)
