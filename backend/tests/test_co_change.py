from __future__ import annotations

import pytest
from app.history.co_change import (
    CoChangePartner,
    detect_hidden_coupling,
    mine_co_change_partners,
)


def test_mine_co_change_partners() -> None:
    # 5 commits where auth_service and auth_config always change together
    # and logging changes in only 1 commit
    commits = [
        {"src/auth/service.py", "src/auth/config.yaml"},
        {"src/auth/service.py", "src/auth/config.yaml"},
        {"src/auth/service.py", "src/auth/config.yaml"},
        {"src/auth/service.py", "src/auth/config.yaml"},
        {"src/auth/service.py", "src/auth/logging.py"},
    ]

    partners = mine_co_change_partners(commits, min_co_changes=2, min_frequency=0.5)

    assert "src/auth/service.py" in partners
    service_partners = partners["src/auth/service.py"]
    assert len(service_partners) == 1
    assert service_partners[0].partner_file == "src/auth/config.yaml"
    assert service_partners[0].co_change_count == 4
    # Frequency: 4 co-changes out of 5 total changes of service.py = 0.8
    assert service_partners[0].frequency == 0.8


def test_detect_hidden_coupling_warning() -> None:
    co_change_matrix = {
        "src/payment/gateway.py": [
            CoChangePartner(
                target_file="src/payment/gateway.py",
                partner_file="config/payment_credentials.yaml",
                co_change_count=8,
                total_target_changes=10,
                frequency=0.80,
            ),
            CoChangePartner(
                target_file="src/payment/gateway.py",
                partner_file="src/payment/models.py",
                co_change_count=9,
                total_target_changes=10,
                frequency=0.90,
            ),
        ]
    }

    # Static edge exists for models.py, but NOT for credentials.yaml
    known_static_edges = {
        ("src/payment/gateway.py", "src/payment/models.py"),
    }

    # Developer only proposes modifying gateway.py, omitting both
    proposed_files = {"src/payment/gateway.py"}

    warnings = detect_hidden_coupling(proposed_files, co_change_matrix, known_static_edges)

    assert len(warnings) == 2

    # Verify credentials.yaml is flagged as Hidden Coupling
    cred_warning = next(w for w in warnings if w.omitted_partner == "config/payment_credentials.yaml")
    assert cred_warning.has_static_import is False
    assert "Hidden Coupling" in cred_warning.explanation
    assert cred_warning.frequency == 0.80

    # Verify models.py is flagged as Coupled Partner (with static import)
    model_warning = next(w for w in warnings if w.omitted_partner == "src/payment/models.py")
    assert model_warning.has_static_import is True
    assert "Coupled Partner" in model_warning.explanation


def test_hidden_coupling_omission_resolved_when_partner_included() -> None:
    co_change_matrix = {
        "src/payment/gateway.py": [
            CoChangePartner(
                target_file="src/payment/gateway.py",
                partner_file="config/payment_credentials.yaml",
                co_change_count=8,
                total_target_changes=10,
                frequency=0.80,
            ),
        ]
    }

    # If the developer includes the partner in the proposed change, no warning should fire
    proposed_files = {"src/payment/gateway.py", "config/payment_credentials.yaml"}
    warnings = detect_hidden_coupling(proposed_files, co_change_matrix, set())

    assert len(warnings) == 0
