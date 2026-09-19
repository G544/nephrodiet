import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")

# Below the lower bound, two recipes are not even considered candidates.
NAME_SIMILARITY_CANDIDATE_THRESHOLD = 0.3
# Name similarity alone is enough to call it a duplicate above this bound.
NAME_SIMILARITY_DUPLICATE_THRESHOLD = 0.6
# A weaker name match combined with overlapping ingredients is also a duplicate.
NAME_SIMILARITY_WEAK_THRESHOLD = 0.4
INGREDIENT_JACCARD_DUPLICATE_THRESHOLD = 0.5


def normalize_name(name: str) -> str:
    lowered = name.strip().lower()
    no_punct = _PUNCTUATION_RE.sub("", lowered)
    return _WHITESPACE_RE.sub(" ", no_punct).strip()


def ingredient_jaccard(names_a: list[str], names_b: list[str]) -> float:
    set_a = {normalize_name(n) for n in names_a}
    set_b = {normalize_name(n) for n in names_b}
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


@dataclass
class SimilarRecipeCandidate:
    id: int
    name: str
    ingredient_names: list[str]
    name_similarity: float


async def find_similar_recipes(
    session: AsyncSession, normalized_name: str, limit: int = 5
) -> list[SimilarRecipeCandidate]:
    """Trigram-similarity search over recipe.normalized_name using pg_trgm."""
    result = await session.execute(
        text(
            """
            SELECT id, name, ingredients, similarity(normalized_name, :name) AS sim
            FROM recipe
            WHERE normalized_name % :name
            ORDER BY sim DESC
            LIMIT :limit
            """
        ),
        {"name": normalized_name, "limit": limit},
    )
    candidates = []
    for row in result.mappings():
        ingredient_names = [ing.get("name", "") for ing in (row["ingredients"] or [])]
        candidates.append(
            SimilarRecipeCandidate(
                id=row["id"],
                name=row["name"],
                ingredient_names=ingredient_names,
                name_similarity=row["sim"],
            )
        )
    return candidates


def is_duplicate(name_similarity: float, jaccard: float) -> bool:
    if name_similarity > NAME_SIMILARITY_DUPLICATE_THRESHOLD:
        return True
    return name_similarity > NAME_SIMILARITY_WEAK_THRESHOLD and jaccard > INGREDIENT_JACCARD_DUPLICATE_THRESHOLD


async def find_duplicate(
    session: AsyncSession, name: str, ingredient_names: list[str]
) -> SimilarRecipeCandidate | None:
    """Return the best matching existing recipe if `name`/`ingredient_names` look like a duplicate."""
    normalized = normalize_name(name)
    candidates = await find_similar_recipes(session, normalized)
    best: SimilarRecipeCandidate | None = None
    best_score = -1.0
    for candidate in candidates:
        jaccard = ingredient_jaccard(ingredient_names, candidate.ingredient_names)
        if is_duplicate(candidate.name_similarity, jaccard) and candidate.name_similarity > best_score:
            best = candidate
            best_score = candidate.name_similarity
    return best
