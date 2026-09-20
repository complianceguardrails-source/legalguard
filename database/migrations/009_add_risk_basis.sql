-- The risk tier's working. risk_tier is a keyword classification
-- (ingestion/risk_tier_classifier.py); until now the phrases that tripped
-- it and the legal hook behind each were thrown away, so a card could say
-- "high risk" with nothing to show for it. This holds
-- {"tier", "matched": [phrase...], "basis": [{reference, summary, phrases}]}
-- as produced by explain_risk_tier(), re-derived from the row's stored
-- text by ingestion/backfill_risk_basis.py. NULL means the tier could not
-- be reproduced from stored text (it was set from signals -- repo topics,
-- Hub tags -- that were never persisted), or the row is unclassified.
ALTER TABLE banking_use_cases ADD COLUMN IF NOT EXISTS risk_basis JSONB;
