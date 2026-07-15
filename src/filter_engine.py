"""Filter Engine (Module 4 / 7.0): post-ranking hard constraints via metadata.

Architecture alignment
----------------------
Search & Hybrid Ranking produces ranked candidates first. The Filter Engine then
applies Category, Price Range, and Rating filters by looking up product attributes
in the Metadata Store (D5: ID, Category, Price, Rating). Output is ranked &
filtered results for Result Presentation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, Sequence, TypeVar

import pandas as pd

from src.config import CLEAN_CATALOG_PATH

logger = logging.getLogger(__name__)


class RankedProduct(Protocol):
    """Minimal fields required from a ranked search result."""

    product_id: int
    category: str
    price: float
    rating: float


T = TypeVar("T", bound=RankedProduct)


@dataclass(frozen=True)
class FilterCriteria:
    """User-selected hard constraints from the search UI."""

    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None

    def is_active(self) -> bool:
        return any(
            v is not None
            for v in (self.category, self.min_price, self.max_price, self.min_rating)
        )

    @classmethod
    def from_kwargs(
        cls,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
    ) -> FilterCriteria:
        return cls(
            category=category,
            min_price=min_price,
            max_price=max_price,
            min_rating=min_rating,
        )


@dataclass(frozen=True)
class ProductMetadata:
    """Single product record in the Metadata Store (D5)."""

    product_id: int
    category: str
    price: float
    rating: float


class MetadataStore:
    """
    D5: Metadata Store — product attributes used for filtering.

    Holds ID, Category, Price, and Rating keyed by product ID.
    """

    def __init__(self, catalog_path: Path = CLEAN_CATALOG_PATH):
        self.catalog_path = catalog_path
        self._by_id: dict[int, ProductMetadata] = {}
        self._loaded = False

    def load(self, force: bool = False) -> None:
        if self._loaded and not force:
            return
        if not self.catalog_path.exists():
            raise FileNotFoundError(f"Catalog not found: {self.catalog_path}")

        df = pd.read_csv(self.catalog_path)
        required = {"id", "category", "price", "rating"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Catalog missing metadata columns: {sorted(missing)}")

        self._by_id = {
            int(row["id"]): ProductMetadata(
                product_id=int(row["id"]),
                category=str(row["category"]),
                price=float(row["price"]),
                rating=float(row["rating"]),
            )
            for _, row in df.iterrows()
        }
        self._loaded = True
        logger.info("Metadata store loaded with %d products", len(self._by_id))

    def get(self, product_id: int) -> Optional[ProductMetadata]:
        self.load()
        return self._by_id.get(product_id)

    def __len__(self) -> int:
        self.load()
        return len(self._by_id)


class FilterEngine:
    """
    Apply category, price-range, and rating filters to ranked search results.

    Input:  ranked results from Semantic / BM25 / Hybrid ranking
    Output: ranked & filtered results (order preserved)
    """

    def __init__(self, metadata_store: Optional[MetadataStore] = None):
        self.metadata = metadata_store or MetadataStore()

    def _matches(self, meta: ProductMetadata, criteria: FilterCriteria) -> bool:
        if criteria.category and meta.category != criteria.category:
            return False
        if criteria.min_price is not None and meta.price < criteria.min_price:
            return False
        if criteria.max_price is not None and meta.price > criteria.max_price:
            return False
        if criteria.min_rating is not None and meta.rating < criteria.min_rating:
            return False
        return True

    def apply(
        self,
        ranked_results: Sequence[T],
        criteria: FilterCriteria,
        top_k: Optional[int] = None,
    ) -> list[T]:
        """
        Filter ranked results using Metadata Store lookups.

        When no criteria are active, returns the ranked list unchanged
        (optionally truncated to top_k).
        """
        if not criteria.is_active():
            results = list(ranked_results)
            return results[:top_k] if top_k is not None else results

        self.metadata.load()
        filtered: list[T] = []
        for result in ranked_results:
            meta = self.metadata.get(result.product_id)
            if meta is None:
                # Fallback to attributes carried on the result itself
                meta = ProductMetadata(
                    product_id=result.product_id,
                    category=result.category,
                    price=result.price,
                    rating=result.rating,
                )
            if self._matches(meta, criteria):
                filtered.append(result)
                if top_k is not None and len(filtered) >= top_k:
                    break
        return filtered
