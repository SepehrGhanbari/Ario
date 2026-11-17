"""Loss-aware PROV-Python adapter for the synthetic lineage fixtures.

Uses PROV as a provenance representation/interchange implementation only.
It does not evaluate truth, source authenticity, or independent-root semantics.
"""
from __future__ import annotations

from typing import Any


def _validated_lineage_inputs(fixture: Any) -> tuple[list[str], dict[str, list[str]]]:
    """Reject incomplete or malformed source-to-root maps before graph creation."""
    data = fixture.input
    if not isinstance(data, dict):
        raise ValueError("PROV adapter requires a mapping-like fixture input")

    sources = data.get("sources")
    roots = data.get("roots")
    if (
        not isinstance(sources, list)
        or not sources
        or any(not isinstance(source, str) or not source.strip() for source in sources)
        or len(set(sources)) != len(sources)
    ):
        raise ValueError("PROV adapter requires unique, non-empty string source identifiers")

    if not isinstance(roots, dict) or set(roots) != set(sources):
        raise ValueError(
            "PROV adapter requires an exact source-to-root mapping; "
            "missing or undeclared source entries are not accepted"
        )

    validated: dict[str, list[str]] = {}
    for source in sources:
        source_roots = roots[source]
        if (
            not isinstance(source_roots, (list, tuple))
            or not source_roots
            or any(not isinstance(root, str) or not root.strip() for root in source_roots)
        ):
            raise ValueError(
                f"PROV adapter requires non-empty string root identifiers for source {source!r}"
            )
        validated[source] = list(source_roots)

    return list(sources), validated


def _safe_local_id(prefix: str, original_id: str) -> str:
    """Encode UTF-8 identifiers as hex so arbitrary input cannot corrupt PROV QNames.

    Hex is reversible and uses only QName-safe ASCII characters. The original
    identifier is therefore not silently normalized or discarded.
    """
    return f"{prefix}_{original_id.encode('utf-8').hex()}"


def build_prov_document(fixture: Any) -> Any:
    """Map a complete lineage fixture into a PROV-DM document.

    The adapter rejects incomplete lineage instead of silently omitting edges.
    The caller must install the pinned optional adapter requirements.
    """
    if fixture.family != "lineage_dependence":
        raise ValueError("PROV adapter currently supports lineage_dependence only")

    sources, roots = _validated_lineage_inputs(fixture)

    try:
        from prov.model import ProvDocument
    except ImportError as exc:  # pragma: no cover - exercised in adapter env
        raise RuntimeError(
            "PROV adapter dependency missing; install requirements-adapters.txt"
        ) from exc

    doc = ProvDocument()
    doc.set_default_namespace("https://ario.example/aec/")
    root_entities: dict[str, Any] = {}

    # Deterministic ordering makes serialized fixtures stable. Local identifiers
    # are reversible UTF-8 hex encodings, not claimed source identities.
    for source in sorted(sources):
        agent = doc.agent(_safe_local_id("agent", source))
        record = doc.entity(_safe_local_id("record", source))
        record.wasAttributedTo(agent)

        for root_id in sorted(roots[source]):
            if root_id not in root_entities:
                root_local_id = _safe_local_id("root", root_id)
                root_entities[root_id] = doc.entity(root_local_id)
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
