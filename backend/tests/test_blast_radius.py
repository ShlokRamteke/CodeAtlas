from __future__ import annotations

from app.investigation.blast_radius import BlastRadiusAnalyzer, BlastRadiusResult


def test_blast_radius_direct_reachability():
    # Direct graph:
    # A imports B (A depends on B)
    # B imports C (B depends on C)
    # D imports A (D depends on A)
    edges = [
        ("src/services/order.ts", "src/services/payment.ts"),
        ("src/services/payment.ts", "src/lib/stripe.ts"),
        ("src/controllers/orderController.ts", "src/services/order.ts"),
    ]

    target = ["src/services/payment.ts"]

    res = BlastRadiusAnalyzer.compute_blast_radius(target, edges, max_depth=3)

    assert isinstance(res, BlastRadiusResult)
    assert res.target_files == ["src/services/payment.ts"]

    # Downstream of payment.ts: stripe.ts (depth 1)
    downstream_paths = [n.path for n in res.downstream_dependencies]
    assert "src/lib/stripe.ts" in downstream_paths

    # Upstream of payment.ts: order.ts (depth 1), orderController.ts (depth 2)
    upstream_paths = [n.path for n in res.upstream_callers]
    assert "src/services/order.ts" in upstream_paths
    assert "src/controllers/orderController.ts" in upstream_paths

    # Depth verification
    order_node = next(n for n in res.upstream_callers if n.path == "src/services/order.ts")
    assert order_node.depth == 1
    assert order_node.direction == "upstream"

    ctrl_node = next(
        n for n in res.upstream_callers if n.path == "src/controllers/orderController.ts"
    )
    assert ctrl_node.depth == 2
    assert ctrl_node.via == "src/services/order.ts"

    # Transitive files and components
    assert "src/lib/stripe.ts" in res.transitive_files
    assert "src/services/order.ts" in res.transitive_files
    assert "src/controllers" in res.affected_components
    assert "src/services" in res.affected_components
    assert "src/lib" in res.affected_components
    assert res.total_affected_count == 4  # target + 3 reached


def test_blast_radius_cycle_protection():
    # Graph with cycles: A -> B -> C -> A
    edges = [
        ("app/a.py", "app/b.py"),
        ("app/b.py", "app/c.py"),
        ("app/c.py", "app/a.py"),
    ]

    res = BlastRadiusAnalyzer.compute_blast_radius(["app/a.py"], edges, max_depth=5)
    assert res.total_affected_count == 3
    assert set(res.transitive_files) == {"app/b.py", "app/c.py"}


def test_blast_radius_max_depth_cutoff():
    # Linear chain: A -> B -> C -> D -> E
    edges = [
        ("app/a.py", "app/b.py"),
        ("app/b.py", "app/c.py"),
        ("app/c.py", "app/d.py"),
        ("app/d.py", "app/e.py"),
    ]

    # With max_depth=2, from A we only reach B and C
    res = BlastRadiusAnalyzer.compute_blast_radius(["app/a.py"], edges, max_depth=2)
    downstream = [n.path for n in res.downstream_dependencies]
    assert "app/b.py" in downstream
    assert "app/c.py" in downstream
    assert "app/d.py" not in downstream
    assert "app/e.py" not in downstream
