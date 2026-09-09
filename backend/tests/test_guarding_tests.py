from __future__ import annotations

from app.history.guarding_tests import (
    analyze_guarding_tests,
    detect_verification_gaps,
    rank_tests_by_reach,
)


def test_rank_tests_by_reach() -> None:
    # Test suite A covers 3 of the changed files
    # Test suite B covers 1 changed file
    # Test suite C covers 2 changed files
    test_to_covered = {
        "tests/integration/test_checkout_flow.py": {
            "src/cart.py",
            "src/checkout.py",
            "src/payment.py",
        },
        "tests/unit/test_cart.py": {"src/cart.py"},
        "tests/integration/test_payment_api.py": {"src/checkout.py", "src/payment.py"},
        "tests/unit/test_user.py": {"src/user.py"},  # touches no changed file
    }

    changed_files = {"src/cart.py", "src/checkout.py", "src/payment.py"}

    ranked = rank_tests_by_reach(test_to_covered, changed_files)

    assert len(ranked) == 3

    # #1 should be test_checkout_flow with 3 reached targets
    assert ranked[0].test_file == "tests/integration/test_checkout_flow.py"
    assert ranked[0].reached_target_count == 3

    # #2 should be test_payment_api with 2 reached targets
    assert ranked[1].test_file == "tests/integration/test_payment_api.py"
    assert ranked[1].reached_target_count == 2

    # #3 should be test_cart with 1 reached target
    assert ranked[2].test_file == "tests/unit/test_cart.py"
    assert ranked[2].reached_target_count == 1


def test_detect_verification_gaps() -> None:
    file_to_tests = {
        # payment.py is guarded by test_payment.py
        "src/payment.py": {"tests/test_payment.py"},
        # legacy.py has zero guarding tests
        "src/legacy.py": set(),
    }

    # Case 1: legacy.py changed -> flagged as Untested Change
    # payment.py changed, but tests/test_payment.py NOT in diff -> flagged as Stale Test Candidate
    proposed = {"src/payment.py", "src/legacy.py"}
    diff_files = {"src/payment.py", "src/legacy.py"}

    untested, stale = detect_verification_gaps(proposed, file_to_tests, diff_files)

    assert len(untested) == 1
    assert untested[0].target_file == "src/legacy.py"
    assert "Untested Change" in untested[0].explanation

    assert len(stale) == 1
    assert stale[0].target_file == "src/payment.py"
    assert "Stale Test Candidate" in stale[0].explanation


def test_analyze_guarding_tests_report() -> None:
    file_to_tests = {
        "src/auth.py": {"tests/test_auth.py", "tests/test_integration.py"},
        "src/session.py": {"tests/test_integration.py"},
    }

    # Developer modified both auth.py and session.py, and also updated test_auth.py
    proposed = {"src/auth.py", "src/session.py"}
    diff_files = {"src/auth.py", "src/session.py", "tests/test_auth.py"}

    report = analyze_guarding_tests(proposed, file_to_tests, diff_files)

    # 1. Reach Ranking
    assert report.total_guarding_tests == 2
    # test_integration reaches both files (reach = 2)
    assert report.ranked_tests[0].test_file == "tests/test_integration.py"
    assert report.ranked_tests[0].reached_target_count == 2
    # test_auth reaches only auth.py (reach = 1)
    assert report.ranked_tests[1].test_file == "tests/test_auth.py"
    assert report.ranked_tests[1].reached_target_count == 1

    # 2. Verification Gaps
    # auth.py is NOT stale because tests/test_auth.py is in diff_files
    # session.py IS stale candidate because test_integration.py was NOT in diff_files
    assert len(report.untested_changes) == 0
    assert len(report.stale_test_candidates) == 1
    assert report.stale_test_candidates[0].target_file == "src/session.py"
