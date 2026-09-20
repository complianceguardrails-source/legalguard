-- Use-case categories: what a system DOES (fraud, credit, trading, crypto,
-- insurance ...), as distinct from parent_sector, which is which part of a
-- bank would own it (CIB, Consumer Finance, Front Office ...). Categories
-- are the user-facing axis: the app's landing screen is a multi-select
-- cloud of them, and a use case can legitimately sit in several -- a
-- crypto trading bot is both Crypto & DeFi and Trading & Markets -- so
-- this is an array, not a single label.
--
-- Assigned by ingestion/usecase_categories.py from real evidence (name,
-- description, model card or README prose). NULL means no category
-- matched, and the app hides NULL rows: tagging the corpus showed that
-- roughly a quarter of it is not financial AI at all (interview-question
-- lists, scraping frameworks, an Android tools list -- leaks from bank-org
-- and generic-keyword mining). "No financial category" is the filter that
-- keeps those off the front page without deleting them; the tagger writes
-- the untagged rows to a review list so real ones can be rescued.

ALTER TABLE banking_use_cases
    ADD COLUMN IF NOT EXISTS categories TEXT[];

-- The app filters with array overlap (&&) on the selected categories.
CREATE INDEX IF NOT EXISTS idx_use_cases_categories
    ON banking_use_cases USING GIN (categories);

COMMENT ON COLUMN banking_use_cases.categories IS
    'Use-case categories (what the system does), from ingestion/usecase_categories.py: keyword-matched against the row''s real name, description and card/README prose. Multi-valued by design. NULL = no financial category matched; the app does not show NULL rows.';
