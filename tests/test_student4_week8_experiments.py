"""Check saved pilot provenance and prevent accidental test-result overwrite."""
import json
from pathlib import Path
import pytest
from scripts.student4_week8_evaluate import DATA_DIR, RESULT_DIR, MODEL_PATH, file_hash
from scripts.student4_week8_test import main
from scripts.student4_week8_thresholds import confidence_label


def test_test_result_is_not_overwritten():
    path=RESULT_DIR/'test_comparison.json';before=path.read_bytes()
    with pytest.raises(FileExistsError):main()
    assert path.read_bytes()==before


def test_frozen_result_matches_input_label_model_and_config():
    report=json.loads((RESULT_DIR/'test_comparison.json').read_text())
    for key,path in [('input_sha256',DATA_DIR/'test_inputs.json'),('label_sha256',DATA_DIR/'test_labels.json'),('model_sha256',MODEL_PATH),('config_sha256',DATA_DIR/'experiment_config.json')]:
        assert report[key]==file_hash(path)
    validation=json.loads((DATA_DIR/'validation_inputs.json').read_text())
    test=json.loads((DATA_DIR/'test_inputs.json').read_text())
    assert {x['case_id'] for x in validation}.isdisjoint(x['case_id'] for x in test)
    assert all('expected_decision' not in x for x in validation+test)


@pytest.mark.parametrize('score,high,expected',[(.79,.8,'MEDIUM'),(.8,.8,'HIGH'),(.5,.8,'MEDIUM'),(.49,.8,'LOW'),(.89,.9,'MEDIUM'),(.9,.9,'HIGH')])
def test_threshold_boundaries(score,high,expected):
    assert confidence_label(score,high)==expected


def test_llm_round2_provenance_and_counts():
    report=json.loads((RESULT_DIR/'llm_comparison_round2.json').read_text())
    folder=DATA_DIR/'llm_responses_round2'
    assert report['raw_submission_sha256']==file_hash(folder/'user_supplied_responses_raw.txt')
    assert report['round1_report_sha256']==file_hash(RESULT_DIR/'llm_comparison.json')
    assert report['prompt_manifest_sha256']==file_hash(DATA_DIR/'llm_prompts/manifest.json')
    expected={x['case_id']:x['expected_decision'] for x in json.loads((DATA_DIR/'test_labels.json').read_text())}
    correct=0
    for row in report['cases']:
        assert report['response_sha256'][row['case_id']]==file_hash(folder/f"{row['case_id']}_response.txt")
        raw=json.loads((folder/f"{row['case_id']}_response.txt").read_text())
        assert row['decision']==raw['decision']
        correct+=raw['decision']==expected[row['case_id']]
    assert correct==report['summary']['correct_cases']
