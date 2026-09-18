#!/usr/bin/env python3
"""Build an entity alias table from required_entities in the golden set."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "eci_evm_golden_set_v1.jsonl"
OUTPUT = ROOT / "entity_aliases.json"

KNOWN_ALIASES = {
    "Ballot Unit": ["BU", "ballot unit", "ballot units"],
    "Control Unit": ["CU", "control unit", "control units"],
    "VVPAT": ["VVPAT", "Voter Verifiable Paper Audit Trail", "voter verifiable paper audit trail"],
    "EVM": ["EVM", "EVMs", "Electronic Voting Machine", "Electronic Voting Machines"],
    "ECI-EVM": ["ECI-EVM", "ECI EVM", "ECI Electronic Voting Machine"],
    "FLC": ["FLC", "First Level Checking", "first level checking"],
    "BEL": ["BEL", "Bharat Electronics Limited"],
    "ECIL": ["ECIL", "Electronics Corporation of India Limited"],
    "EMS": ["EMS", "EVM Management System"],
    "EMS 2.0": ["EMS 2.0", "EMS2.0", "EVM Management System 2.0"],
    "SLU": ["SLU", "Symbol Loading Unit"],
    "UADM": ["UADM", "Unauthorized Access Detection Module", "Unauthorised Access Detection Module"],
    "NOTA": ["NOTA", "None of the Above"],
    "DEO": ["DEO", "District Election Officer"],
    "RO": ["RO", "Returning Officer"],
    "ARO": ["ARO", "Assistant Returning Officer"],
    "CAPF": ["CAPF", "Central Armed Police Forces"],
    "GPS": ["GPS", "Global Positioning System"],
    "OTP": ["OTP", "One Time Programmable", "One-Time Programmable"],
    "OTP Chip": ["OTP Chip", "One Time Programmable Chip"],
    "OTP Memory": ["OTP Memory", "One Time Programmed Memory"],
    "Form 17A": ["Form 17A", "17A", "Register for Voters"],
    "Form 17C": ["Form 17C", "17C"],
    "Rule 49MA": ["Rule 49MA", "49MA"],
    "Section 61A": ["Section 61A", "61A"],
    "Power Pack": ["Power Pack", "power pack", "battery"],
    "VVPAT slip": ["VVPAT slip", "VVPAT slips", "printed paper slip"],
    "VVPAT Slips": ["VVPAT Slips", "VVPAT slips", "printed paper slips"],
    "Paper Ballot": ["Paper Ballot", "paper ballot", "ballot paper"],
    "Assembly Constituency": ["Assembly Constituency", "AC"],
    "Assembly Segment": ["Assembly Segment", "AS"],
    "Parliamentary Constituency": ["Parliamentary Constituency", "PC"],
    "Legislative Assembly Constituency": ["Legislative Assembly Constituency", "SLA"],
    "Lok Sabha": ["Lok Sabha", "House of the People", "Parliamentary election"],
}


def generated_aliases(entity: str) -> list[str]:
    aliases = [entity, entity.lower()]
    normalized = re.sub(r"[-_/]+", " ", entity).strip()
    if normalized != entity:
        aliases.append(normalized)
    words = re.findall(r"[A-Za-z0-9]+", entity)
    if len(words) > 1:
        aliases.append("".join(word[0] for word in words).upper())
    if entity.endswith("s") and len(entity) > 1:
        aliases.append(entity[:-1])
    return list(dict.fromkeys(aliases))


def main() -> None:
    counts: Counter[str] = Counter()
    with DATASET.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            counts.update(record["required_entities"])

    entities = []
    for index, (entity, count) in enumerate(sorted(counts.items(), key=lambda item: (-item[1], item[0])), start=1):
        aliases = KNOWN_ALIASES.get(entity, generated_aliases(entity))
        entities.append({
            "id": f"ENT-{index:03d}",
            "canonical": entity,
            "aliases": list(dict.fromkeys(aliases)),
            "question_count": count,
        })

    canonical_names = {entity["canonical"] for entity in entities}
    alias_owners: dict[str, set[str]] = {}
    for entity in entities:
        for alias in entity["aliases"]:
            alias_owners.setdefault(alias, set()).add(entity["canonical"])
    for entity in entities:
        entity["aliases"] = [
            alias
            for alias in entity["aliases"]
            if alias == entity["canonical"]
            or (alias not in canonical_names and len(alias_owners[alias]) == 1)
        ]

    output = {
        "source_dataset": DATASET.name,
        "entity_count": len(entities),
        "entities": entities,
    }
    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "entity_count": len(entities), "top_entities": entities[:10]}, indent=2))


if __name__ == "__main__":
    main()
