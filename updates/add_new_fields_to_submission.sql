ALTER TABLE "t_articles" 
ADD COLUMN  IF NOT EXISTS no_results_based_on_data  boolean DEFAULT false,
ADD COLUMN  IF NOT EXISTS results_based_on_data  boolean DEFAULT false,
ADD COLUMN  IF NOT EXISTS data_doi character varying(512),
ADD COLUMN  IF NOT EXISTS no_scripts_used_for_result  boolean DEFAULT false,
ADD COLUMN  IF NOT EXISTS scripts_used_for_result  boolean DEFAULT false,
ADD COLUMN  IF NOT EXISTS scripts_doi character varying(512),
ADD COLUMN  IF NOT EXISTS no_codes_used_in_study  boolean DEFAULT false,
ADD COLUMN  IF NOT EXISTS codes_used_in_study boolean DEFAULT false,
ADD COLUMN  IF NOT EXISTS codes_doi character varying(512);
