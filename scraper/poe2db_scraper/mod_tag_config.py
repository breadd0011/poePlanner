from __future__ import annotations

# Tag metadata is parser-normalization config, not a source of game stats.
# Full PoE2DB DOM/ModsView rows expose tags via badge data. These tokens are
# only used when parsing legacy plain-text snapshots where PoE2DB badge text is
# glued to the stat line (for example "# to maximum Life Life").
TAG_COMPONENTS = [
    "Lightning",
    "Elemental",
    "Resistance",
    "Physical",
    "Defences",
    "Critical",
    "Attribute",
    "AttackSpeed",
    "Attack",
    "Damage",
    "Chaos",
    "Cold",
    "Fire",
    "Life",
    "Mana",
    "Speed",
]

COMPOUND_TAG_TOKENS: dict[str, list[str]] = {
    "ElementalLightningResistance": ["Elemental", "Lightning", "Resistance"],
    "ElementalColdResistance": ["Elemental", "Cold", "Resistance"],
    "ElementalFireResistance": ["Elemental", "Fire", "Resistance"],
    "ElementalLightning": ["Elemental", "Lightning"],
    "ElementalCold": ["Elemental", "Cold"],
    "ElementalFire": ["Elemental", "Fire"],
    "DamageElementalLightningAttack": ["Damage", "Elemental", "Lightning", "Attack"],
    "DamageElementalColdAttack": ["Damage", "Elemental", "Cold", "Attack"],
    "DamageElementalFireAttack": ["Damage", "Elemental", "Fire", "Attack"],
    "DamagePhysicalAttack": ["Damage", "Physical", "Attack"],
    "LifePhysicalAttack": ["Life", "Physical", "Attack"],
    "ManaPhysicalAttack": ["Mana", "Physical", "Attack"],
    "PhysicalAttack": ["Physical", "Attack"],
    "LifeDefences": ["Life", "Defences"],
    "ChaosResistance": ["Chaos", "Resistance"],
    "DamageCritical": ["Damage", "Critical"],
    "AttackSpeed": ["Attack", "Speed"],
}

TAG_TOKENS = sorted(set(COMPOUND_TAG_TOKENS) | set(TAG_COMPONENTS), key=len, reverse=True)

TAG_TEXT_BY_DATA_TAG = {
    "life": "Life",
    "mana": "Mana",
    "defences": "Defences",
    "damage": "Damage",
    "physical": "Physical",
    "elemental": "Elemental",
    "fire": "Fire",
    "cold": "Cold",
    "lightning": "Lightning",
    "attack": "Attack",
    "attribute": "Attribute",
    "chaos": "Chaos",
    "resistance": "Resistance",
    "speed": "Speed",
    "critical": "Critical",
}
