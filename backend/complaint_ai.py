"""Transparent rule-based complaint triage helpers.

This module deliberately makes advisory suggestions only. It is not a trained
machine-learning model and never changes a complaint's saved priority/status.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

CATEGORY_RULES = {
    "Classroom": ("classroom", "projector", "smart board", "blackboard", "desk", "bench", "fan", "light", "chair"),
    "Laboratory": ("lab", "laboratory", "oscilloscope", "equipment", "apparatus", "experiment", "instrument"),
    "Library": ("library", "book", "journal", "reading room", "issue desk"),
    "Canteen": ("canteen", "cafeteria", "food", "meal", "water cooler", "hygiene"),
    "Hostel": ("hostel", "dorm", "room", "warden", "mess", "bathroom"),
    "Washroom": ("washroom", "toilet", "restroom", "wash basin", "sanitation"),
    "IT Support": ("wifi", "wi-fi", "internet", "network", "computer", "login", "software", "printer", "server"),
    "Infrastructure": ("road", "building", "roof", "leak", "electricity", "power", "drainage", "water supply", "lift"),
}
DEPARTMENTS = {
    "Classroom": "Facilities / Classroom Maintenance",
    "Laboratory": "Laboratory Technical Support",
    "Library": "Library Administration",
    "Canteen": "Canteen Administration",
    "Hostel": "Hostel Administration",
    "Washroom": "Housekeeping / Sanitation",
    "IT Support": "IT Services",
    "Infrastructure": "Facilities and Maintenance",
    "Other": "Student Affairs / Manual Review",
}
HIGH_RISK = ("fire", "smoke", "electric shock", "shock", "exposed wire", "sparking", "gas leak", "injury", "violence", "harassment", "unsafe", "emergency", "flood")
MEDIUM_RISK = ("not working", "broken", "damaged", "leak", "blocked", "repeated", "frequently", "unable to", "cannot")
NEGATIVE = ("bad", "poor", "broken", "not working", "unsafe", "dirty", "leak", "failed", "problem", "issue", "damaged", "unusable")


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (value or "").lower())).strip()


def analyze_complaint(title: str, description: str, selected_category: str | None = None) -> dict:
    text = _clean(f"{title} {description}")
    scores = {category: sum(1 for word in words if _clean(word) in text) for category, words in CATEGORY_RULES.items()}
    detected = max(scores, key=scores.get) if scores and max(scores.values()) else "Other"
    category = detected if detected != "Other" else (selected_category if isinstance(selected_category, str) and selected_category in DEPARTMENTS else "Other")
    high_hits = [word for word in HIGH_RISK if _clean(word) in text]
    medium_hits = [word for word in MEDIUM_RISK if _clean(word) in text]
    if high_hits:
        priority, reason = "High", "Potential safety or urgent-risk wording was detected: " + ", ".join(high_hits[:3]) + "."
    elif medium_hits:
        priority, reason = "Medium", "The description indicates a service failure or recurring issue."
    else:
        priority, reason = "Low", "No explicit urgent-risk wording was detected; administrator review is still required."
    negative_hits = sum(1 for word in NEGATIVE if _clean(word) in text)
    sentiment = "Negative" if negative_hits else "Neutral"
    confidence = 0.45 if category == "Other" else min(0.92, 0.55 + 0.09 * scores.get(category, 0))
    return {
        "category": category,
        "priority": priority,
        "sentiment": sentiment,
        "suggested_department": DEPARTMENTS.get(category, DEPARTMENTS["Other"]),
        "priority_reason": reason,
        "confidence": round(confidence, 2),
        "model_type": "transparent-rule-based-v1",
        "disclaimer": "Advisory rule-based analysis only; verify the complaint and make all final category, priority and assignment decisions manually.",
    }


def find_similar_complaints(title: str, description: str, existing_rows: list[dict], threshold: float = 0.3) -> list[dict]:
    """Return likely duplicates using normalized text similarity, highest first."""
    target = _clean(f"{title} {description}")
    results = []
    for row in existing_rows or []:
        existing = _clean(f"{row.get('title', '')} {row.get('description', '')}")
        if not existing:
            continue
        score = SequenceMatcher(None, target, existing).ratio()
        # Token overlap helps when word order differs substantially.
        left, right = set(target.split()), set(existing.split())
        overlap = len(left & right) / max(1, len(left | right))
        score = max(score, overlap)
        if score >= threshold:
            results.append({
                "complaint_id": row.get("complaint_id"),
                "title": row.get("title"),
                "status": row.get("status"),
                "similarity": round(score, 3),
            })
    return sorted(results, key=lambda item: item["similarity"], reverse=True)[:5]
