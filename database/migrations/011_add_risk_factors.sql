-- What the risk tier is made of: the granular risks (ingestion/risk_taxonomy.py
-- slugs) that apply to this use case, derived by rule from its categories,
-- model type, source, deployment modality and risk_basis. The app shows
-- them grouped by family when the tier is tapped. NULL = not yet derived;
-- an empty set is stored as NULL too, since "no rule reached it" is not a
-- finding of safety.
ALTER TABLE banking_use_cases ADD COLUMN IF NOT EXISTS risk_factors TEXT[];
