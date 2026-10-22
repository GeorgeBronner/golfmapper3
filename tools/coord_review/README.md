# Course coordinate review

A local tool for checking course locations by hand. Each course is shown on an OpenStreetMap map and a
satellite map with its **current** point (red) and a **proposed** point (green). You can accept the
proposal, move it, or leave the course as it is. Every decision is saved to `data/decisions.json` straight
away. The database is only read; changes reach it through `apply.py`.

It was built for the "Courses sharing one coordinate" task in `tasks/todo.md`, but any list of courses in
the format below can be reviewed.

## Setup

1. Copy `env.sample` to `.env` in this folder and set `COORD_REVIEW_DB` to a local copy of the prod
   `golf_mapper.db` (the review reads current points from it).
2. Put `report_data.json` (and `decisions.json`, if continuing a review) in `data/`.

`.env` and `data/` are git-ignored: they hold local paths and course data.

## Reviewing

From the project root:

```bash
uv run --project backend python tools/coord_review/review.py
```

Then open http://127.0.0.1:8890. The server listens on localhost only and has no login.

- The list puts played courses first, then the rest by confidence, highest first. Stop whenever the
  suggestions stop being useful.
- Drag the green pin, click either map, or paste `lat, lon` into the Proposed box to change the point.
- **Save Change** (`S`) saves the green pin's position, **No Edit** (`N`) keeps the current point, and
  **No Decision** (`D`) skips the course for now. Each choice moves on to the next undecided course.
- **Show** filters the list by decision. Opening a decided course shows an **Undo decision** button.

## Applying decisions

Restore a copy of the DB that matches prod, apply the saves to it, and check the output:

```bash
uv run --project backend python tools/coord_review/apply.py <path to DB copy>
```

- A course is updated only if it is still at the point in `report_data.json`. Courses changed since are
  listed as skipped.
- State and country are re-derived with a Nominatim reverse lookup (about one request per second). They
  change only when the country differs, or when a GBR/USA/CAN/AUS/IRL state differs and the new state is
  specific (not ENG/SCT/WLS/NIR or blank).
- The script prints the integrity check, row counts and any state/country changes.

Then swap the copy into prod the usual way (stop `gm3-backend`, check prod's hash still matches, back up,
copy in, start) and commit the DB to `keys`.

Once it is live, record the batch as applied, using the DB now in `keys` (same as prod):

```bash
uv run --project backend python tools/coord_review/apply.py --mark <path to live DB copy>
```

This adds an `"applied"` date to each save whose course is now at the saved point, so the next apply
skips it. Stop the review server before running it: the server holds decisions in memory, and its next
save would overwrite the file.

## Data format

### `data/report_data.json` (input)

```json
{
  "remaining": [
    {
      "id": 15624,
      "group": 409,
      "category": "C",
      "club_name": "St. Andrews",
      "course_name": "Castle",
      "country": "GBR",
      "lat": 56.349815,
      "lon": -2.817122,
      "played": 1,
      "status": "still shared",
      "confidence": 75,
      "note": "",
      "guess_source": "osm",
      "guess_name": "The Castle Course",
      "guess_lat": 56.328838,
      "guess_lon": -2.753858,
      "guess_dist": 4.54
    }
  ],
  "moves": [
    {
      "club_name": "St. Andrews",
      "course_name": "Old Course",
      "old_lat": 56.349815,
      "old_lon": -2.817122,
      "new_lat": 56.3434,
      "new_lon": -2.8031
    }
  ]
}
```

`remaining` is the review list, one entry per course:

| Field | Use |
|---|---|
| `id` | `courses.id` |
| `lat`, `lon` | The point when the list was made. `apply.py` updates a course only if it is still there. |
| `group` | Any key shared by courses that should be shown together. Courses with the same `group` are listed as "Shares the point with". |
| `category` | `C` (one club, several courses) or `E` (different clubs). Only used for the label. |
| `played` | Number of users who have played it. Courses with `played > 0` are listed first. |
| `confidence` | 0–100. Sets the order and the colour of the badge. |
| `status`, `note` | Free text shown under the course name (`note` in amber). |
| `guess_*` | The proposed point and where it came from. `guess_source` is `osm`, `gcb`, `oga`, `nominatim` or empty. Set `guess_lat`/`guess_lon` to `null` when there is no proposal; the page then starts without a green pin. |

`moves` is optional context. Each entry is a course already moved away from a point (`old_lat`/`old_lon`).
On a course whose current point matches it, the course appears as a blue pin at `new_lat`/`new_lon`. Use
`"moves": []` if there are none.

The tool shows the current point from the DB (`COORD_REVIEW_DB`), not from `lat`/`lon`. A course that is
not in the DB is left out of the list.

### `data/decisions.json` (output)

Keyed by course id. Created by the tool on the first decision.

```json
{
  "15624": {"decision": "save", "at": "2026-10-22T14:03:11+00:00", "lat": 56.3279104, "lon": -2.7545794, "applied": "2026-10-22"},
  "22870": {"decision": "no_edit", "at": "2026-10-22T14:05:40+00:00"},
  "8123": {"decision": "undecided", "at": "2026-10-22T14:06:02+00:00"}
}
```

`decision` is `save` (with `lat`/`lon`), `no_edit` or `undecided` (the No Decision button). `applied` is
added after a batch is live, and `apply.py` skips entries that have it.

## Starting a new review

1. Write a new `data/report_data.json` in the format above. Any script can build it; only `remaining` is
   required, plus an empty `moves` list.
2. Move the old `data/decisions.json` out of the way, or keep it if the same course ids should stay
   decided.
3. Run the review, then apply as above.
