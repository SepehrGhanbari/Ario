"""Loss-aware PROV-Python adapter for the synthetic lineage fixtures.

Uses PROV as a provenance representation/interchange implementation only.
It does not evaluate truth, source authenticity, or independent-root semantics.
"""
from __future__ import annotations

from typing import Any


def build_prov_document(fixture: Any) -> Any:
    """Map a lineage fixture into a PROV-DM document.

    The caller must install the pinned optional adapter requirements.
    """
    if fixture.family != "lineage_dependence":
        raise ValueError("PROV adapter currently supports lineage_dependence only")

    try:
        from prov.model import ProvDocument
    except ImportError as exc:  # pragma: no cover - exercised in adapter env
        raise RuntimeError(
            "PROV adapter dependency missing; install requirements-adapters.txt"
        ) from exc

    doc = ProvDocument()
    doc.set_default_namespace("https://ario.example/aec/")
    root_entities: dict[str, Any] = {}

    # Deterministic ordering makes serialized fixtures stable.
    for source in sorted(fixture.input["sources"]):
        agent = doc.agent(f"agent_{source}")
        record = doc.entity(f"record_{source}")
        record.wasAttributedTo(agent)

        for root_id in sorted(fixture.input["roots"].get(source, [])):
            if root_id not in root_entities:
                root_entities[root_id] = doc.entity(f"root_{root_id}")
            # PROV derivation records a declared lineage edge only. The root
            # label remains a fixture premise, not authenticated provenance.
            record.wasDerivedFrom(root_entities[root_id])

    return doc


def serialize_prov_n(fixture: Any) -> str:
    """Return deterministic PROV-N for a lineage fixture."""
    return build_prov_document(fixture).get_provn(width=None)


def round_trip_prov_n(fixture: Any) -> bool:
    """Check that the pinned library can parse its own PROV-N output."""
    from prov.model import ProvDocument

    source = build_prov_document(fixture)
    serialized = source.get_provn(width=None)
    restored = ProvDocument.deserialize(content=serialized, format="provn")
    return restored == source
