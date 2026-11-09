"""Synthetic repository-per-Space fixtures."""

from __future__ import annotations

import copy

# Stable IDs and synthetic hashes imported from t01-contract-tests.yaml.

SALES = {
    "space_id": "sales",
    "repository_id": "repo-sales",
    "policy_bundle_id": "bundle-sales-v1",
    "access_policy_revision": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "approval_policy_revision": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "group_snapshot": {
        "snapshot_id": "gs-sales-1",
        "captured_at": "2026-11-08T00:00:00Z",
        "groups": ["sales-authors", "sales-approvers"],
    },
    "revocation_epoch": 1,
    "active_snapshot": True,
    "readers": ["user-sales-1"],
    "authors": ["user-sales-2"],
    "approvers": ["user-sales-3"],
}

SALES_PRICING = {
    "space_id": "sales-pricing",
    "repository_id": "repo-sales-pricing",
    "policy_bundle_id": "bundle-pricing-v1",
    "access_policy_revision": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "approval_policy_revision": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "group_snapshot": {
        "snapshot_id": "gs-pricing-1",
        "captured_at": "2026-11-08T00:00:00Z",
        "groups": ["pricing-authors", "pricing-approvers"],
    },
    "revocation_epoch": 2,
    "active_snapshot": True,
    "readers": ["user-pricing-1"],
    "authors": ["user-pricing-2"],
    "approvers": ["user-pricing-3"],
}


def sales_space() -> dict:
    return copy.deepcopy(SALES)


def sales_pricing_space() -> dict:
    return copy.deepcopy(SALES_PRICING)
