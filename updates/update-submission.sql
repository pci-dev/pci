ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS guide_read boolean NOT NULL DEFAULT true,
ADD COLUMN IF NOT EXISTS approvals_obtained boolean NOT NULL DEFAULT true,
ADD COLUMN IF NOT EXISTS human_subject_consent_obtained boolean NOT NULL DEFAULT true,
ADD COLUMN IF NOT EXISTS lines_numbered boolean NOT NULL DEFAULT true,
ADD COLUMN IF NOT EXISTS funding_sources_listed boolean NOT NULL DEFAULT true,
ADD COLUMN IF NOT EXISTS conflicts_of_interest_indicated boolean NOT NULL DEFAULT true,
ADD COLUMN IF NOT EXISTS no_financial_conflict_of_interest boolean NOT NULL DEFAULT true;
