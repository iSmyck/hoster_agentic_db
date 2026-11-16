"""Merge notifications for subscribed editors (KBI.3.4)."""

from __future__ import annotations

import uuid
from typing import Any

from ..schemas.source_sync import (
    DeliveryRecord,
    NotificationSubscription,
    NotificationSubscriptionRequest,
)


class Notifier:
    def __init__(self) -> None:
        self._subs: dict[str, NotificationSubscription] = {}
        self.deliveries: list[DeliveryRecord] = []
        self.failures: list[DeliveryRecord] = []
        self.fail_next: int = 0
        self.max_attempts: int = 3

    def subscribe(self, request: NotificationSubscriptionRequest) -> NotificationSubscription:
        record = NotificationSubscription(
            subscription_id=uuid.uuid4().hex,
            editor_stable_id=request.editor_stable_id,
            space_id=request.space_id,
            path=request.path,
            channel=request.channel,
        )
        self._subs[record.subscription_id] = record
        return record

    def notify_merge(
        self,
        *,
        space_id: str,
        path: str,
        payload: dict[str, Any],
    ) -> list[DeliveryRecord]:
        sent: list[DeliveryRecord] = []
        for sub in self._subs.values():
            if sub.space_id != space_id:
                continue
            if not _path_match(sub.path, path):
                continue
            record = self._deliver(sub, path, payload)
            sent.append(record)
        return sent

    def _deliver(
        self,
        sub: NotificationSubscription,
        path: str,
        payload: dict[str, Any],
    ) -> DeliveryRecord:
        attempts = 0
        last_error = ""
        while attempts < self.max_attempts:
            attempts += 1
            if self.fail_next > 0:
                self.fail_next -= 1
                last_error = "injected delivery failure"
                continue
            record = DeliveryRecord(
                editor_stable_id=sub.editor_stable_id,
                space_id=sub.space_id,
                path=path,
                channel=sub.channel,
                attempts=attempts,
                status="sent",
                detail=dict(payload),
            )
            self.deliveries.append(record)
            return record
        failed = DeliveryRecord(
            editor_stable_id=sub.editor_stable_id,
            space_id=sub.space_id,
            path=path,
            channel=sub.channel,
            attempts=attempts,
            status="failed",
            detail={"error": last_error, **payload},
        )
        self.failures.append(failed)
        self.deliveries.append(failed)
        return failed


def _path_match(pattern: str, path: str) -> bool:
    if pattern == path:
        return True
    prefix = pattern if pattern.endswith("/") else f"{pattern}/"
    return path.startswith(prefix)
