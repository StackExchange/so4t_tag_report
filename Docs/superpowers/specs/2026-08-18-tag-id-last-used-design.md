# Tag ID and Last Used Report Fields

## Goal

Add the tag identifier and the date a tag was most recently used to each tag's report metrics. A tag is used when it appears on a question or article. The new values must be available in both the generated tag data and CSV report.

## Output contract

Each tag's `metrics` object will include:

- `tag_id`: the tag's API v3 `id` value.
- `last_used`: the latest `creation_date` among all questions and articles carrying the tag, formatted as `YYYY-MM-DD` in UTC.

The CSV exporter will render these keys as `Tag Id` and `Last Used`, following its existing underscore-to-title-case convention. A tag with no questions or articles will have an empty `last_used` value.

The existing `tag_creation_date` remains unchanged. It describes when the tag itself was created, while `last_used` describes the latest content creation that used it.

## Data flow

The script already retrieves all questions and articles before it optionally filters them for a `--days` report. It will reuse those responses instead of issuing tag-specific API calls.

1. After API data is loaded or fetched, calculate the newest content creation timestamp for every tag name across the complete question and article collections.
2. Store the formatted value on each raw tag as `lastUsed`. This occurs before `filter_api_data_by_date`, so `--days` cannot erase the all-time value.
3. Initialize report metrics from each raw tag, mapping `id` to `tag_id` and `lastUsed` to `last_used`.
4. Continue filtering and calculating all existing metrics as before.

The calculation will be a focused function that accepts tags, questions, and articles. It will build a tag-name lookup, inspect each content item's `tags` and `creation_date`, keep the maximum timestamp per known tag, and then annotate the tags. Unknown content tags will be ignored consistently with the existing metric processors.

## Date semantics

`last_used` is based only on question and article creation, because these are the content types to which tags can be applied. Answers and comments do not count as tag use. Later activity or modification on tagged content does not update `last_used`.

Unix timestamps will be converted to UTC dates. Keeping the `YYYY-MM-DD` format aligns the field with `tag_creation_date` and avoids local-timezone-dependent report output.

## Error and edge-case handling

- A tag with no tagged questions or articles gets an empty value.
- If both content types use a tag, the later creation timestamp wins.
- Missing or invalid content timestamps are ignored rather than preventing report creation.
- Content that names a tag absent from the current v3 tag collection is ignored.
- Existing saved API data used with `--no-api` remains compatible because the calculation uses the already saved questions, articles, and tag `id` values.

## Testing

Unit tests will cover:

- `tag_id` mapping from the v3 tag object into metrics.
- A tag used only by a question.
- A tag used only by an article.
- Selection of the newest use across questions and articles.
- An unused tag producing an empty `last_used` value.
- Invalid or missing timestamps being ignored.
- Preservation of all-time `last_used` when `--days` filters metric inputs.

The existing test suite will be run after implementation. The metrics reference and example CSV header/data will be updated to document the two fields.

## Non-goals

- Adding one API request per tag.
- Treating answers, comments, views, votes, or edits as tag use.
- Changing the semantics of existing date filtering or metrics.
