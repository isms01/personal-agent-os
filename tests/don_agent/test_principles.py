from app.core.don_principles import (
    ALL_PRINCIPLES,
    PRACTICAL_PRINCIPLES,
    PRINCIPLE_LINKAGE_MAP,
    STRUCTURAL_PRINCIPLES,
)


def test_structural_principles_count() -> None:
    assert len(STRUCTURAL_PRINCIPLES) == 3


def test_practical_principles_count() -> None:
    assert len(PRACTICAL_PRINCIPLES) == 7


def test_structural_principle_ids() -> None:
    ids = [p.id for p in STRUCTURAL_PRINCIPLES]
    assert ids == ["S1", "S2", "S3"]


def test_practical_principle_ids() -> None:
    ids = [p.id for p in PRACTICAL_PRINCIPLES]
    assert ids == ["P1", "P2", "P3", "P4", "P5", "X", "Z"]


def test_all_principles_lookup() -> None:
    assert len(ALL_PRINCIPLES) == 10
    for pid in ["S1", "S2", "S3", "P1", "P2", "P3", "P4", "P5", "X", "Z"]:
        assert pid in ALL_PRINCIPLES


def test_each_principle_has_required_fields() -> None:
    for p in STRUCTURAL_PRINCIPLES + PRACTICAL_PRINCIPLES:
        assert p.id
        assert p.name
        assert p.summary
        assert p.core_statement
        assert len(p.activation_signals) >= 1
        assert len(p.application_pattern) >= 1
        assert len(p.anti_pattern) >= 1


def test_linkage_map_keys_are_structural() -> None:
    structural_ids = {p.id for p in STRUCTURAL_PRINCIPLES}
    assert set(PRINCIPLE_LINKAGE_MAP.keys()) == structural_ids


def test_linkage_map_values_are_practical() -> None:
    practical_ids = {p.id for p in PRACTICAL_PRINCIPLES}
    for linked in PRINCIPLE_LINKAGE_MAP.values():
        for pid in linked:
            assert pid in practical_ids


def test_linkage_map_coverage() -> None:
    # 仕様で定義された紐づき（S1→P1,P4,P5,Z / S2→P4,X / S3→P2,P3）
    assert set(PRINCIPLE_LINKAGE_MAP["S1"]) == {"P1", "P4", "P5", "Z"}
    assert set(PRINCIPLE_LINKAGE_MAP["S2"]) == {"P4", "X"}
    assert set(PRINCIPLE_LINKAGE_MAP["S3"]) == {"P2", "P3"}
