UPDATE "t_articles" 
SET results_based_on_data = 'None of the results are based on data' WHERE results_based_on_data = 'false';
UPDATE "t_articles" 
SET results_based_on_data = 'All or part of the results presented in this preprint are based on data' WHERE results_based_on_data = 'true';
UPDATE "t_articles" 
SET scripts_used_for_result = 'No script (e.g. for statistical analysis, like R scripts) was used to obtain or analyze the results' WHERE scripts_used_for_result = 'false';
UPDATE "t_articles" 
SET scripts_used_for_result = 'Scripts were used to obtain or analyze the results' WHERE scripts_used_for_result = 'true';
UPDATE "t_articles" 
SET codes_used_in_study = 'No codes (e.g. codes for original programs or software) were used in this study' WHERE codes_used_in_study = 'false';
UPDATE "t_articles" 
SET codes_used_in_study = 'Codes have been used in this study' WHERE codes_used_in_study = 'true';

