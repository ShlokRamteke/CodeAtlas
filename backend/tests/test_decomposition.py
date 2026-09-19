from __future__ import annotations

from app.investigation.decomposition import ChangeDecomposer


def test_decomposition_empty_targets():
    report = ChangeDecomposer.evaluate_subgraph(
        target_files=[],
        dependency_edges=[("a.py", "b.py")],
    )
    assert report.total_files == 0
    assert report.component_count == 0
    assert report.is_decomposable is False
    assert len(report.clusters) == 0


def test_decomposition_single_file():
    report = ChangeDecomposer.evaluate_subgraph(
        target_files=["backend/app/auth/router.py"],
        dependency_edges=[
            ("backend/app/auth/router.py", "backend/app/auth/service.py"),
        ],
    )
    assert report.total_files == 1
    assert report.component_count == 1
    assert report.is_decomposable is False
    assert len(report.clusters) == 1
    assert report.clusters[0].files == ["backend/app/auth/router.py"]
    assert report.clusters[0].dominant_component == "backend/app"
    assert "router" in report.clusters[0].suggested_pr_title.lower()


def test_decomposition_tightly_coupled_single_component():
    target_files = [
        "app/auth/router.py",
        "app/auth/service.py",
        "app/auth/models.py",
    ]
    edges = [
        ("app/auth/router.py", "app/auth/service.py"),
        ("app/auth/service.py", "app/auth/models.py"),
    ]
    report = ChangeDecomposer.evaluate_subgraph(
        target_files=target_files,
        dependency_edges=edges,
    )
    assert report.total_files == 3
    assert report.component_count == 1
    assert report.is_decomposable is False
    assert report.modularity_score == 0.0
    assert len(report.clusters) == 1
    assert set(report.clusters[0].files) == set(target_files)
    assert report.clusters[0].internal_edge_count == 2


def test_decomposition_two_disjoint_clusters():
    target_files = [
        "app/auth/router.py",
        "app/auth/service.py",
        "app/billing/charge.py",
        "app/billing/stripe.py",
    ]
    edges = [
        ("app/auth/router.py", "app/auth/service.py"),
        ("app/billing/charge.py", "app/billing/stripe.py"),
        ("app/billing/stripe.py", "external/sdk.py"),  # external dep
    ]
    report = ChangeDecomposer.evaluate_subgraph(
        target_files=target_files,
        dependency_edges=edges,
    )
    assert report.total_files == 4
    assert report.component_count == 2
    assert report.is_decomposable is True
    assert report.modularity_score == 0.5
    assert len(report.clusters) == 2

    # Verify cluster separation
    cluster_files = [set(c.files) for c in report.clusters]
    auth_set = {"app/auth/router.py", "app/auth/service.py"}
    billing_set = {"app/billing/charge.py", "app/billing/stripe.py"}
    assert auth_set in cluster_files
    assert billing_set in cluster_files

    # Check external dependencies captured
    billing_cluster = next(c for c in report.clusters if "billing" in c.files[0])
    assert "external/sdk.py" in billing_cluster.external_dependencies


def test_decomposition_isolated_singletons():
    target_files = [
        "app/core/config.py",
        "app/frontend/Button.tsx",
        "docs/README.md",
    ]
    # No dependency edges between them
    report = ChangeDecomposer.evaluate_subgraph(
        target_files=target_files,
        dependency_edges=[],
    )
    assert report.total_files == 3
    assert report.component_count == 3
    assert report.is_decomposable is True
    assert len(report.clusters) == 3
    for c in report.clusters:
        assert len(c.files) == 1


def test_decomposition_cyclic_intra_cluster():
    target_files = [
        "app/a.py",
        "app/b.py",
        "service/x.py",
        "service/y.py",
    ]
    edges = [
        ("app/a.py", "app/b.py"),
        ("app/b.py", "app/a.py"),  # cycle
        ("service/x.py", "service/y.py"),
    ]
    report = ChangeDecomposer.evaluate_subgraph(
        target_files=target_files,
        dependency_edges=edges,
    )
    assert report.component_count == 2
    assert report.is_decomposable is True
    a_cluster = next(c for c in report.clusters if "app/a.py" in c.files)
    assert a_cluster.internal_edge_count == 2  # a->b and b->a


def test_decomposition_foundational_ordering():
    target_files = [
        "app/api/endpoints.py",
        "app/models/user.py",
    ]
    report = ChangeDecomposer.evaluate_subgraph(
        target_files=target_files,
        dependency_edges=[],
    )
    assert report.component_count == 2
    # Model cluster should be recommended before endpoint cluster
    assert report.clusters[0].files == ["app/models/user.py"]
    assert report.clusters[0].recommended_order == 1
    assert report.clusters[1].files == ["app/api/endpoints.py"]
    assert report.clusters[1].recommended_order == 2


def test_decomposition_serialization():
    target_files = ["app/a.py", "lib/b.py"]
    report = ChangeDecomposer.evaluate_subgraph(
        target_files=target_files,
        dependency_edges=[],
    )
    data = report.to_dict()
    assert data["total_files"] == 2
    assert data["component_count"] == 2
    assert data["is_decomposable"] is True
    assert len(data["clusters"]) == 2
    assert "suggested_pr_title" in data["clusters"][0]
    assert "suggested_branch_name" in data["clusters"][0]
