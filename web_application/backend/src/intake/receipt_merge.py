"""Utilities for deterministic receipt text merge into classifier input."""

from __future__ import annotations


def normalize_text(text: str) -> str:
    return ' '.join(text.strip().split())


def merge_receipt_context(complaint_text: str, receipt_text: str | None) -> tuple[str, bool]:
    complaint = normalize_text(complaint_text)
    if not receipt_text or not receipt_text.strip():
        return complaint, False

    receipt = normalize_text(receipt_text)
    merged = f'{complaint}\n\n[RECEIPT_CONTEXT]\n{receipt}'
    return merged, True