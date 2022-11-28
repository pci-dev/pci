from app_modules.utils import all_pci_db_uris


is_admin = auth.has_membership(role="administrator")

stats = lambda: {
    "by pci": by_pci,
    "by status": by_status,
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


def date_field(_=request.vars):
    return dict(
        creation="upload_timestamp",
        decision="last_status_change",
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


def CROSSTAB(rows):
    lines, cols, tab = crosstab(crosstab_as_dict(rows))
    return TABLE(
        TR( TD(),     *[ TD(str(int(v))) for v in cols ]),
     *[ TR( TD(line), *[ TD(str(v or '')) for v in tab[i] ])
            for i, line in enumerate(lines) ]
    )

 
def ALL_CROSSTABS(func):
    return DIV(*[
        DIV(
            P(get_db_from_uri(uri)),
            CROSSTAB(func(uri)),
        )
        for uri in all_pci_db_uris()
    ])


def PAGE(*args):
    return DIV(
        list_stats(butt_style=""),
        PRE(*args),
    )


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
            )
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
