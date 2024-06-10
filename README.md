# Stack Overflow for Teams Tag Report (so4t_tag_report)
A Python script that uses the Stack Overflow for Teams API to create a CSV report of how well each tag is performing. You can see an example of what the output looks like in the Examples directory ([here](https://github.com/jklick-so/so4t_tag_report/blob/main/Examples/tag_metrics.csv)).

For a detailed list of metrics included in the report, see [Metrics in the CSV Report](https://github.com/jklick-so/so4t_tag_report/blob/main/Docs/metrics.md)

## Table of Contents
* [Requirements](https://github.com/jklick-so/so4t_tag_report?tab=readme-ov-file#requirements)
* [Setup](https://github.com/jklick-so/so4t_tag_report?tab=readme-ov-file#setup)
* [Basic Usage](https://github.com/jklick-so/so4t_tag_report?tab=readme-ov-file#basic-usage)
* [Advanced Usage](https://github.com/jklick-so/so4t_tag_report?tab=readme-ov-file#advanced-usage)
  * [`--no-api` and `--days`](https://github.com/jklick-so/so4t_tag_report?tab=readme-ov-file#--no-api-and---days)
  * [`--web-client`](https://github.com/jklick-so/so4t_tag_report?tab=readme-ov-file#--web-client)
  * [`--proxy`](https://github.com/jklick-so/so4t_tag_report?tab=readme-ov-file#--proxy)
* [Support, security, and legal](https://github.com/jklick-so/so4t_tag_report?tab=readme-ov-file#support-security-and-legal)

## Requirements
* A Stack Overflow for Teams instance (Basic, Business, or Enterprise)
  * If using a version of Stack Overflow Enterprise prior to 2023.3, please use the [2023.2 branch](https://github.com/jklick-so/so4t_tag_report/tree/2023.2) instead
* Python 3.9 or higher ([download](https://www.python.org/downloads/))
* Operating system: Linux, MacOS, or Windows

If using the `--web-client` argument, there are additional requirements (details in [Advanced Usage](https://github.com/jklick-so/so4t_tag_report#--web-client) section)

## Setup

[Download](https://github.com/jklick-so/so4t_tag_report/archive/refs/heads/main.zip) and unpack the contents of this repository

**Installing Dependencies**

* Open a terminal window (or, for Windows, a command prompt)
* Navigate to the directory where you unpacked the files
* Install the dependencies: `pip3 install -r requirements.txt`

**API Authentication**

For the Basic and Business tiers, you'll need an API token. For Enterprise, you'll need to obtain both an API key and an API token.

* For Basic or Business, instructions for creating a personal access token (PAT) can be found in [this KB article](https://stackoverflow.help/en/articles/4385859-stack-overflow-for-teams-api).
* For Enterprise, documentation for creating the key and token can be found within your instance, at this url: `https://[your_site]/api/docs/authentication`

Creating an access token for Enterpise can sometimes be tricky for people who haven't done it before. Here are some (hopefully) straightforward instructions:
* Go to the page where you created your API key. Take note of the "Client ID" associated with your API key.
* Go to the following URL, replacing the base URL, the `client_id`, and base URL of the `redirect_uri` with your own:
`https://YOUR.SO-ENTERPRISE.URL/oauth/dialog?client_id=111&redirect_uri=https://YOUR.SO-ENTERPRISE.URL/oauth/login_success`
* You may be prompted to login to Stack Overflow Enterprise, if you're not already. Either way, you'll be redirected to a page that simply says "Authorizing Application"
* In the URL of that page, you'll find your access token. Example: `https://YOUR.SO-ENTERPRISE.URL/oauth/login_success#access_token=YOUR_TOKEN`

## Basic Usage

In a terminal window, navigate to the directory where you unpacked the script. 
Run the script using the following format, replacing the URL, token, and/or key with your own:
* For Basic and Business: `python3 so4t_tag_report.py --url "https://stackoverflowteams.com/c/TEAM-NAME" --token "YOUR_TOKEN"`
* For Enterprise: `python3 so4t_tag_report.py --url "https://SUBDOMAIN.stackenterprise.co" --key "YOUR_KEY" --token "YOUR_TOKEN"`

The script can take several minutes to run, particularly as it gathers data via the API. As it runs, it will continue to update the terminal window with the tasks it's performing.

When the script completes, it will indicate the CSV has been exported, along with the name of file. You can see an example of what the output looks like [here](https://github.com/jklick-so/so4t_tag_report/blob/main/Examples/tag_metrics.csv).

## Advanced Usage

There are some additional arguments you can add to the command line to customize the script's behavior, which are described below. All arguments (and instructions) can also be found by running the `--help` argument: `python3 so4t_tag_report.py --help` 

### `--no-api` and `--days`

By default, the CSV report aggregates all historical data for the tags. If you'd like to filter this based on a certain amount of history, the `--days` argument can be used to indicate how many days of history you want to use for the CSV report. If you wanted to pull just the last 90 days worth of data, it would look like this:
`python3 so4t_tag_report.py --url "https://SUBDOMAIN.stackenterprise.co" --key "YOUR_KEY" --token "YOUR_TOKEN" --days 90`

In conjunction with the `--days` argument, `--no-api` allows you to use leverage preexisting JSON data from previous execution of this script. This is significantly faster than running all the API calls again; in fact, it's nearly instantaneous. If you were looking to generate tag metrics based on a variety of time ranges (via `--days`), using the `--no-api` argument sigificantly speeds up the process. 

Example:
* You generate an initial CSV report via the Basic Usage instructions: `python3 so4t_tag_report.py --url "https://SUBDOMAIN.stackenterprise.co" --key "YOUR_KEY" --token "YOUR_TOKEN"`
* As part of collecting data via the API, an `api_data.json` file is generated and stored locally. For subsequent runs of the script where you're trying to generate the report for different time ranges, you can use the preexisting `api_data.json` data by leveraging the `--no-api` argument.
* To quickly generate a CSV report for the past 30 days: `python3 so4t_tag_report.py --no-api --days 30`
* Then, you generate a report for the past 90 days: `python3 so4t_tag_report.py --no-api --days 90`

Note: when using `--no-api`, the `--url`, `--key`, and `--token` arguments are unecessary. When you'd like to update the JSON data via fresh API calls, simply remove the `no-api` argument and add back the required authentication arguments.

### `--web-client`
The `--web-client` argument allows you to gather additional data from Stack Overflow for Teams, particularly data that is **not** available via the API (yet). 

> **NOTE**: For this specific feature of the script, you'll need to make sure you have Google Chrome installed on your computer. When the script runs, you'll be prompted with a login window (via Chrome) for your Stack Overflow for Teams instance. Once you've logged in, that window will close and the script will continue to run.

Here are the additional data points that are obtained when scraping is enabled, along with any additional requirements for obtaining those data points:

* The number of configured webhooks (ChatOps notifications) for each tag [Requirements: admin permissions]
* The number of communities associated with a tag. If there are webhooks configured for a community, the webhook count will be included in the webhook count for the tag. [Requirements: admin permissions]

To use this function, simply append the `--web-client` argument to the end of command for running the Python script. Example: `python3 so4t_tag_report.py --url "https://SUBDOMAIN.stackenterprise.co" --key "YOUR_KEY" --token "YOUR_TOKEN" --web-client`

### `--proxy`
The `--proxy` argument allows you to use a proxy server to make the API calls. This is useful if you're behind a corporate firewall, or if you're running the script on a server that requires a proxy to access the internet.

To use this argument, simply append the `--proxy` argument to the end of the command for running the Python script, including the address of the proxy server in the argument. Example: `python3 so4t_tag_report.py --url "https://SUBDOMAIN.stackenterprise.co" --key "YOUR_KEY" --token "YOUR_TOKEN" --proxy "PROXY.EXAMPLE.COM:PORTNUMBER"`

## Support, security, and legal
Disclaimer: the creator of this project works at Stack Overflow, but it is a labor of love that comes with no formal support from Stack Overflow. 

If you run into issues using the script, please [open an issue](https://github.com/jklick-so/so4t_tag_report/issues). You are also welcome to edit the script to suit your needs, steal the code, or do whatever you want with it. It is provided as-is, with no warranty or guarantee of any kind. If the creator wasn't so lazy, there would likely be an MIT license file included.

All data is handled locally on the device from which the script is run. The script does not transmit data to other parties, such as Stack Overflow. All of the API calls performed are read only, so there is no risk of editing or adding content on your Stack Overflow for Teams instance.
