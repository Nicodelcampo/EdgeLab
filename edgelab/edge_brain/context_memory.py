from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


class ContextMemoryError(ValueError):
    """Raised on context pack constraint violation."""


@dataclass(frozen=True)
class ContextItem:
    record_id: str
    item_type: str
    reason_for_inclusion: str
    estimated_tokens: int = 50

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "item_type": self.item_type,
            "reason_for_inclusion": self.reason_for_inclusion,
        }


@dataclass
class ContextPack:
    context_pack_id: str
    episode_id: str
    token_budget: int
    provenance: str
    items: list[ContextItem] = field(default_factory=list)
    created_at_utc: str = ""

    def add_item(self, item: ContextItem) -> None:
        if any(existing.record_id == item.record_id for existing in self.items):
            return
        total_tokens = sum(i.estimated_tokens for i in self.items) + item.estimated_tokens
        if total_tokens > self.token_budget:
            raise ContextMemoryError(
                f"Item {item.record_id} exceeds token budget ({total_tokens} > {self.token_budget})"
            )
        self.items.append(item)

    def deterministic_hash(self) -> str:
        # Sort items deterministically by record_id
        sorted_items = sorted(self.items, key=lambda x: x.record_id)
        canonical_repr = json.dumps(
            {
                "context_pack_id": self.context_pack_id,
                "episode_id": self.episode_id,
                "token_budget": self.token_budget,
                "provenance": self.provenance,
                "items": [it.to_dict() for it in sorted_items],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        sorted_items = sorted(self.items, key=lambda x: x.record_id)
        return {
            "context_pack_id": self.context_pack_id,
            "episode_id": self.episode_id,
            "token_budget": self.token_budget,
            "provenance": self.provenance,
            "items": [it.to_dict() for it in sorted_items],
            "deterministic_hash": self.deterministic_hash(),
            "created_at_utc": self.created_at_utc,
        }


def build_deterministic_context_pack(
    context_pack_id: str,
    episode_id: str,
    token_budget: int,
    provenance: str,
    candidates: list[ContextItem],
    created_at_utc: str,
) -> ContextPack:
    """Construct a bounded, deterministic context pack strictly ordered by priority and ID."""
    pack = ContextPack(
        context_pack_id=context_pack_id,
        episode_id=episode_id,
        token_budget=token_budget,
        provenance=provenance,
        created_at_utc=created_at_utc,
    )
    # Sort candidates deterministically by record_id
    sorted_candidates = sorted(candidates, key=lambda c: c.record_id)
    current_tokens = 0
    for cand in sorted_candidates:
        if current_tokens + cand.estimated_tokens <= token_budget:
            pack.items.append(cand)
            current_tokens += cand.estimated_tokens
    return pack
