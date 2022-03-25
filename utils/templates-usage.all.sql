select mail_template_hashtag as template, count(id)
from mail_queue
group by template
order by template;
