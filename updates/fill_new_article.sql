ALTER TABLE auth_user 
ADD COLUMN IF NOT EXISTS new_article_cache jsonb;

delete from help_texts where hashtag in (
	'#UserSubmitNewArticleText'
);

INSERT INTO help_texts("hashtag","lang","contents") values (E'#UserSubmitNewArticleText',E'default',E'<p>You cannot upload your preprint on this website. Your preprint must have been deposited on a preprint server or an open archive such as bioRxiv, Zenodo, arXiv, HAL, OSF preprints... and must have a DOI or a specific URL.</p><p><span style="color: red; font-weight: bold;">*</span> <span style="color: #000000;">Mandatory information</span></p>');
