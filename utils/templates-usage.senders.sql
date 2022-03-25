select
    mail_template_hashtag as template,
    groups,
    count(mail_queue.id)
from
    mail_queue
    inner join auth_user
    on (auth_user.id = user_id)
    left outer join (
        SELECT
        user_id, string_agg(group_id::text, ','
                   order by group_id) as groups
        from auth_membership
        group by user_id
    ) as g
    on (auth_user.id = g.user_id)
group by template, groups
order by template;
