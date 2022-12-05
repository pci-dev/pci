from app_modules.utils import all_pci_db_uris


is_admin = auth.has_membership(role="administrator")

stats = lambda: {
    "articles by pci": by_pci,
    "articles by status": by_status,
    "articles by status (all pci)": by_status_all_pci,
    "reviews invites": by_reviews,
    "reviews by states": by_review_states,
    "reviews by states (all pci)": by_review_states_all_pci,
    "": None,
    "review completion durations (days)": review_invited_to_completed,
    "recommended articles submitters emails": emails_recommended_submitters,
}


def index():
    return list_stats()


def years_by_status(uri):
    return DAL(uri).executesql(f"""
    select
        status,
        extract (year from {date_field()}) as year,
        count(id)
    from t_articles
    group by year, status
    order by status, year desc
    """)


def years_totals(uri):
    return DAL(uri).executesql(f"""
    select
        extract (year from {date_field()}) as year,
        count(id)
    from t_articles
    group by year
    """)


def recommended_submitters(uri):
    return DAL(uri).executesql(f"""
    select
        year, string_agg(email, '\n' order by email)
    from (select
        distinct concat(usr.email, art.submitter_details) as email,
        extract (year from art.{date_field()}) as year
    from auth_user as usr
    left join t_articles as art
        on (usr.id = art.user_id)
        where art.status = 'Recommended'
    ) as submitters
    where year > extract(year from now()) - 2
    group by year
    order by year desc
    """)


def review_durations(uri):
    return DAL(uri).executesql(f"""
    select
        year, string_agg(nb_days::text, ',' order by nb_days desc)
    from (select
        {extract_review_year()} as year,
        extract(day from last_change - acceptation_timestamp) as nb_days
        from t_reviews
        where review_state = 'Review completed'
    ) as durations
    group by year
    order by year desc
    """)


extract_review_year = lambda: \
    f"coalesce(extract(year from {review_date_field()}), 0)"

def years_by_review_states(uri):
    return DAL(uri).executesql(f"""
    select
        review_state,
        {extract_review_year()} as year,
        count(id)
    from t_reviews
    group by year, review_state
    order by review_state, year
    """)


def years_by_reviewers(uri):
    return DAL(uri).executesql(f"""
    select
        {extract_review_year()} as year,
        count(distinct reviewer_id)
    from t_reviews
    group by year
    """)


def years_x_review_states(uri, states):
    return DAL(uri).executesql(f"""
    select
        {extract_review_year()} as year,
        count(id)
    from t_reviews
    where review_state in ('{"','".join(states)}')
    group by year
    """)


def years_by_declined(uri):
    return years_x_review_states(uri, [
        'Declined',
        'Declined manually',
        'Declined by recommender',
    ])


def years_by_willing(uri):
    return years_x_review_states(uri, [
        'Willing to review',
    ])


def date_field(_=request.vars):
    return dict(
        creation="upload_timestamp",
        decision="last_status_change",
    ).get(_.date or "creation")


def review_date_field(_=request.vars):
    return dict(
        creation="last_change",
        decision="acceptation_timestamp",
    ).get(_.date or "creation")


@auth.requires(is_admin)
def by_pci():
    return PAGE(
        CROSSTAB(years_by_pci(all_pci_db_uris()))
    )


@auth.requires(is_admin)
def by_status():
    return PAGE(
        ALL_CROSSTABS(years_by_status)
    )


@auth.requires(is_admin)
def by_status_all_pci():
    return PAGE(
        CROSSTAB(stack(years_by_status))
    )


@auth.requires(is_admin)
def by_reviews():
    return PAGE(
        ALL_CROSSTABS(years_by_reviews)
    )


@auth.requires(is_admin)
def by_review_states():
    return PAGE(
        ALL_CROSSTABS(years_by_review_states)
    )


@auth.requires(is_admin)
def by_review_states_all_pci():
    return PAGE(
        CROSSTAB(stack(years_by_review_states))
    )


@auth.requires(is_admin)
def review_invited_to_completed():
    return PAGE(
        ALL_REPORTS(durations_by_year(review_durations))
    )


@auth.requires(is_admin)
def emails_recommended_submitters():
    return PAGE(
        ALL_REPORTS(recommended_submitters_last_2_years)
    )


def years_by_pci(uris):
    stats = {
        get_db_from_uri(uri): years_totals(uri)
        for uri in uris
    }
    rows = []
    for pci in stats:
        for year, total in stats[pci]:
            rows.append([pci, year, total])

    return rows


def years_by_reviews(uri):
    queries = {
        "invited reviewers": years_by_reviewers,
        "declined reviews": years_by_declined,
        "willing to review": years_by_willing,
    }
    rows = []

    for topic, func in queries.items():
        years = func(uri)
        for year, val in years:
            rows.append([topic, year, val])

    return rows


def durations_by_year(query):
    return lambda pci: durations(pci, query)


def durations(pci, query):
    return TABLE(*[
        TR(*[ TD(x) for x in [int(year)] + (values or "").split(",")])
        for year, values in query(pci) if year
    ])


def recommended_submitters_last_2_years(pci):
    return TABLE(*[
        TR(
            TR(int(year)),
            TR(TD(), TD(PRE(emails)))
        )
        for year, emails in recommended_submitters(pci)
    ])


def CROSSTAB(rows):
    lines, cols, tab = crosstab(crosstab_as_dict(rows))
    return TABLE(
        TR( TD(),     *[ TD(str(int(v))) for v in cols ]),
     *[ TR( TD(line), *[ TD(str(v or '')) for v in tab[i] ])
            for i, line in enumerate(lines) ]
    )

 
def ALL_CROSSTABS(func):
    return ALL_REPORTS(func, item=CROSSTAB)


def ALL_REPORTS(func, item=DIV):
    return DIV(*[
        DIV(
            P(get_db_from_uri(uri)),
            item(func(uri)),
        )
        for uri in all_pci_db_uris()
    ])


def PAGE(*args):
    return DIV(
        list_stats(butt_style=""),
        PRE(*args),
    )


def stack(func):
    stats = {
        get_db_from_uri(uri): func(uri)
        for uri in all_pci_db_uris()
    }
    rows = []
    for pci in stats:
        for line, col, val in stats[pci]:
            rows.append([str(line), col, val])
    rows.sort()

    return rows


def crosstab(lines_dict):
    lines = list(lines_dict.keys())
    cols = get_cols(lines_dict)
    tab = [ [ lines_dict[line].get(col) for col in cols ] for line in lines ]

    return lines, cols, tab


def crosstab_as_dict(rows):
    tab = {}
    for row in rows:
        line, column, value = row
        tab.update({ line: tab.get(line) or {} })
        value += tab[line].get(column) or 0
        tab[line].update({column: value})

    return tab


def get_cols(lines_dict):
    cols = {}
    [ cols.update(line) for line in lines_dict.values() ]
    cols = list(cols.keys())
    cols.sort(reverse=True)

    return cols


def get_db_from_uri(uri):
    return uri.split("/")[-1]


def list_stats(butt_style="display:block"):
    return DIV(
        DIV([
            BUTTON(text, _value=URL(f=val),
                _onclick="butt_click(this)",
                _style=butt_style,
            ) \
                if text else BR()
            for text, val in stats().items()
        ]),
        DIV(
        SPAN("date: "),
        *[ LABEL(INPUT(_value=val, _type="radio", _name="date_type"), val)
            for val in [ "creation", "decision"] ],
        ),
        script_for_buttons("date_type"),
        style_for_buttons("selected"),

        _style="margin-bottom:1rem",
    )


def script_for_buttons(_):
    return SCRIPT("""
        function butt_click(butt) {
            document.location = butt.value + '?date=' +
                document.querySelector('input[name="date_type"]:checked')
                .value
        }

        function set_buttons_state() {
            let radio_buttons = 'input[name="date_type"]'
            let val = new URLSearchParams(window.location.search)
                .get("date") || "creation"

            document.querySelector(radio_buttons+'[value="'+val+'"]')
                .checked = "yes"

            document.querySelector(
                'button[value="'+document.location.pathname+'"]')
                .setAttribute("class", "selected")
        }

        window.onload = set_buttons_state
        """)


def style_for_buttons(_):
    return STYLE("""
        button.selected {
            background-color:orange;
            border-radius: .5rem;
            border: solid 1px;
            padding: .2rem .4rem;
        }
    """)
