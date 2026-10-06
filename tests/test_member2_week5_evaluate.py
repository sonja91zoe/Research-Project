from scripts.member2_week5_evaluate import expected_damage_label, metrics, source_safe_groups


def test_week5_groups_variants_with_their_source_image():
    groups = source_safe_groups([
        {"source_image_id": "H001", "case_id": "DDV1-001"},
        {"source_image_id": "H001", "case_id": "DDV1-071"},
    ])
    assert groups == {"H001": ["DDV1-001", "DDV1-071"]}


def test_week5_maps_clean_visual_state_to_no_damage():
    assert expected_damage_label({"damage_type": "none"}) == "no_damage"


def test_week5_metrics_do_not_count_unexecuted_cases():
    result = metrics([{"execution_status": "not_materialized_variant"}], "damage", ("no_damage",))
    assert result["status"] == "not_available"
