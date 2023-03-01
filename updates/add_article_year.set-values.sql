update t_articles as art
set article_year = greatest(
	reco.year,
	extract(year from art.upload_timestamp)
)
from (
	select article_id,
	extract(year from max(validation_timestamp)) as year
	from t_recommendations group by article_id
) as reco
where art.id = reco.article_id;

-- show articles likely to need manual fix
-- (articles with null article_source are not listed)
select
	id,
	article_year,
	substring(article_source from 0 for 40) as art_source

from t_articles
where not (article_source ~ cast(article_year as text))
order by id;
