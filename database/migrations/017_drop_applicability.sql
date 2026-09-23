-- Geospatial capabilities are part of the catalogue, not a class apart.
--
-- 016 held them separately on the grounds that a system adapted to
-- finance is not a system already doing the job. In use that split cost
-- more than it protected: the systems were invisible where a reader
-- looks for them, under Spatial Finance and the category each one would
-- serve. They now sit with everything else, and translation still
-- carries the honest part -- the financial decision the system could
-- feed, and what a firm would have to supply first -- shown on the card
-- as its label and in full on the detail screen.
DROP INDEX IF EXISTS idx_use_cases_applicability;
ALTER TABLE banking_use_cases DROP COLUMN IF EXISTS applicability;
