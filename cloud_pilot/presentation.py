"""Readable evidence summaries shared by the refund page and UI tests."""
MISSING_LABELS = {'detected_product': 'Product identity in the photo',
                  'claim_image_consistency': 'Support for the stated damage and location',
                  'damage_location': 'Detected damage location'}
REASONS = {
    'damage_type_mismatch': 'The predicted damage type differs from your description.',
    'claimed_damage_not_detected': 'The model did not detect the damage described.',
    'detected_location_missing_or_unsupported': 'The model could not confirm the damage location.',
    'detected_location_not_specific_enough': 'The predicted location is not specific enough.',
    'insufficient_image_quality': 'The photo or claimed area is not clear enough to compare.',
    'visual_review_required': 'The visual result requires review before it can support the claim.',
    'damage_type_matches': 'The predicted damage type matches; no location was claimed.',
    'damage_type_and_location_match': 'The predicted damage type and location match the description.',
    'location_mismatch': 'The predicted location differs from the claimed location.',
    'unsupported_or_missing_claim': 'The description could not be parsed into a supported damage claim.',
    'missing_case_evidence': 'A photo or description is missing.',
    'unsupported_claimed_location': 'The claimed location is not supported by the parser.',
}

def evidence_summary(result):
    visual = result.get('member2', {})
    order_evidence = result.get('member3', {})
    verification = result.get('member2_verification', {})
    verdict = verification.get('verdict')
    return {
        'verdict': {'positive': 'Supports the description', 'negative': 'Does not support the description',
                    'ambiguous': 'Cannot confirm'}.get(verdict, 'Not assessed'),
        'reason': REASONS.get(verification.get('reason_code'), 'See the full analysis for verification details.'),
        'damage': str(visual.get('damage_type') or 'Not identified').replace('_', ' '),
        'product': str(visual.get('detected_product') or 'Not identified').replace('_', ' '),
        'product_confidence': visual.get('product_confidence'),
        'order_match': str(order_evidence.get('image_order_match_status') or 'NOT_AVAILABLE').replace('_', ' ').title(),
        'location': str(visual.get('damage_location') or 'Not identified').replace('_', ' '),
        'missing': [MISSING_LABELS.get(key, key.replace('_', ' ')) for key in result.get('missing_evidence', [])],
    }
