"""Relationship detection — hybrid deterministic + evidence scoring."""

from __future__ import annotations

import uuid
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

import pandas as pd

from app.config import get_settings
from app.models.dataset import (
    Dataset,
    Relationship,
    RelationshipEvidence,
    RelationshipStatus,
    RelationshipType,
    SemanticType,
)

if TYPE_CHECKING:
    pass


def _name_similarity(a: str, b: str) -> float:
    """Normalized string similarity between column names (case-insensitive, stripped)."""
    a_clean = a.lower().replace("_", " ").replace("-", " ").strip()
    b_clean = b.lower().replace("_", " ").replace("-", " ").strip()
    if a_clean == b_clean:
        return 1.0
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def _types_compatible(left_type: str, right_type: str) -> bool:
    """Check if physical types are compatible for joining."""
    numeric = {"BIGINT", "DOUBLE", "INTEGER", "FLOAT"}
    string = {"VARCHAR", "TEXT"}
    date = {"TIMESTAMP", "DATE"}

    def group(t: str) -> str:
        if t in numeric:
            return "numeric"
        if t in string:
            return "string"
        if t in date:
            return "date"
        return t

    return group(left_type) == group(right_type)


def _semantic_compatible(left_sem: SemanticType, right_sem: SemanticType) -> bool:
    """Identifiers can join with identifiers or dimensions."""
    join_compatible = {SemanticType.IDENTIFIER, SemanticType.DIMENSION}
    return left_sem in join_compatible and right_sem in join_compatible


def _compute_value_overlap(
    left_values: pd.Series,
    right_values: pd.Series,
    max_sample: int = 5000,
) -> float:
    """Compute what fraction of left values appear in the right set."""
    if left_values.empty or right_values.empty:
        return 0.0

    left_sample = left_values.dropna().astype(str)
    right_set = set(right_values.dropna().astype(str).unique())

    if len(left_sample) > max_sample:
        left_sample = left_sample.sample(max_sample, random_state=42)

    if not right_set:
        return 0.0

    overlap_count = left_sample.isin(right_set).sum()
    return float(overlap_count) / max(len(left_sample), 1)


def _infer_relationship_type(
    left_unique_ratio: float,
    right_unique_ratio: float,
) -> RelationshipType:
    """Infer cardinality from uniqueness ratios."""
    if left_unique_ratio > 0.95 and right_unique_ratio > 0.95:
        return RelationshipType.ONE_TO_ONE
    if right_unique_ratio > 0.95:
        return RelationshipType.MANY_TO_ONE
    if left_unique_ratio > 0.95:
        return RelationshipType.ONE_TO_MANY
    return RelationshipType.MANY_TO_MANY


def detect_relationships(
    datasets: list[Dataset],
    dfs: dict[str, pd.DataFrame],  # dataset_id -> normalized DataFrame
) -> list[Relationship]:
    """
    Detect cross-dataset relationships using deterministic evidence.
    Compares all column pairs across dataset pairs.
    """
    settings = get_settings()
    relationships: list[Relationship] = []
    seen_pairs: set[tuple] = set()

    active = [d for d in datasets if d.status.value == "ready"]

    for i, left_ds in enumerate(active):
        for right_ds in active[i + 1 :]:
            left_df = dfs.get(left_ds.dataset_id)
            right_df = dfs.get(right_ds.dataset_id)

            if left_df is None or right_df is None:
                continue

            for left_col in left_ds.columns:
                for right_col in right_ds.columns:
                    pair_key = (
                        left_ds.dataset_id, left_col.name,
                        right_ds.dataset_id, right_col.name,
                    )
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    # 1. Name similarity
                    name_sim = _name_similarity(left_col.name, right_col.name)
                    name_match = name_sim >= 0.85

                    # 2. Physical type compatibility
                    type_match = _types_compatible(
                        left_col.physical_type, right_col.physical_type
                    )

                    # 3. Semantic type compatibility
                    semantic_match = _semantic_compatible(
                        left_col.semantic_type, right_col.semantic_type
                    )

                    # Early exit: must have name match AND type match
                    if not name_match or not type_match:
                        continue

                    # 4. Value overlap (expensive — only when name+type pass)
                    overlap = 0.0
                    try:
                        left_vals = left_df[left_col.name]
                        right_vals = right_df[right_col.name]
                        overlap = _compute_value_overlap(left_vals, right_vals)
                    except KeyError:
                        continue

                    if overlap < 0.1:
                        continue  # no meaningful overlap

                    # 5. Evidence score computation
                    score = (
                        name_sim * 0.30
                        + float(type_match) * 0.20
                        + float(semantic_match) * 0.15
                        + overlap * 0.35
                    )

                    if score < settings.relationship_suggest_threshold:
                        continue  # below minimum threshold

                    # Determine status
                    if score >= settings.relationship_auto_join_threshold:
                        status = RelationshipStatus.HIGH_CONFIDENCE
                    else:
                        status = RelationshipStatus.SUGGESTED

                    rel_type = _infer_relationship_type(
                        left_col.unique_ratio, right_col.unique_ratio
                    )

                    evidence = RelationshipEvidence(
                        name_similarity=round(name_sim, 3),
                        name_match=name_match,
                        type_match=type_match,
                        semantic_match=semantic_match,
                        overlap_ratio=round(overlap, 3),
                        left_uniqueness=round(left_col.unique_ratio, 3),
                        right_uniqueness=round(right_col.unique_ratio, 3),
                        evidence_score=round(score, 3),
                    )

                    relationships.append(
                        Relationship(
                            relationship_id=f"rel_{uuid.uuid4().hex[:8]}",
                            left_dataset=left_ds.dataset_id,
                            left_column=left_col.name,
                            right_dataset=right_ds.dataset_id,
                            right_column=right_col.name,
                            relationship_type=rel_type,
                            status=status,
                            evidence=evidence,
                        )
                    )

    # Deduplicate: if multiple column pairs connect the same two datasets, keep highest evidence
    relationships.sort(key=lambda r: r.evidence.evidence_score, reverse=True)
    return relationships
