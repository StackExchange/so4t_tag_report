# Tag ID and Last Used Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `tag_id` and all-time `last_used` fields to each tag's JSON metrics and CSV report without making additional API requests.

**Architecture:** Add one focused preprocessing function that scans the already-fetched questions and articles, validates their Unix creation timestamps, and annotates raw tags with the newest UTC use date. Call it before optional `--days` filtering, then map the raw v3 tag ID and annotation into the existing metrics dictionary.

**Tech Stack:** Python 3.9+, standard-library `datetime`, `unittest`, CSV and Markdown documentation.

---

## File structure

- Modify `so4t_tag_report.py`: derive all-time tag use dates, wire derivation before filtering, and expose both fields in metrics.
- Modify `tests/test_tag_processing.py`: add unit and pipeline-order coverage for date derivation and metric mapping.
- Modify `Docs/metrics.md`: define Tag ID and Last Used semantics.
- Modify `Examples/tag_metrics.csv`: demonstrate the two new output columns and the already-supported Tag Creation Date column.

### Task 1: Derive all-time last-used dates from existing content

**Files:**
- Modify: `tests/test_tag_processing.py:1-72`
- Modify: `so4t_tag_report.py:7-14,233`

- [ ] **Step 1: Write failing tests for question, article, newest-use, unused, invalid, and filtered cases**

Add the imports and update the tag fixture:

```python
import datetime
from unittest.mock import patch


def make_tag(name, tag_id=1, last_used=''):
    return {
        'id': tag_id,
        'name': name,
        'creationDate': '2026-01-01T00:00:00Z',
        'lastUsed': last_used,
        'watcherCount': 0,
        'smes': {
            'users': [],
            'userGroups': [],
        },
    }


def utc_timestamp(year, month, day):
    return int(datetime.datetime(
        year, month, day, tzinfo=datetime.timezone.utc).timestamp())
```

Add these methods to `TagProcessingTests`:

```python
def test_add_last_used_to_tags_uses_question_and_article_dates(self):
    tags = [
        make_tag('question-tag', tag_id=11),
        make_tag('article-tag', tag_id=12),
        make_tag('newest-tag', tag_id=13),
        make_tag('unused-tag', tag_id=14),
    ]
    questions = [
        {'tags': ['question-tag'], 'creation_date': utc_timestamp(2026, 1, 2)},
        {'tags': ['newest-tag'], 'creation_date': utc_timestamp(2026, 2, 3)},
    ]
    articles = [
        {'tags': ['article-tag'], 'creation_date': utc_timestamp(2026, 3, 4)},
        {'tags': ['newest-tag'], 'creation_date': utc_timestamp(2026, 4, 5)},
    ]

    result = so4t_tag_report.add_last_used_to_tags(tags, questions, articles)

    self.assertIs(tags, result)
    self.assertEqual('2026-01-02', result[0]['lastUsed'])
    self.assertEqual('2026-03-04', result[1]['lastUsed'])
    self.assertEqual('2026-04-05', result[2]['lastUsed'])
    self.assertEqual('', result[3]['lastUsed'])

def test_add_last_used_to_tags_ignores_invalid_and_unknown_content(self):
    tags = [make_tag('known-tag')]
    questions = [
        {'tags': ['known-tag'], 'creation_date': 'not-a-timestamp'},
        {'tags': ['known-tag'], 'creation_date': True},
        {'tags': ['unknown-tag'], 'creation_date': utc_timestamp(2026, 5, 6)},
        {'tags': ['known-tag']},
    ]

    result = so4t_tag_report.add_last_used_to_tags(tags, questions, [])

    self.assertEqual('', result[0]['lastUsed'])

def test_last_used_survives_days_filtering(self):
    api_data = {
        'tags': [make_tag('known-tag')],
        'questions': [{
            'tags': ['known-tag'],
            'creation_date': utc_timestamp(2020, 1, 2),
        }],
        'articles': [],
    }
    api_data['tags'] = so4t_tag_report.add_last_used_to_tags(
        api_data['tags'], api_data['questions'], api_data['articles'])

    with patch('so4t_tag_report.time.time', return_value=utc_timestamp(2026, 8, 18)):
        filtered = so4t_tag_report.filter_api_data_by_date(api_data, 30)

    self.assertEqual([], filtered['questions'])
    self.assertEqual('2020-01-02', filtered['tags'][0]['lastUsed'])
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
../../.venv/bin/python -m unittest \
  tests.test_tag_processing.TagProcessingTests.test_add_last_used_to_tags_uses_question_and_article_dates \
  tests.test_tag_processing.TagProcessingTests.test_add_last_used_to_tags_ignores_invalid_and_unknown_content \
  tests.test_tag_processing.TagProcessingTests.test_last_used_survives_days_filtering -v
```

Expected: the first two tests error with `AttributeError: module 'so4t_tag_report' has no attribute 'add_last_used_to_tags'`; the filtered-case test errors for the same reason before reaching its assertions.

- [ ] **Step 3: Implement the minimal last-used derivation**

Add `import datetime` with the standard-library imports. Add this function immediately before `filter_api_data_by_date`:

```python
def add_last_used_to_tags(tags, questions, articles):
    last_used_by_tag = {tag['name']: None for tag in tags}

    for content in questions + articles:
        timestamp = content.get('creation_date')
        if isinstance(timestamp, bool):
            continue
        try:
            formatted_date = datetime.datetime.fromtimestamp(
                timestamp, datetime.timezone.utc).date().isoformat()
        except (TypeError, ValueError, OSError, OverflowError):
            continue

        for tag_name in content.get('tags', []):
            if tag_name not in last_used_by_tag:
                continue
            current = last_used_by_tag[tag_name]
            if current is None or timestamp > current[0]:
                last_used_by_tag[tag_name] = (timestamp, formatted_date)

    for tag in tags:
        last_used = last_used_by_tag[tag['name']]
        tag['lastUsed'] = last_used[1] if last_used else ''

    return tags
```

- [ ] **Step 4: Run focused and complete tests**

Run:

```bash
../../.venv/bin/python -m unittest tests.test_tag_processing -v
```

Expected: 5 tests pass, including the two existing unknown-tag regression tests.

- [ ] **Step 5: Commit the derivation**

```bash
git add so4t_tag_report.py tests/test_tag_processing.py
git commit -m "Add tag last-used date derivation"
```

### Task 2: Wire preprocessing and expose report fields

**Files:**
- Modify: `tests/test_tag_processing.py`
- Modify: `so4t_tag_report.py:41-48,320-353`

- [ ] **Step 1: Write failing tests for metric mapping and pre-filter pipeline order**

Add `from types import SimpleNamespace` with the test imports, then add:

```python
def test_process_tags_includes_tag_id_and_last_used_metrics(self):
    tags = so4t_tag_report.process_tags([
        make_tag('known-tag', tag_id=42, last_used='2026-07-08'),
    ])

    self.assertEqual(42, tags[0]['metrics']['tag_id'])
    self.assertEqual('2026-07-08', tags[0]['metrics']['last_used'])

def test_main_adds_last_used_before_days_filtering(self):
    args = SimpleNamespace(no_api=False, days=30)
    api_data = {
        'tags': [make_tag('known-tag', tag_id=42)],
        'questions': [{
            'tags': ['known-tag'],
            'creation_date': utc_timestamp(2020, 1, 2),
        }],
        'articles': [],
    }

    def assert_metadata_is_ready(data, days):
        self.assertEqual(30, days)
        self.assertEqual('2020-01-02', data['tags'][0]['lastUsed'])
        return data

    with patch('so4t_tag_report.get_args', return_value=args), \
            patch('so4t_tag_report.data_collector', return_value=api_data), \
            patch('so4t_tag_report.filter_api_data_by_date',
                  side_effect=assert_metadata_is_ready) as filter_mock, \
            patch('so4t_tag_report.create_tag_report') as create_mock:
        so4t_tag_report.main()

    filter_mock.assert_called_once()
    create_mock.assert_called_once_with(api_data, 30)
```

- [ ] **Step 2: Run the two focused tests and verify they fail**

Run:

```bash
../../.venv/bin/python -m unittest \
  tests.test_tag_processing.TagProcessingTests.test_process_tags_includes_tag_id_and_last_used_metrics \
  tests.test_tag_processing.TagProcessingTests.test_main_adds_last_used_before_days_filtering -v
```

Expected: the metrics test fails because `tag_id` is absent, and the main-pipeline test fails because `lastUsed` is still empty when filtering starts.

- [ ] **Step 3: Wire all-time preprocessing before `--days` filtering**

In `main`, immediately after the API/no-API branch and before `if args.days`, add:

```python
so4t_data['tags'] = add_last_used_to_tags(
    so4t_data['tags'], so4t_data['questions'], so4t_data['articles'])
```

- [ ] **Step 4: Map raw tag metadata into metrics**

Start the metrics dictionary in `process_tags` with:

```python
tag['metrics'] = {
    'tag_name': tag['name'],
    'tag_id': tag['id'],
    'tag_creation_date': (tag.get('creationDate') or '')[:10],
    'last_used': tag.get('lastUsed', ''),
    'total_page_views': 0,
    'webhooks': 0,
    'tag_watchers': tag['watcherCount'],
    'communities': 0,
    'total_smes': 0,
    'median_time_to_first_answer_hours': 0,
    'median_time_to_first_response_hours': 0,
    'total_unique_contributors': 0,
    'unique_askers': 0,
    'unique_answerers': 0,
    'unique_commenters': 0,
    'unique_article_contributors': 0,
    'question_count': 0,
    'question_upvotes': 0,
    'question_downvotes': 0,
    'question_comments': 0,
    'questions_no_answers': 0,
    'questions_accepted_answer': 0,
    'questions_self_answered': 0,
    'answer_count': 0,
    'sme_answers': 0,
    'answer_upvotes': 0,
    'answer_downvotes': 0,
    'answer_comments': 0,
    'article_count': 0,
    'article_upvotes': 0,
    'article_comments': 0,
}
```

- [ ] **Step 5: Run the complete unit suite**

Run:

```bash
../../.venv/bin/python -m unittest discover -v
```

Expected: 7 tests pass with no errors or failures.

- [ ] **Step 6: Commit pipeline integration and output mapping**

```bash
git add so4t_tag_report.py tests/test_tag_processing.py
git commit -m "Include tag ID and last used in report metrics"
```

### Task 3: Document and demonstrate the fields

**Files:**
- Modify: `Docs/metrics.md:5-9`
- Modify: `Examples/tag_metrics.csv:1-41`

- [ ] **Step 1: Add the two metric definitions**

Add these rows immediately before Tag Creation Date in `Docs/metrics.md`:

```markdown
| Tag ID | The tag's unique API v3 identifier. This remains stable when the tag name is displayed in different report contexts. |
| Last Used | The most recent UTC date on which the tag appeared on a newly created question or article, formatted `YYYY-MM-DD`. This value is all-time even when `--days` filters the other report metrics, and is blank for a tag that has never been used. |
```

- [ ] **Step 2: Update the example CSV shape**

Use a bulk mechanical edit to place the columns after Tag Name. The resulting header must be exactly:

```csv
Tag Name,Tag Id,Tag Creation Date,Last Used,Total Page Views,Webhooks,Tag Watchers,Communities,Total Smes,Median Time To First Answer Hours,Median Time To First Response Hours,Total Unique Contributors,Unique Askers,Unique Answerers,Unique Commenters,Unique Article Contributors,Question Count,Question Upvotes,Question Downvotes,Question Comments,Questions No Answers,Questions Accepted Answer,Questions Self Answered,Answer Count,Sme Answers,Answer Upvotes,Answer Downvotes,Answer Comments,Article Count,Article Upvotes,Article Comments
```

For the 40 illustrative data rows, insert a nonempty sequential Tag Id, `2014-05-13` as the illustrative Tag Creation Date, and `2026-08-18` as the illustrative Last Used value. For example, the first row becomes:

```csv
machine-learning,1,2014-05-13,2026-08-18,551412,22,275,3,15,7.41,4.08,1781,970,763,1014,2,1355,3800,138,1899,222,519,56,1916,2,4426,99,1947,3,6,0
```

Run this exact mechanical rewrite once:

```bash
perl -i -pe 'if ($. == 1) { s/^Tag Name,/Tag Name,Tag Id,Tag Creation Date,Last Used,/ } else { $id = $. - 1; s/^([^,]+),/$1,$id,2014-05-13,2026-08-18,/ }' Examples/tag_metrics.csv
```

- [ ] **Step 3: Verify documentation and CSV consistency**

Run:

```bash
../../.venv/bin/python -c "import csv; rows=list(csv.reader(open('Examples/tag_metrics.csv'))); assert all(len(row)==len(rows[0]) for row in rows); assert rows[0][:4]==['Tag Name','Tag Id','Tag Creation Date','Last Used']; assert all(row[1] and row[2] and row[3] for row in rows[1:])"
rg -n '^\| (Tag ID|Last Used|Tag Creation Date) \|' Docs/metrics.md
```

Expected: both commands exit 0; `rg` prints exactly three metric-definition rows.

- [ ] **Step 4: Commit documentation and example output**

```bash
git add Docs/metrics.md Examples/tag_metrics.csv
git commit -m "Document tag ID and last used metrics"
```

### Task 4: Final verification

**Files:**
- Verify: `so4t_tag_report.py`
- Verify: `tests/test_tag_processing.py`
- Verify: `Docs/metrics.md`
- Verify: `Examples/tag_metrics.csv`

- [ ] **Step 1: Run the complete test suite**

```bash
../../.venv/bin/python -m unittest discover -v
```

Expected: 7 tests pass, 0 failures, 0 errors.

- [ ] **Step 2: Check syntax, whitespace, and worktree state**

```bash
../../.venv/bin/python -m py_compile so4t_tag_report.py tests/test_tag_processing.py
git diff --check main...HEAD
git status --short --branch
```

Expected: compilation and diff checks exit 0; status shows `codex/tag-id-last-used` with no uncommitted changes.

- [ ] **Step 3: Inspect the cumulative change**

```bash
git diff --stat main...HEAD
git log --oneline --decorate main..HEAD
```

Expected: changes are limited to the design/plan documents, tag report implementation, tests, metrics documentation, and example CSV; history contains the planned focused commits.
