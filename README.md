# Kindergarten Admissions

Mandatory assignment 5 in IS-114 at the University of Agder, autumn 2024. A web application for
applying for a kindergarten place, written in Flask. The application receives an application,
processes it automatically against the number of available places and gives the applicant an
immediate answer (`TILBUD`, an offer, or `AVSLAG`, a rejection). It also shows an overview of all
kindergartens, all submitted applications and statistics on the share of children in kindergarten
per municipality.

The starting point is a code skeleton handed out in the course, and the assignment text is still
left on the front page in `index.html`. What has been written here is the admissions algorithm in
`kgcontroller.py`, the templates for the answer, application overview, kindergarten list and
municipality statistics, and the routes belonging to them in `kg.py`.

## Running Locally

Requires Python 3.10+.

```bash
git clone https://github.com/dovidee/is114-tema05.git
cd is114-tema05
pip install -r requirements.txt
cd barnehage
python kg.py
```

The application runs on `http://127.0.0.1:5000`. All paths in the code are relative, so `kg.py`
must be started from the `barnehage` folder.

The Excel database should have been rebuildable with `python initiatedb.py`, but the file stops
with an `IndentationError` as it stands (see [Notes](#notes)). The kindergarten table in the
SQLite database is reset by uncommenting the "Reset barnehage data" block at the bottom of `kg.py`
and running the file once.

## Technology

| Component | Use |
|-----------|-----|
| Flask | Web framework and routing |
| Flask-SQLAlchemy | ORM against SQLite (`users`, `barnehage`) |
| sqlite3 | Direct SQL in the admissions algorithm |
| pandas | Data processing and reading of Excel files |
| Plotly Express | Bar chart of the municipality statistics |
| Jinja2 | HTML templates |

## Structure

| File | Responsibility |
|------|----------------|
| `barnehage/kg.py` | Flask app, routes and database models |
| `barnehage/kgcontroller.py` | The admissions algorithm, CRUD methods and chart generation |
| `barnehage/kgmodel.py` | Data classes: `Foresatt`, `Barn`, `Barnehage`, `Soknad` |
| `barnehage/dbexcel.py` | Reads `kgdata.xlsx` into DataFrames |
| `barnehage/initiatedb.py` | Creates the Excel database with the initial data |
| `barnehage/templates/` | Jinja2 templates |

| Route | Description |
|-------|-------------|
| `/` | Front page |
| `/barnehager` | Overview of kindergartens and available places |
| `/behandle` | Application form (GET) and processing of an application (POST) |
| `/soknader` | All submitted applications with status |
| `/kommune` | Bar chart of the share of children in kindergarten for the selected municipality |

## Application Processing Algorithm

The processing happens in `behandle_soknad` in `kgcontroller.py`. The application is decided by two
fields: whether the applicant has a **priority right** (child welfare, illness in the family or
illness in the child), and which kindergartens the applicant has **prioritized**.

The priorities are entered as a text string separated by comma and space, in descending priority:

```
ABC Kindergarten, Tiny Tots Academy, Giggles and Grins Childcare, Playful Pals Daycare
```

### Steps

1. The priority string is split on `", "` into a list. An empty string means no priorities.
2. The kindergarten table is read from SQLite into a DataFrame with name, number of places and
   available places.
3. The application follows one of four branches, depending on priority right and priorities (see
   the table below).
4. When a place is assigned, the kindergarten is updated in the database:
   `barnehage_ledige_plasser` is decreased by 1 and `barnehage_antall_plasser` is increased by 1.
5. The application is stored in the `users` table with the assigned kindergarten, status and
   priority right.

### Branches

| Priority right | Priorities | Order of attempts |
|----------------|------------|-------------------|
| No | No | `gi_plass`, otherwise `AVSLAG` |
| No | Yes | `gi_plass_prio`, then `gi_plass` (only if exactly one priority), otherwise `AVSLAG` |
| Yes | No | `gi_plass`, then `stjel_plass`, otherwise `AVSLAG` |
| Yes | Yes | `gi_plass_prio`, then `gi_plass`, then `stjel_plass_full`, otherwise `AVSLAG` |

### Assignment Methods

**`gi_plass`**: free choice. Kindergartens without available places are filtered out, the rest are
sorted in descending order by number of available places, and the top one is chosen. The applicant
therefore gets the kindergarten with the most available places. Fails if no kindergarten has
available places.

**`gi_plass_prio`**: prioritized choice. Only the prioritized kindergartens are kept. These are
sorted in the order the applicant gave, then those without available places are removed, and the
top one is chosen. The applicant therefore gets the highest prioritized kindergarten that actually
has an available place. Fails if none of the prioritized kindergartens have available places.

**`stjel_plass`**: only with priority right, when no places are available. The most recent
application without priority right that has status `TILBUD` is set to `AVSLAG`, and the place is
given to the applicant with priority right. Fails if all existing offers belong to applicants with
priority right.

**`stjel_plass_full`**: the same principle, but targeted. Kindergartens without assigned places are
filtered out, the rest are sorted, and the most recent application without priority right in the
top kindergarten is set to `AVSLAG`. If no such application exists, the method falls back to
freeing an arbitrary place as in `stjel_plass`. The sort is meant to pick the kindergarten with the
most assigned places, but does not (see [Notes](#notes)).

### Examples

With the initial data from `initiatedb.py`, where `ABC Kindergarten` and
`Giggles and Grins Childcare` have zero available places:

- `ABC Kindergarten, Tiny Tots Academy, Giggles and Grins Childcare` gives
  **Tiny Tots Academy**, because the first priority is full and the next priority with an available
  place is chosen.
- `ABC Kindergarten` on its own: the priority is discarded, and the applicant gets the kindergarten
  with the most available places (**Sunshine Preschool**). With more than one priority, where none
  has an available place, the answer is `AVSLAG` instead.

## Troubleshooting

### `attempt to write a readonly database`

The error means that the process running the application does not have write permissions on the
SQLite file. SQLite also creates a journal file next to the database, so the **folder**
`instance/` has to be writable in addition to the file itself:

```bash
chown www-data:www-data barnehage/instance barnehage/instance/db.sqlite3
chmod 755 barnehage/instance
chmod 644 barnehage/instance/db.sqlite3
```

The owner should be the user that **runs the Python process**. If the application is run with
`python kg.py` in a terminal window, that is your own user, and then no `chown` is needed at all.
Under a web server it is the user of the application server (mod_wsgi, gunicorn, uWSGI):

| Distribution | Apache | Nginx |
|--------------|--------|-------|
| Debian / Ubuntu | `www-data` | `www-data` |
| RHEL / Rocky / AlmaLinux / CentOS | `apache` | `nginx` |
| Fedora | `apache` | `nginx` |

Note that Nginx is normally only a reverse proxy and never touches the database file itself; it is
the user of the process behind the proxy that needs write access. On RHEL based systems and Fedora,
SELinux can block writes even with the correct permissions. The file then has to be labelled with
`chcon -t httpd_sys_rw_content_t`.

## Notes

The project was never finished. Assignment 5 was dropped as a requirement during the semester, and
the work stopped where it stood that day. The points below are therefore not mistakes that slipped
through a submission, but a picture of where the code lay when it was put down: half finished
branches, placeholders marked `# fikser senere` (fix later), task 3 which was never started, and an
Excel layer on its way out in favour of SQLite without the move ever being completed. The list
covers what actually breaks or gives the wrong answer, not typos and unused imports, and stands
here as a note to myself.

- `initiatedb.py` does not run. Line 51 opens a triple quoted block indented six spaces inside a
  `with` block indented eight, and Python stops with `IndentationError: unindent does not match any
  outer indentation level` before a single line has been executed. The `kgdata.xlsx` in the repo
  was therefore built with an earlier version of the file, and the script has to be fixed before it
  can be run again.
- `stjel_plass` returns the string `'Unknown'`. It finds the right application to set to `AVSLAG`,
  but does not know which kindergarten the place belonged to, so the applicant gets `TILBUD` at a
  kindergarten that does not exist. The kindergarten table is not touched either, so the freed place
  is registered nowhere: one applicant loses their place, another gets it, and none of the numbers
  in `/barnehager` change. Two `# fikser senere` comments in the same function say most of it.
- `barnehage_antall_plasser` means two different things. In `initiatedb.py` it is the total capacity
  (50, 25, 35, 12, 15, 10, 40), while in SQLite it is set to `0` by the reset block in `kg.py` and
  increased by 1 for every assignment, that is, the number of **assigned** places. The column is
  nevertheless labelled "Antall plasser" (number of places) in `barnehager.html`, so a fresh
  database claims that all seven kindergartens have zero places in total and at the same time have
  available places. The correct name would have been `barnehage_tildelte_plasser`.
- `stjel_plass_full` sorts on the wrong column. The comment says "steal from the highest count" and
  the filtering does remove kindergartens with `barnehage_antall_plasser == 0`, but `sort_values`
  sorts on `barnehage_ledige_plasser`. The method is only reached when everything is full, that is,
  when every available place count is 0, so the sort does nothing and `df.loc[0]` picks the first
  row in id order. The intention was `barnehage_antall_plasser`, and the result is that the place is
  stolen from an arbitrary kindergarten.
- Two bare `except:` clauses without an exception type catch everything, including errors from the
  database, and print `Kan ikke sortere!` (cannot sort) whatever the cause. A misspelled
  kindergarten in the form and a locked or corrupted database file look exactly alike, and both end
  in `AVSLAG` for an applicant who might have been entitled to a place. Errors that should have
  stopped the application turn into an answer instead.
- The priority list is parsed with `split(', ')` and nothing more. If you write a comma without a
  space, the whole string becomes one name that matches nothing. The names are matched with `isin`
  and are therefore literal, and unknown names disappear silently. The applicant never learns that
  the priority was ignored, and the answer looks like a perfectly ordinary decision. A dropdown per
  priority would have removed the whole problem.
- The fallback at exactly one priority is inconsistent. If the applicant has no priority right,
  names exactly one kindergarten and it is full, the priority is discarded and `gi_plass` gives any
  kindergarten at all. With two or more full priorities the answer is `AVSLAG`. Two applicants in
  the same situation therefore get different answers depending on how many kindergartens they
  bothered to list. The check `len(prioritert) == 1` has no counterpart in the priority right
  branch.
- "Fortrinnsrett - Annet" (priority right, other) and "Har søsken som går i barnehagen" (has a
  sibling attending the kindergarten) do nothing. Both fields exist in `soknad.html`, but
  `behandle_soknad` looks only at `fortrinnsrett_barnevern`, `fortrinnsrett_sykdom_i_familien` and
  `fortrinnsrett_sykdome_paa_barnet`, and the `users` table has no columns for the other two. An
  applicant who justifies a priority right in the free text field is processed as if they had no
  priority right at all.
- No validation in `/behandle`. The fields are fetched with `request.form['...']`, which gives a 400
  if a field is missing, and a completely empty application is accepted without objection. The
  `instance/db.sqlite3` in the repo contains exactly such a row: every field empty, status
  `AVSLAG`.
- The `/svar` route shows an empty table. It fetches `session['information']` and passes it on as
  `data`, while `svar.html` reads `sdHar` and `sdStat`. The cells are therefore always empty, and
  the route gives a 500 if no application is in the session. The real answer comes from
  `POST /behandle`, which renders the same template with the right variables. `/svar` is a leftover
  that should have been removed.
- `kommune_bar` crashes on an unknown municipality. `str.fullmatch` is literal and exact, so a typo
  or a lowercase first letter gives an empty selection, and `reduce` over an empty list raises a
  `TypeError` that Flask answers with a 500. `kommune.html` is a free text field without any list of
  valid names, so the error is easy to hit. The function is the same code as `kommune_pie` in
  OBLIG 3 and inherits the same assumptions: `pop(0)` assumes that `Sted` is the first column, and
  `columns.difference(['Sted'])` assumes that the columns sort alphabetically in the same order as
  in the sheet. That holds for `Y2015` to `Y2023`, but it is an assumption and not a guarantee.
- The application will not start without `kgdata.xlsx`. `from dbexcel import *` at the top of
  `kgcontroller.py` reads the Excel file on import, even though the entire pandas layer is unused at
  runtime: `form_to_object_soknad`, `insert_soknad`, `commit_all` and `select_alle_barnehager` are
  imported in `kg.py` and never called, and `Foresatt`, `Barn` and `Soknad` are never created. Only
  `behandle_soknad` and `kommune_bar` are in actual use. The file therefore has to be present for a
  module nothing asks for.

## License

CC0 1.0 Universal. See [LICENSE](LICENSE).
