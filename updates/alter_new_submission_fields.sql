ALTER TABLE "t_articles" 
DROP COLUMN IF EXISTS no_results_based_on_data,
DROP COLUMN IF EXISTS no_codes_used_in_study,
DROP COLUMN IF EXISTS no_scripts_used_for_result,
ALTER COLUMN  results_based_on_data TYPE character varying(512),
ALTER COLUMN  scripts_used_for_result TYPE character varying(512),
ALTER COLUMN  codes_used_in_study TYPE character varying(512),
ALTER COLUMN  results_based_on_data DROP DEFAULT,
ALTER COLUMN  scripts_used_for_result DROP DEFAULT,
ALTER COLUMN  codes_used_in_study DROP DEFAULT;
