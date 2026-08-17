"""
Automated topic research and candidate scoring.

Uses the OpenAI Responses API with web_search_preview to research current
Los Angeles real estate conditions, then scores and selects the best three
topics (one per article type: A=timely, B=evergreen, C=authority/investment).
"""
import json
import os
import re
from datetime import date

CANDIDATE_COUNT = 12  # how many candidates to generate before scoring

ARTICLE_TYPE_DESCRIPTIONS = {
    "A": "Timely / Market Intelligence — current LA market changes, legislation, mortgage environment, insurance, housing policy, inventory shifts",
    "B": "Evergreen Search / Consumer Education — durable buyer/seller/owner guides: financing, neighborhoods, inspections, HOA, offer strategy, closing costs",
    "C": "Authority / Investment — analytical topics: duplexes, multifamily, investment strategy, house hacking, rental economics, value-add, development potential",
}

SCORING_DIMENSIONS = """
Score each topic 1-10 on each dimension. Be honest and specific.
- relevance_to_business: How directly does this serve a Los Angeles real estate buyer, seller, landlord, or investor?
- la_specificity: How specific to Los Angeles is this (vs. generic national real estate)?
- client_usefulness: How immediately actionable or clarifying is this for a prospective client?
- search_intent: Does a real person plausibly search for this? Is the intent clear?
- evergreen_seo: Will this topic still be valuable in 12-18 months?
- timeliness: Is there a time-sensitive reason to cover this now?
- authority_building: Does this demonstrate specialist expertise that generic agents could not write?
- differentiation: Is this meaningfully different from what other agents typically publish?
- internal_linking: Does this naturally connect to other content on the site?
- duplication_risk: (INVERSE — score 10 if no risk, 1 if high duplication risk vs. existing articles)
- factual_sourcing: Are there reliable, authoritative sources for the claims this article would need to make?
"""


def build_research_prompt(existing_articles: list, today: date, candidate_count: int) -> str:
    existing_summary = "\n".join(
        f"- [{a['article_type']}] {a['title']} ({a['category']}, {a['date_iso']})"
        for a in sorted(existing_articles, key=lambda x: x["date_iso"], reverse=True)
    )

    return f"""Today is {today.strftime('%B %d, %Y')}.

You are the editorial research system for paulsellsproperties.com, the website of Paul Adams II, a Los Angeles real estate agent at Coldwell Banker Realty Beverly Hills.

EXISTING ARTICLES ALREADY PUBLISHED (do not substantially duplicate these):
{existing_summary}

YOUR TASK:
1. Research current Los Angeles real estate conditions, market news, legislation, financing trends, and consumer questions using web search where helpful.
2. Generate exactly {candidate_count} candidate article topics. Aim for roughly this distribution: 4 Type A (timely), 5 Type B (evergreen), 3 Type C (investment/authority). Do not force a weak topic just to fill a category.
3. Score each candidate on the dimensions below.
4. Recommend the best 3 topics, one from each type if quality allows — but topic quality matters more than forcing the mix.

ARTICLE TYPES:
- A: {ARTICLE_TYPE_DESCRIPTIONS['A']}
- B: {ARTICLE_TYPE_DESCRIPTIONS['B']}
- C: {ARTICLE_TYPE_DESCRIPTIONS['C']}

SCORING DIMENSIONS (rate each 1-10):
{SCORING_DIMENSIONS}

Do NOT suggest topics that substantially overlap existing articles.
Avoid near-duplicate keyword targeting.

Return valid JSON in this exact structure:
{{
  "research_notes": "2-3 sentences on what you found about current LA real estate conditions and what this suggests for content priorities",
  "candidates": [
    {{
      "topic": "Concise topic description (not the headline)",
      "suggested_headline": "A specific, clear article headline",
      "article_type": "A|B|C",
      "category": "one of: Buyer's Guide | Buyer Strategy | Market Analysis | Landlord & Rental Laws | Real Estate Investing | Condo / HOA | Seller Strategy",
      "primary_keyword": "the main search query this targets",
      "rationale": "Why this topic, why now, why it is not a duplicate",
      "key_sources": ["source 1", "source 2"],
      "scores": {{
        "relevance_to_business": 0,
        "la_specificity": 0,
        "client_usefulness": 0,
        "search_intent": 0,
        "evergreen_seo": 0,
        "timeliness": 0,
        "authority_building": 0,
        "differentiation": 0,
        "internal_linking": 0,
        "duplication_risk": 0,
        "factual_sourcing": 0
      }}
    }}
  ],
  "recommended": {{
    "type_a": "index of the best Type A candidate (0-based)",
    "type_b": "index of the best Type B candidate (0-based)",
    "type_c": "index of the best Type C candidate (0-based)"
  }}
}}"""


def research_topics(client, existing_articles: list, cfg: dict, manual_topics: list = None) -> list:
    """
    Return a list of up to 3 selected topic dicts for article generation.
    Uses manual_topics as overrides if provided, fills remaining slots from AI research.
    """
    today = date.today()
    slots_needed = cfg.get("articles_per_run", 3)
    model = cfg.get("research_model", "gpt-4o")

    selected = []

    # Use manual overrides first (up to slots_needed)
    if manual_topics:
        for mt in manual_topics[:slots_needed]:
            selected.append({
                "topic": mt.get("topic", ""),
                "suggested_headline": mt.get("suggested_headline", mt.get("topic", "")),
                "article_type": mt.get("article_type", "B"),
                "category": mt.get("category", "Buyer's Guide"),
                "primary_keyword": mt.get("primary_keyword", ""),
                "rationale": "Manually specified override topic",
                "key_sources": mt.get("key_sources", []),
                "scores": {},
                "is_manual": True,
            })
        if len(selected) >= slots_needed:
            return selected[:slots_needed]

    slots_from_research = slots_needed - len(selected)
    if slots_from_research <= 0:
        return selected

    # AI research
    candidate_count = max(cfg.get("candidate_topic_count", 12), slots_from_research * 4)
    prompt = build_research_prompt(existing_articles, today, candidate_count)

    print(f"[topic_research] Calling {model} for topic research with web search...")

    try:
        # Use Responses API with web_search_preview for current market context
        response = client.responses.create(
            model=model,
            tools=[{"type": "web_search_preview"}],
            input=prompt,
            text={"format": {"type": "text"}},
        )
        raw = response.output_text
    except Exception as e:
        # Fall back to chat completions if Responses API unavailable
        print(f"[topic_research] Responses API unavailable ({e}), falling back to chat completions")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        raw = response.choices[0].message.content

    # Parse JSON (may be wrapped in markdown code fence)
    json_match = re.search(r'```json\s*(.*?)\s*```', raw, re.DOTALL)
    if json_match:
        raw = json_match.group(1)
    # Also strip any leading/trailing non-JSON
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r'^```\w*\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse topic research JSON: {e}\nRaw: {raw[:500]}")

    print(f"[topic_research] Research notes: {data.get('research_notes', '')}")

    candidates = data.get("candidates", [])
    recommended = data.get("recommended", {})
    already_used = set()
    types_needed = ["A", "B", "C"][:slots_from_research]

    # Select recommended candidates by type
    for t in types_needed:
        key = f"type_{t.lower()}"
        idx = recommended.get(key)
        if idx is not None:
            try:
                idx = int(str(idx))
                if 0 <= idx < len(candidates) and idx not in already_used:
                    selected.append(candidates[idx])
                    already_used.add(idx)
                    continue
            except (ValueError, TypeError):
                pass
        # Fallback: pick the highest-scoring unused candidate of this type
        best = None
        best_score = -1
        for i, c in enumerate(candidates):
            if i in already_used:
                continue
            if c.get("article_type") != t:
                continue
            s = sum(c.get("scores", {}).values())
            if s > best_score:
                best_score = s
                best = (i, c)
        if best:
            selected.append(best[1])
            already_used.add(best[0])

    # If still short, fill from any remaining high-scoring candidates
    if len(selected) < slots_needed:
        remaining = sorted(
            [(i, c) for i, c in enumerate(candidates) if i not in already_used],
            key=lambda x: sum(x[1].get("scores", {}).values()),
            reverse=True,
        )
        for i, c in remaining:
            if len(selected) >= slots_needed:
                break
            selected.append(c)

    return selected[:slots_needed]
