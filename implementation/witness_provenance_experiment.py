"""ARIO-TB-003: synthetic provenance/control-graph experiment only.

All 'frozen' facts and completeness attestations are laboratory assumptions.
This module authenticates no custodian, principal, clock, graph, or historical event.
No filesystem, network, signer, M0 bridge, or authority activation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PROFILE = "ARIO-WITNESS-PROVENANCE-EXPERIMENT-0.1"
LAB = "FROZEN_TEST_CONTROLLER_REFERENCE"
CANDIDATE = "CANDIDATE_SUPPLIED"
SELF = "WITNESS_SELF_DECLARATION"
DERIVED = "DERIVED_COMPARISON_RESULT"
UNRESOLVED = "UNRESOLVED_ORIGIN"
ORIGINS = frozenset((LAB, CANDIDATE, SELF, DERIVED, UNRESOLVED))
KINDS = frozenset(("SOURCE", "CAPTURE", "ARTIFACT", "CUSTODIAN", "STORAGE_DOMAIN", "CONTROL_PRINCIPAL", "CONTROL_ROOT", "EXPERIMENT_CONTROLLER"))
EDGES = frozenset(("DERIVED_FROM", "CAPTURED_FROM", "TRANSFERRED_TO", "STORED_AT", "HELD_BY", "CAN_WRITE", "CAN_DELETE", "ADMINISTERS", "SHARES_CONTROL_ROOT", "RESTORES_FROM"))
MAX_NODES, MAX_EDGES, MAX_ARTIFACTS, MAX_DEPTH = 64, 128, 32, 16
MAX_INPUT_BYTES = 131072


@dataclass(frozen=True)
class Node:
    node_id: str
    kind: str
    scope: str
    origin: str
    support_ref: str
    object_identity: str | None = None  # SOURCE/STORAGE_DOMAIN canonical object identity, lab-declared
    capture_sequence: int | None = None  # CAPTURE test sequence, not timestamp
    capture_custodian: str | None = None  # CAPTURE's initial CUSTODIAN node_id


@dataclass(frozen=True)
class Edge:
    edge_id: str
    source: str
    target: str
    kind: str
    origin: str
    support_ref: str
    subject_artifact_ref: str | None = None  # only TRANSFERRED_TO
    sequence: int | None = None  # only TRANSFERRED_TO


@dataclass(frozen=True)
class ControlGraph:
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    origin: str = LAB


@dataclass(frozen=True)
class CompromiseInterval:
    node_id: str
    start_sequence: int
    end_sequence: int | None = None


@dataclass(frozen=True)
class ProvenanceCase:
    graph: ControlGraph
    scope: str
    witness_artifact_refs: tuple[str, str]
    complete_control_surface: bool = False
    complete_source_surface: bool = False
    completeness_origin: str = UNRESOLVED
    mutation_sequence: int | None = None
    compromised_node_ids: tuple[str, ...] = ()
    compromise_intervals: tuple[CompromiseInterval, ...] = ()
    controller_compromised: bool = False
    presented_claims: tuple[Edge, ...] = ()
    profile: str = PROFILE


@dataclass(frozen=True)
class Finding:
    status: str
    reason: str
    support: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProvenanceReport:
    per_witness_custody: tuple[Finding, ...]
    storage_separation: Finding
    administrative_separation: Finding
    source_independence: Finding
    capture_order: Finding
    common_control_paths: tuple[tuple[str, ...], ...]
    unsupported_claims: tuple[str, ...]
    conflicting_provenance: tuple[str, ...]
    model_assumptions: tuple[str, ...]
    reason_codes: tuple[str, ...]
    kind: str = field(default="EXPERIMENTAL_PROVENANCE_REPORT", init=False)
    production_custody_authenticity: str = field(default="NOT_ESTABLISHED", init=False)
    cryptographic_authentication: str = field(default="NOT_CHECKED", init=False)
    historical_event_truth: str = field(default="UNKNOWN", init=False)
    entity_continuity: str = field(default="UNKNOWN", init=False)
    ontological_continuity: str = field(default="UNKNOWN", init=False)
    human_authorization: str = field(default="NOT_EVALUATED", init=False)
    evidence_admission: str = field(default="NOT_EVALUATED", init=False)
    production_historical_continuity: str = field(default="INCONCLUSIVE", init=False)


def _f(status: str, reason: str, *support: str) -> Finding:
    return Finding(status, reason, tuple(sorted(set(support))))


def _ascii(value: Any, limit: int = 128) -> bool:
    return type(value) is str and 0 < len(value) <= limit and all(32 <= ord(c) <= 126 for c in value)


def _int(value: Any) -> bool:
    return type(value) is int and 0 <= value <= 1000000


def _unknown(reason: str) -> Finding:
    return _f("UNKNOWN", reason)


def _invalid(reason: str) -> ProvenanceReport:
    u = _unknown(reason)
    return ProvenanceReport((u, u), u, u, u, u, (), (), (), (), (reason,))


def _edge_types_compatible(e: Edge, nodes: dict[str, Node]) -> bool:
    src, dst = nodes[e.source].kind, nodes[e.target].kind
    return {
        "DERIVED_FROM": src in ("SOURCE", "CAPTURE") and dst == "SOURCE",
        "CAPTURED_FROM": src == "ARTIFACT" and dst == "CAPTURE",
        "TRANSFERRED_TO": src == dst == "CUSTODIAN",
        "STORED_AT": src == "ARTIFACT" and dst == "STORAGE_DOMAIN",
        "HELD_BY": src == "ARTIFACT" and dst == "CUSTODIAN",
        "CAN_WRITE": src == "CONTROL_PRINCIPAL" and dst == "STORAGE_DOMAIN",
        "CAN_DELETE": src == "CONTROL_PRINCIPAL" and dst == "STORAGE_DOMAIN",
        "ADMINISTERS": src == "CONTROL_ROOT" and dst in ("CONTROL_ROOT", "CONTROL_PRINCIPAL"),
        "SHARES_CONTROL_ROOT": src == dst == "CONTROL_ROOT",
        "RESTORES_FROM": src == dst == "STORAGE_DOMAIN",
    }[e.kind]


def _validate(case: Any) -> str | None:
    if type(case) is not ProvenanceCase or type(case.graph) is not ControlGraph:
        return "INVALID_CASE_OR_GRAPH"
    g = case.graph
    if case.profile != PROFILE:
        return "UNSUPPORTED_PROFILE"
    if not _ascii(case.scope) or type(g.nodes) is not tuple or type(g.edges) is not tuple:
        return "INVALID_GRAPH_SHAPE"
    if (len(g.nodes) > MAX_NODES or len(g.edges) > MAX_EDGES or
        type(case.witness_artifact_refs) is not tuple or len(case.witness_artifact_refs) != 2 or
        type(case.compromised_node_ids) is not tuple or len(case.compromised_node_ids) > MAX_NODES or
        type(case.compromise_intervals) is not tuple or len(case.compromise_intervals) > MAX_NODES or
        type(case.presented_claims) is not tuple or len(case.presented_claims) > MAX_EDGES or
        type(case.complete_control_surface) is not bool or
        type(case.complete_source_surface) is not bool or type(case.controller_compromised) is not bool or
        (case.mutation_sequence is not None and not _int(case.mutation_sequence))):
        return "INVALID_BOUNDS_OR_TYPES"
    if (type(g.origin) is not str or g.origin not in ORIGINS or
        type(case.completeness_origin) is not str or case.completeness_origin not in ORIGINS or
        any(type(x) is not str for x in case.witness_artifact_refs + case.compromised_node_ids)):
        return "INVALID_ORIGIN_OR_REFERENCES"
    ns: dict[str, Node] = {}
    for n in g.nodes:
        if (type(n) is not Node or not _ascii(n.node_id) or n.node_id in ns or
            type(n.kind) is not str or n.kind not in KINDS or not _ascii(n.scope) or
            type(n.origin) is not str or n.origin not in ORIGINS or
            not _ascii(n.support_ref) or
            (n.object_identity is not None and not _ascii(n.object_identity)) or
            (n.capture_sequence is not None and not _int(n.capture_sequence)) or
            (n.capture_custodian is not None and not _ascii(n.capture_custodian))):
            return "INVALID_OR_DUPLICATE_NODE"
        if n.kind in ("STORAGE_DOMAIN", "SOURCE"):
            if n.object_identity is None or n.capture_sequence is not None or n.capture_custodian is not None:
                return "INVALID_SOURCE_OR_STORAGE_NODE"
        elif n.kind == "CAPTURE":
            if n.capture_sequence is None or n.capture_custodian is None or n.object_identity is not None:
                return "INVALID_CAPTURE_NODE"
        elif n.object_identity is not None or n.capture_sequence is not None or n.capture_custodian is not None:
            return "INVALID_NODE_TYPE_FIELDS"
        ns[n.node_id] = n
    if (len(set(case.witness_artifact_refs)) != 2 or
        any(x not in ns or ns[x].kind != "ARTIFACT" for x in case.witness_artifact_refs) or
        any(x not in ns for x in case.compromised_node_ids) or
        len(set(case.compromised_node_ids)) != len(case.compromised_node_ids) or
        sum(n.kind == "ARTIFACT" for n in g.nodes) > MAX_ARTIFACTS):
        return "INVALID_ARTIFACT_OR_COMPROMISE_REFERENCE"
    if any(n.kind == "CAPTURE" and (n.capture_custodian not in ns or ns[n.capture_custodian].kind != "CUSTODIAN") for n in g.nodes):
        return "INVALID_CAPTURE_CUSTODIAN"
    if any(type(i) is not CompromiseInterval or i.node_id not in ns or
           not _int(i.start_sequence) or
           (i.end_sequence is not None and (not _int(i.end_sequence) or i.end_sequence < i.start_sequence))
           for i in case.compromise_intervals):
        return "INVALID_COMPROMISE_INTERVAL"
    if len(set(i.node_id for i in case.compromise_intervals)) != len(case.compromise_intervals):
        return "DUPLICATE_COMPROMISE_INTERVAL"
    es: set[str] = set()
    for e in g.edges + case.presented_claims:
        if (type(e) is not Edge or not _ascii(e.edge_id) or e.edge_id in es or
            not _ascii(e.source) or not _ascii(e.target) or
            e.source not in ns or e.target not in ns or
            type(e.kind) is not str or e.kind not in EDGES or
            type(e.origin) is not str or e.origin not in ORIGINS or not _ascii(e.support_ref)):
            return "INVALID_OR_DUPLICATE_EDGE"
        es.add(e.edge_id)
        if not _edge_types_compatible(e, ns):
            return "INVALID_EDGE_ENDPOINT_TYPES"
        if e.kind == "TRANSFERRED_TO":
            if (not _ascii(e.subject_artifact_ref) or
                e.subject_artifact_ref not in ns or ns[e.subject_artifact_ref].kind != "ARTIFACT" or
                not _int(e.sequence)):
                return "INVALID_TRANSFER_FIELDS"
        elif e.subject_artifact_ref is not None or e.sequence is not None:
            return "INVALID_EDGE_TYPE_FIELDS"
    # Bounded approximate serialized input size; all strings are bounded and counted.
    size = sum(len(str(v)) for n in g.nodes for v in vars(n).values())
    size += sum(len(str(v)) for e in g.edges + case.presented_claims for v in vars(e).values())
    size += sum(len(str(v)) for i in case.compromise_intervals for v in vars(i).values())
    if size > MAX_INPUT_BYTES:
        return "OVERSIZED_INPUT"
    return None


def _paths(edges: tuple[Edge, ...], starts: tuple[str, ...], kinds: set[str], *,
           direction: str = "forward", limit: int = MAX_DEPTH) -> tuple[dict[str, tuple[str, ...]], bool]:
    """Shortest deterministic edge paths, plus overflow flag (no truncation-as-proof)."""
    routes = {s: () for s in starts}
    overflow = False
    adj: dict[str, list[tuple[str, str]]] = {}
    for e in edges:
        if e.kind not in kinds:
            continue
        src, dst = (e.source, e.target) if direction == "forward" else (e.target, e.source)
        adj.setdefault(src, []).append((dst, e.edge_id))
        if e.kind == "SHARES_CONTROL_ROOT":
            adj.setdefault(dst, []).append((src, e.edge_id))
    queue = list(sorted(starts))
    idx = 0
    while idx < len(queue):
        at = queue[idx]; idx += 1
        for next_id, eid in sorted(adj.get(at, [])):
            path = routes[at] + (eid,)
            if len(path) > limit:
                overflow = True
                continue
            if next_id not in routes:
                routes[next_id] = path
                queue.append(next_id)
    return routes, overflow


def _reachable_cycle(edges: tuple[Edge, ...], starts: tuple[str, ...], kind: str) -> bool:
    adjacency: dict[str, list[str]] = {}
    for e in edges:
        if e.kind == kind:
            adjacency.setdefault(e.source, []).append(e.target)
    active: set[str] = set()
    finished: set[str] = set()

    def visit(node: str) -> bool:
        if node in active:
            return True
        if node in finished:
            return False
        active.add(node)
        for child in adjacency.get(node, ()):
            if visit(child):
                return True
        active.remove(node)
        finished.add(node)
        return False

    return any(visit(n) for n in starts)


def _custody_for(artifact: str, ns: dict[str, Node], es: tuple[Edge, ...]) -> Finding:
    captures = [e for e in es if e.kind == "CAPTURED_FROM" and e.source == artifact]
    holders = [e for e in es if e.kind == "HELD_BY" and e.source == artifact]
    if len(captures) != 1 or len(holders) != 1:
        return _unknown("MISSING_OR_AMBIGUOUS_CAPTURE_HOLDER")
    cap, held = captures[0], holders[0]
    if cap.origin != LAB or held.origin != LAB or ns[cap.target].origin != LAB:
        return _unknown("UNSUPPORTED_CUSTODY_ORIGIN")
    first = ns[cap.target].capture_custodian
    dest = held.target
    if first == dest:
        return _f("LAB_CHAIN_PRESENT", "DIRECT_LAB_CUSTODY", cap.edge_id, held.edge_id)
    # Transfer sequence must be strictly ordered after capture.
    eligible = [e for e in es if e.kind == "TRANSFERRED_TO" and e.subject_artifact_ref == artifact and
                e.origin == LAB and e.sequence is not None and e.sequence > ns[cap.target].capture_sequence]
    graph = {}
    for e in eligible:
        graph.setdefault(e.source, []).append(e)
    options: list[tuple[str, ...]] = []
    cyclic = False

    def walk(at: str, prev: int, seen: frozenset[str], path: tuple[str, ...]) -> None:
        nonlocal cyclic
        if len(path) > MAX_DEPTH:
            cyclic = True
            return
        if at == dest:
            options.append(path)
            return
        for edge in sorted(graph.get(at, []), key=lambda x: x.edge_id):
            if edge.target in seen:
                cyclic = True
            elif edge.sequence > prev:
                walk(edge.target, edge.sequence, seen | {edge.target}, path + (edge.edge_id,))

    walk(first, ns[cap.target].capture_sequence, frozenset((first,)), ())
    if cyclic:
        return _unknown("CYCLIC_OR_OVERSIZED_CUSTODY_CHAIN")
    if len(options) != 1:
        return _unknown("MISSING_OR_AMBIGUOUS_CUSTODY_TRANSFER")
    return _f("LAB_CHAIN_PRESENT", "LAB_TRANSFER_CHAIN_PRESENT", cap.edge_id, held.edge_id, *options[0])


def _source_set(artifact: str, ns: dict[str, Node], es: tuple[Edge, ...]) -> tuple[set[str], tuple[str, ...], bool]:
    captures = [e for e in es if e.kind == "CAPTURED_FROM" and e.source == artifact and e.origin == LAB]
    if len(captures) != 1:
        return set(), (), True
    cap = captures[0].target
    if _reachable_cycle(es, (cap,), "DERIVED_FROM"):
        return set(), (), True
    reached, overflow = _paths(es, (cap,), {"DERIVED_FROM"})
    source_nodes = {k for k in reached if ns[k].kind == "SOURCE" and ns[k].origin == LAB}
    sources = {ns[k].object_identity for k in source_nodes}
    used = {captures[0].edge_id}
    for k in source_nodes:
        used.update(reached[k])
    return sources, tuple(sorted(used)), overflow


def evaluate_provenance(case: ProvenanceCase) -> ProvenanceReport:
    """Bounded structural diagnostics; no real-world trust or provenance verification."""
    bad = _validate(case)
    if bad:
        return _invalid(bad)
    ns = {n.node_id: n for n in case.graph.nodes}
    g = case.graph
    witnesses = case.witness_artifact_refs
    cross_scope_nodes = tuple(sorted(n.node_id for n in g.nodes if n.scope != case.scope))
    trusted_graph = g.origin == LAB and not case.controller_compromised and not cross_scope_nodes
    clean_lab_graph = all(n.origin == LAB for n in g.nodes) and all(e.origin == LAB for e in g.edges)
    lab_edges = tuple(sorted((e for e in g.edges if e.origin == LAB and
                              ns[e.source].origin == LAB and ns[e.target].origin == LAB),
                             key=lambda x: x.edge_id)) if trusted_graph else ()
    unsupported = tuple(sorted(
        ["NODE:" + n.node_id for n in g.nodes if n.origin != LAB] +
        [e.edge_id for e in g.edges if e.origin != LAB or
         ns[e.source].origin != LAB or ns[e.target].origin != LAB] +
        [e.edge_id for e in case.presented_claims]
    ))
    assumptions = ["NO_PRODUCTION_AUTHENTICATION", "GRAPH_CONTROL_FACTS_LAB_DECLARED_ONLY"]
    if case.complete_control_surface and case.completeness_origin == LAB:
        assumptions.append("LAB_CONTROL_SURFACE_DECLARED_COMPLETE")
    if case.complete_source_surface and case.completeness_origin == LAB:
        assumptions.append("LAB_SOURCE_SURFACE_DECLARED_COMPLETE")
    conflicts = []
    # A declared-but-unsupported claim about any control relationship is never accepted.
    if g.origin != LAB:
        assumptions.append("GRAPH_NOT_FROZEN_BY_LAB")
    if case.controller_compromised:
        assumptions.append("LAB_CONTROLLER_COMPROMISED_BY_SCENARIO")
    for a in cross_scope_nodes:
        conflicts.append("SCOPE_REPLAY:" + a)
    custody = tuple(_custody_for(a, ns, lab_edges) if trusted_graph and ns[a].scope == case.scope
                    else _unknown("UNTRUSTED_GRAPH_OR_SCOPE") for a in witnesses)

    storage_nodes = []
    storage_eids = []
    for a in witnesses:
        edges = [e for e in lab_edges if e.kind == "STORED_AT" and e.source == a]
        if len(edges) == 1 and ns[a].scope == case.scope:
            storage_nodes.append(edges[0].target)
            storage_eids.append(edges[0].edge_id)
        else:
            storage_nodes.append(None)
            storage_eids.append(None)
    if any(x is None for x in storage_nodes):
        storage = _unknown("MISSING_OR_UNTRUSTED_STORAGE_BINDING")
    elif ns[storage_nodes[0]].object_identity == ns[storage_nodes[1]].object_identity:
        storage = _f("SAME_STORAGE_OBJECT", "ALIASED_STORAGE_OBJECT", *storage_eids)
    else:
        storage = _f("LAB_DISTINCT_OBJECTS", "LAB_STORAGE_REFERENCES_DISTINCT", *storage_eids)

    compromised = set(case.compromised_node_ids) | {i.node_id for i in case.compromise_intervals}
    # Candidate-visible compromised storage, root, or principal is not assumed secure.
    if case.controller_compromised:
        admin = _unknown("CONTROLLER_COMPROMISED")
        control_paths: tuple[tuple[str, ...], ...] = ()
    elif any(x is None for x in storage_nodes):
        admin = _unknown("MISSING_STORAGE_FOR_CONTROL_AUDIT")
        control_paths = ()
    else:
        # Include ONLY declared restore inputs. A shared backup without an enabled restore
        # path is not automatically a mutation path.
        exposures = []
        exceeds = False
        for st in storage_nodes:
            r, too_deep = _paths(lab_edges, (st,), {"RESTORES_FROM"})
            exposures.append(r)
            exceeds |= too_deep
        controllers = []
        controller_traces = []
        for exp in exposures:
            by_actor: dict[str, tuple[str, ...]] = {}
            for e in lab_edges:
                if e.kind in ("CAN_WRITE", "CAN_DELETE") and e.target in exp:
                    trail = (e.edge_id,) + exp[e.target]
                    actor_routes, deep = _paths(lab_edges, (e.source,), {"ADMINISTERS", "SHARES_CONTROL_ROOT"}, direction="reverse")
                    exceeds |= deep
                    for a, p in actor_routes.items():
                        if a not in by_actor or (len(trail) + len(p), p + trail) < (len(by_actor[a]), by_actor[a]):
                            by_actor[a] = p + trail
            controllers.append(set(by_actor))
            controller_traces.append(by_actor)
        common = sorted(controllers[0] & controllers[1])
        paths = set()
        for actor in common:
            paths.add(("CONTROL:" + actor,) + controller_traces[0][actor] + ("WITNESS_B",) + controller_traces[1][actor])
        control_paths = tuple(sorted(paths))
        impacted = bool(compromised & (controllers[0] | controllers[1] | set(storage_nodes) | set(witnesses)))
        if common:
            admin = _f("COMMON_CONTROL_DETECTED", "SHARED_MUTATION_CONTROLLER", *sorted(set(e for p in control_paths for e in p)))
        elif impacted:
            admin = _f("COMPROMISED_BY_SCENARIO", "EXPLICIT_CONTROL_OR_STORAGE_COMPROMISE", *sorted(compromised))
        elif exceeds or _reachable_cycle(lab_edges, tuple(ns), "ADMINISTERS") or _reachable_cycle(lab_edges, tuple(storage_nodes), "RESTORES_FROM"):
            admin = _unknown("CONTROL_GRAPH_CYCLE_OR_DEPTH_LIMIT")
        elif not clean_lab_graph or not case.complete_control_surface or case.completeness_origin != LAB:
            admin = _unknown("CONTROL_SURFACE_INCOMPLETE_OR_SELF_DECLARED")
        elif storage.status == "SAME_STORAGE_OBJECT":
            admin = _f("COMMON_CONTROL_DETECTED", "SHARED_STORAGE_OBJECT", *storage.support)
        elif any(c.status != "LAB_CHAIN_PRESENT" for c in custody):
            admin = _unknown("CUSTODY_CHAIN_NOT_ESTABLISHED")
        else:
            admin = _f("LAB_CONDITIONALLY_SEPARATE", "DISJOINT_LAB_CONTROL_PATHS", *storage.support)

    sources = []
    origin_support = []
    failed_source_walk = False
    for a in witnesses:
        s, refs, failure = _source_set(a, ns, lab_edges)
        sources.append(s)
        origin_support.extend(refs)
        failed_source_walk |= failure
    shared = sources[0] & sources[1]
    if not trusted_graph or any(ns[a].scope != case.scope for a in witnesses):
        source = _unknown("UNTRUSTED_SOURCE_GRAPH_OR_SCOPE")
    elif shared:
        source = _f("COMMON_SOURCE_DETECTED", "SHARED_DECLARED_ORIGIN", *sorted(shared), *origin_support)
    elif failed_source_walk:
        source = _unknown("SOURCE_PATH_LIMIT_OR_MISSING_CAPTURE")
    elif (not clean_lab_graph or not case.complete_source_surface or case.completeness_origin != LAB or
          not all(sources) or any(c.status != "LAB_CHAIN_PRESENT" for c in custody)):
        source = _unknown("SOURCE_SURFACE_INCOMPLETE_OR_UNSUPPORTED")
    else:
        source = _f("LAB_CONDITIONALLY_DISTINCT", "DISJOINT_LAB_SOURCE_SETS", *origin_support)

    captures = []
    capture_support = []
    for a in witnesses:
        matches = [e for e in lab_edges if e.kind == "CAPTURED_FROM" and e.source == a]
        if len(matches) == 1:
            captures.append(ns[matches[0].target].capture_sequence)
            capture_support.append(matches[0].edge_id)
        else:
            captures.append(None)
    compromised_at_capture = any(
        witness in case.compromised_node_ids or
        any(i.node_id == witness and i.start_sequence <= moment and
            (i.end_sequence is None or moment <= i.end_sequence)
            for i in case.compromise_intervals)
        for witness, moment in zip(witnesses, captures) if moment is not None
    )
    if not trusted_graph or case.mutation_sequence is None or any(c is None for c in captures):
        order = _unknown("NO_TRUSTED_LAB_SEQUENCE_ORDER")
    elif any(c >= case.mutation_sequence for c in captures):
        order = _f("NOT_BEFORE_MUTATION", "CAPTURE_NOT_STRICTLY_PRIOR", *capture_support)
    elif compromised_at_capture:
        order = _unknown("CAPTURE_ARTIFACT_COMPROMISED_BY_SCENARIO")
    else:
        order = _f("LAB_BEFORE_MUTATION", "CAPTURE_SEQUENCE_PRECEDES_MUTATION", *capture_support)

    if case.controller_compromised:
        admin = _unknown("CONTROLLER_COMPROMISED")
        source = _unknown("CONTROLLER_COMPROMISED")
        order = _unknown("CONTROLLER_COMPROMISED")
        custody = (_unknown("CONTROLLER_COMPROMISED"),) * 2
        storage = _unknown("CONTROLLER_COMPROMISED")
    # Unsupported claims never become fixed control edges. Record exact IDs.
    reason_codes = tuple(sorted(set([x.reason for x in (*custody, storage, admin, source, order)] +
                                    ["UNSUPPORTED_CLAIM:" + u for u in unsupported] + conflicts)))
    return ProvenanceReport(custody, storage, admin, source, order, control_paths,
                            unsupported, tuple(sorted(conflicts)), tuple(sorted(set(assumptions))), reason_codes)
