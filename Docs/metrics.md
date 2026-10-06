# Metrics in the CSV Report
Here is a list of current metrics that are included in the CSV report, as well as what they mean and how they might be used:

The recommended HTML report includes the API v3 metrics below. **Webhooks** and **Communities** were optional metrics in the historical Python browser-scraping mode and are not included in the HTML CSV.


| Metric     | Description                                                                          |
|------------|--------------------------------------------------------------------------------------|
| Tag ID | The stable API v3 identifier for the tag on that site. |
| Last Used | The latest UTC `creationDate` among questions and articles that currently carry the tag, formatted `YYYY-MM-DD`. It is not the date the tag was assigned or a content modification/activity time. This value is all-time even when `--days` filters the other report metrics, and is blank when no currently tagged question or article exists. |
| Tag Creation Date | The date the tag was first created on the site, formatted `YYYY-MM-DD`. Useful for putting other tag metrics in context — a low question count on a brand-new tag is very different from the same count on a tag that's existed for years. |
| Total Page Views | The aggregate number of page views across all questions and articles for a given tag. This can be a helpful measurement of how popular the tag is, as well as how often knowledge is being reused within a given tag.|
| Tag Watchers | The number of users who have subscribed to email notifications for a given tag. This can be a gauge of how much visibility this tag receives when a new question, answer, or article is posted.|
| Communities | The number of communities associated with a given tag. This can be a gauge of how much visibility this tag receives when a new question, answer, or article is posted.|
| Webhooks | The number of webhooks configured for a given tag (i.e. subscriptions to tag notifications via Slack or Microsoft Teams). This can be a gauge of how much visibility this tag receives when a new question, answer, or article is posted.| 
| Total SMEs | The number of unique users who have been configured as a Subject Matter Expert (SME) for a given tag. Configuring SMEs makes it easier for users to route questions to the right people. It also provides a baseline level of ownership/accountability for a given tag.|
| Median Time to First Answer | The median time in hours from a question's creation to its first answer by another user. Self-answers are excluded. |
| Median Time to First Response | The median time in hours from a question's creation to its first answer by another user or first comment by another user, whichever occurs earlier. A response from the asker is excluded. |
| Total Unique Contributors | The number of unique users who have contributed to a given tag (i.e. asked a question, provided an answer, posted a comment, or authored an article). This help measure the overall engagement within a given tag.|
| Unique Askers | The number of unique users who have asked a question within a given tag. |
| Unique Answerers | The number of unique users who have provided an answer within a given tag. |
| Unique Commenters | The number of unique users who have posted a comment within a given tag. |
| Unique Article Contributors | The number of unique users who have authored an article within a given tag. |
| Question Count | The number of questions that have been asked within a given tag. |
| Question Score | The sum of API v3 question scores within a tag. Each score is upvotes minus downvotes; API v3 does not provide the separate counts. |
| Question Comments | The number of comments that have been posted on questions within a given tag. This can be a measure of how engaged the community is within a given tag. |
| Questions No Answers | The number of questions that have been asked within a given tag that have not received an answer. There's oftentimes going to be some amount of questions where there might not be an answer, an answer hasn't been provided yet, or where the question is answered via comments. However, when the number of unanswered questions is high in proportion to the total number of questions for a tag, it can be an indication that there's a lack of proper ownership or accountability for a given tag. In that case, review/improve your corresponding tag metrics for visibility and ownership, such as Tag Watchers, Communities, Webhooks, and/or Total SMEs |
| Questions Accepted Answer | The number of questions that have been asked within a given tag that have received an accepted answer. This is a measure of how good question askers are at accepting the answer that best helped them. Accepting answers can be important for helping future users (who find the same question) to know which answer (if any) solved the problem. In organizations who use Stack Overflow for Teams heavily for internal support, this metric can be important for providing closure to teams who support/own the tag. |
| Questions Self Answered | The number of questions within a tag whose earliest answer was posted by the asker. |
| Answer Count | The number of answers that have been provided within a given tag. In contrast to Questions No Answers, if the answer count is high in proportion to the total number of questions for a tag, it can indicate a high level of engagement within a tag, where multiple viewpoints and/or solutions are being provided. |
| SME Answers | The number of answers that have been provided within a given tag by a Subject Matter Expert (SME). This can be a measure of how much ownership/accountability is being provided by SMEs within a given tag. It can be used inversely to measure how much ownership/accountability is being provided by non-SMEs within a given tag (i.e. community-based support rather than relying too heavily on SMEs). |
| Answer Score | The sum of API v3 answer scores within a tag. Each score is upvotes minus downvotes; API v3 does not provide the separate counts. |
| Answer Comments | The number of comments that have been posted on answers within a given tag. This can be a measure of how engaged the community is within a given tag. Comments on answers are a great way to improve and update answers, by sharing updates, additional insights, asking follow up questions, etc. |
| Article Count | The number of articles that have been authored within a given tag. |
| Article Score | The sum of API v3 article scores within a tag. Each score is upvotes minus downvotes. |
| Article Comments | The number of comments that have been posted on articles within a given tag. This can be a measure of how engaged the community is within a given tag. Comments on articles are a great way to improve and update articles, by sharing updates, additional insights, asking follow up questions, etc. |
