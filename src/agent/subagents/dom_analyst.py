"""DOM Analyst sub-agent for element selection."""

from typing import Any

from src.app.i18n import t
from src.app.logging import RunLogger
from src.llm.base import LLMProvider


class DOMAnalyst:
    """
    Sub-agent specialized in analyzing DOM elements and selecting
    the best candidate for a given intent.
    """

    def __init__(self, llm: LLMProvider, logger: RunLogger):
        self.llm = llm
        self.logger = logger

    async def analyze_candidates(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        context: str = "",
    ) -> dict[str, Any]:
        """
        Analyze candidates and select the best match for the query.

        Args:
            query: What the user wants to interact with
            candidates: List of candidate elements from query_dom
            context: Additional context about the task

        Returns:
            dict with 'selected_id', 'selector', and 'confidence'
        """
        self.logger.log_subagent("DOM", t("dom_processing_query", query=query))

        if not candidates:
            self.logger.log_subagent("DOM", t("dom_no_candidates"))
            return {
                "selected_id": None,
                "selector": None,
                "confidence": 0.0,
                "reason": t("dom_no_candidates"),
            }

        # Use heuristic scoring for simple cases
        scored = self._score_candidates(query, candidates)

        if scored and scored[0]["score"] > 0.8:
            # High confidence match - use directly
            best = scored[0]
            self.logger.log_subagent(
                "DOM",
                t("dom_high_confidence", id=best["id"], text=best.get("text", "")[:30]),
            )
            return {
                "selected_id": best["id"],
                "selector": best["selector"],
                "confidence": best["score"],
                "reason": "High confidence heuristic match",
            }

        # For ambiguous cases, use LLM
        if len(scored) > 1 and scored[0]["score"] < 0.5:
            self.logger.log_subagent("DOM", t("dom_low_confidence"))
            return await self._llm_select(query, candidates, context)

        # Return best heuristic match
        if scored:
            best = scored[0]
            self.logger.log_subagent(
                "DOM",
                t("dom_selected", id=best["id"], score=best["score"]),
            )
            return {
                "selected_id": best["id"],
                "selector": best["selector"],
                "confidence": best["score"],
                "reason": "Best heuristic match",
            }

        return {
            "selected_id": None,
            "selector": None,
            "confidence": 0.0,
            "reason": "No suitable match found",
        }

    def _score_candidates(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Score candidates by relevance to query."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for c in candidates:
            score = 0.0

            # Get all text fields
            text_fields = [
                c.get("text", "").lower(),
                c.get("aria_label", "").lower(),
                c.get("placeholder", "").lower(),
                c.get("name", "").lower(),
            ]

            combined_text = " ".join(text_fields)

            # Exact match bonus
            for field in text_fields:
                if query_lower == field:
                    score = 1.0
                    break

            # Contains match
            if score < 1.0:
                for field in text_fields:
                    if query_lower in field:
                        score = max(score, 0.8)
                    elif field in query_lower:
                        score = max(score, 0.7)

            # Word overlap
            if score < 0.7:
                combined_words = set(combined_text.split())
                overlap = len(query_words & combined_words)
                if query_words:
                    word_score = overlap / len(query_words) * 0.6
                    score = max(score, word_score)

            # Role relevance bonus
            role = c.get("role", "").lower()
            if "button" in query_lower and "button" in role:
                score += 0.1
            if "input" in query_lower and "input" in role:
                score += 0.1
            if "link" in query_lower and ("link" in role or "a" == role):
                score += 0.1

            # Viewport bonus - prefer visible elements
            if c.get("in_viewport", False):
                score += 0.05

            scored.append({**c, "score": min(score, 1.0)})

        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    async def _llm_select(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        context: str,
    ) -> dict[str, Any]:
        """Use LLM to select best candidate for ambiguous cases."""
        # Format candidates for LLM
        candidates_text = []
        for i, c in enumerate(candidates[:8]):  # Limit to 8 for context
            text = c.get("text", "")[:50]
            role = c.get("role", "unknown")
            aria = c.get("aria_label", "")
            placeholder = c.get("placeholder", "")

            desc_parts = [f"[{i}] {role}: \"{text}\""]
            if aria:
                desc_parts.append(f"aria-label=\"{aria}\"")
            if placeholder:
                desc_parts.append(f"placeholder=\"{placeholder}\"")

            candidates_text.append(" ".join(desc_parts))

        prompt = f"""Select the element that best matches: "{query}"

Candidates:
{chr(10).join(candidates_text)}

{f"Context: {context}" if context else ""}

Reply with just the number (e.g., "0" or "2") or "none" if no match."""

        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                tools=[],
                system_prompt="You are a DOM element selector. Be concise.",
            )

            content = (response.content or "").strip().lower()

            # Parse response
            if content == "none":
                return {
                    "selected_id": None,
                    "selector": None,
                    "confidence": 0.0,
                    "reason": "LLM found no match",
                }

            # Try to extract number
            for char in content:
                if char.isdigit():
                    idx = int(char)
                    if 0 <= idx < len(candidates):
                        return {
                            "selected_id": candidates[idx].get("id", idx),
                            "selector": candidates[idx].get("selector"),
                            "confidence": 0.7,
                            "reason": "LLM selection",
                        }
                    break

        except Exception as e:
            self.logger.log_error(f"DOM Analyst LLM error: {e}")

        # Fallback to first candidate
        if candidates:
            return {
                "selected_id": candidates[0].get("id", 0),
                "selector": candidates[0].get("selector"),
                "confidence": 0.3,
                "reason": "Fallback to first candidate",
            }

        return {
            "selected_id": None,
            "selector": None,

            "confidence": 0.0,
            "reason": "Analysis failed",
        }
