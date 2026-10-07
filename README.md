# Stack Internal Tag Report

**Use the [HTML report](tag-report.html).** It is the recommended version of this tool. Keep the `assets/` folder beside the HTML file, open it in a modern browser, connect it to your Stack Internal site with an API access token, and download a CSV report. There is nothing to install.

The Python scripts remain in this repository for historical reference only. They are no longer the recommended way to generate a report.

## Use the HTML report

1. Download this repository and open [tag-report.html](tag-report.html) in your browser, keeping `assets/` beside it.
2. Enter your Teams URL, such as `https://stackoverflowteams.com/c/TEAM-NAME`, or the root URL of your Enterprise site, such as `https://SUBDOMAIN.stackenterprise.co`.
3. Paste a personal access token (Basic or Business) or an OAuth access token (Enterprise) with permission to read the site.
4. Optionally enter a number of days. Leave it blank for an all-time report.
5. Select **Generate report**. When collection finishes, review the preview and select **Download CSV**.

The page collects all API v3 pages, then retrieves answers, comments, and subject matter experts needed for the metrics. Large sites can take time to process. After collection, you can change the days field to recalculate the report without making another API request. **Last Used** always reflects all fetched content, even when the other metrics are limited by days.

The token is cleared from the form when collection starts and is not saved to browser storage or included in the CSV. The page sends it as a Bearer token only to the API host derived from the URL you enter. Check that URL before generating a report. The data stays in the browser tab until you close or reload it.

### Browser access

The API must permit browser requests from the page's origin. The public Teams API currently accepts requests from a locally opened HTML file; Enterprise sites can have different cross-origin settings. If collection stops with a browser access error, your site administrator may need to allow that origin for API v3 requests with the `Authorization` header. The page cannot override the site's browser access policy.

## Report contents

The CSV includes tag usage, page views, watchers, subject matter experts, contributor counts, response times, question and answer counts, article counts, and scores. See [metric definitions](Docs/metrics.md) and a [synthetic example CSV](Examples/tag_metrics.csv).

API v3 exposes a net **score** (upvotes minus downvotes) for questions, answers, and articles. It does not expose separate upvote and downvote totals. The HTML report does not include webhook or community counts; those were optional browser-scraped metrics in the historical Python tool.

## Historical Python scripts

`so4t_tag_report.py` and its supporting Python files are retained for reference. They require Python and the packages in `requirements.txt`, and can optionally collect browser-scraped metrics with `--web-client`. New users should use `tag-report.html`.

## Support

If you encounter a problem, please open a GitHub issue. The report only makes read-only API requests; it does not edit Stack Internal content.
