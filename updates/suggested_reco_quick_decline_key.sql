ALTER table t_suggested_recommenders 
ADD COLUMN if not exists quick_decline_key text;
