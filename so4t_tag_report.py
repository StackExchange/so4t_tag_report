'''
This Python script is a working proof of concept example of using Stack Overflow APIs for a Tag Report. 
If you run into difficulties, please leave feedback in the Github Issues.
'''

# Standard Python libraries
import argparse
import csv
import json
import os
import pickle
import time
import statistics

# Local libraries
from so4t_web_client import WebClient
from so4t_api_v2 import V2Client
from so4t_api_v3 import V3Client


def main():

    # Get command-line arguments
    args = get_args()

    # If --no-api is used, skip API calls and use existing JSON data
    if args.no_api:
        so4t_data = {}
        try:
            so4t_data['questions'] = read_json('questions.json')
            so4t_data['articles'] = read_json('articles.json')
            so4t_data['tags'] = read_json('tags.json')
            #so4t_data['users'] = read_json('users.json')
            so4t_data['webhooks'] = read_json('webhooks.json')
            so4t_data['communities'] = read_json('communities.json')
        except FileNotFoundError:
            print('Required JSON data not found.')
            print('Please run the script without the --no-api argument to collect data via API.')
            raise SystemExit
    else:
        so4t_data = data_collector(args)

    # If --days is used, filter API data by date
    if args.days:
        so4t_data = filter_api_data_by_date(so4t_data, args.days)
        create_tag_report(so4t_data, args.days)
    else:
        create_tag_report(so4t_data)


def get_args():

    parser = argparse.ArgumentParser(
        prog='so4t_tag_report.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Uses the Stack Overflow for Teams API to create \
        a CSV report with performance metrics for each tag.',
        epilog = 'Example for Stack Overflow Business: \n'
                'python3 so4t_tag_report.py --url "https://stackoverflowteams.com/c/TEAM-NAME" '
                '--token "YOUR_TOKEN" \n\n'
                'Example for Stack Overflow Enterprise: \n'
                'python3 so4t_tag_report.py --url "https://SUBDOMAIN.stackenterprise.co" '
                '--key "YOUR_KEY" --token "YOUR_TOKEN"\n\n')
    
    parser.add_argument('--url', 
                        type=str,
                        help='Base URL for your Stack Overflow for Teams instance. '
                        'Required if --no-api is not used')
    parser.add_argument('--token',
                        type=str,
                        help='API token for your Stack Overflow for Teams instance. '
                        'Required if --no-api is not used')
    parser.add_argument('--key',
                        type=str,
                        help='API key value. Required if using Enterprise and --no-api is not used')
    
    parser.add_argument('--no-api',
                        action='store_true',
                        help='If API data has already been collected, skip API calls and use '
                        'existing JSON data. This negates the need for --url, --token, or --key.')
    parser.add_argument('--days',
                        type=int,
                        help='Only include metrics for content created within the past X days. '
                        'Default is to include all history')
    parser.add_argument('--web-client',
                        action='store_true',
                        help='Enables web client for extra data not available via API. Will '
                        'open a Chrome window and prompt manual login.')
    parser.add_argument('--proxy',
                        type=str,
                        help='Used in situations where a proxy is required for API calls. The '
                        'argument should be the proxy server address (e.g. proxy.example.com:8080).')

    return parser.parse_args()


def data_collector(args):

    # Only create a web scraping session if the --web-client flag is used
    if args.web_client:
        session_file = 'so4t_session'
        try:
            with open(session_file, 'rb') as f:
                web_client = pickle.load(f)
            if web_client.base_url != args.url or not web_client.test_session():
                raise FileNotFoundError # force creation of new session
        except FileNotFoundError:
            print('Opening a Chrome window to authenticate Stack Overflow for Teams...')
            web_client = WebClient(args.url)
            with open(session_file, 'wb') as f:
                pickle.dump(web_client, f)
        
    # Instantiate V2Client and V3Client classes to make API calls
    v2client = V2Client(args.url, args.key, args.token, args.proxy)
    v3client = V3Client(args.url, args.token, args.proxy)
    
    # Get all questions, answers, comments, articles, tags, and SMEs via API
    so4t_data = {}
    so4t_data['questions'] = get_questions_answers_comments(v2client) # also gets answers/comments
    so4t_data['articles'] = get_articles(v2client)
    so4t_data['tags'] = get_tags(v3client) # also gets tag SMEs

    # Get additional data via web scraping
    if args.web_client:
        so4t_data['communities'] = web_client.get_communities()
        so4t_data['webhooks'] = web_client.get_webhooks(communities=so4t_data['communities'])
    else:
        so4t_data['webhooks'] = None
        so4t_data['communities'] = None

    # Export API data to JSON file
    for name, data in so4t_data.items():
        export_to_json(name, data)

    return so4t_data


def get_questions_answers_comments(v2client):
    
    # The API filter used for the /questions endpoint makes it so that the API returns
    # all answers and comments for each question. This is more efficient than making
    # separate API calls for answers and comments.
    # Filter documentation: https://api.stackexchange.com/docs/filters
    if v2client.soe: # Stack Overflow Enterprise requires the generation of a custom filter
        filter_attributes = [
            "answer.body",
            "answer.body_markdown",
            "answer.comment_count",
            "answer.comments",
            "answer.down_vote_count",
            "answer.last_editor",
            "answer.link",
            "answer.share_link",
            "answer.up_vote_count",
            "comment.body",
            "comment.body_markdown",
            "comment.link",
            "question.answers",
            "question.body",
            "question.body_markdown",
            "question.comment_count",
            "question.comments",
            "question.down_vote_count",
            "question.favorite_count",
            "question.last_editor",
            "question.notice",
            "question.share_link",
            "question.up_vote_count"
        ]
        filter_string = v2client.create_filter(filter_attributes)
    else: # Stack Overflow Business or Basic
        filter_string = '!X9DEEiFwy0OeSWoJzb.QMqab2wPSk.X2opZDa2L'
    questions = v2client.get_all_questions(filter_string)

    return questions


def get_articles(v2client):

    if v2client.soe:
        filter_attributes = [
            "article.body",
            "article.body_markdown",
            "article.comment_count",
            "article.comments",
            "article.last_editor",
            "comment.body",
            "comment.body_markdown",
            "comment.link"
        ]
        filter_string = v2client.create_filter(filter_attributes)
    else: # Stack Overflow Business or Basic
        filter_string = '!*Mg4Pjg9LXr9d_(v'

    articles = v2client.get_all_articles(filter_string)

    return articles


def get_tags(v3client):

    # While API v2 is more robust for collecting tag data, it does not return the tag ID field, 
    # which is needed to get the SMEs for each tag. Therefore, API v3 is used to get the tag ID
    tags = v3client.get_all_tags()

    # Get subject matter experts (SMEs) for each tag. This API call is only available in v3.
    # There's no way to get SME configurations in bulk, so this call must be made for each tag, 
    # making it a bit slower to get through. 
    # FUTURE WORK: implementing some form of concurrency would speed this up.
    for tag in tags:
        if tag['subjectMatterExpertCount'] > 0:
            tag['smes'] = v3client.get_tag_smes(tag['id']) 
        else:
            tag['smes'] = {'users': [], 'userGroups': []}

    return tags


def get_users(v3client):
    ### THIS FUNCTION IS NOT CURRENTLY USED ###

    users = v3client.get_all_users()

    # Exclude users with an ID of less than 1 (i.e. Community user and user groups)
    users = [user for user in users if user['id'] > 1]

    if 'soedemo' in v3client.api_url: # for internal testing only
        users = [user for user in users if user['id'] > 28000]

    return users


def filter_api_data_by_date(api_data, days):

    today = int(time.time())
    start_date = today - (days * 24 * 60 * 60)  # convert days to seconds

    # Filter questions and articles by creation date
    questions = [question for question in api_data['questions'] 
                 if question['creation_date'] > start_date]
    api_data['questions'] = questions

    articles = [article for article in api_data['articles']
                if article['creation_date'] > start_date]
    api_data['articles'] = articles

    # Uncomment to export filtered data to JSON
    export_to_json('filtered_api_data', api_data)

    return api_data


def create_tag_report(api_data, days=None):

    api_data['tags'] = process_api_data(api_data)
    export_to_json('tag_data', api_data['tags'])

    tag_metrics = [tag['metrics'] for tag in api_data['tags']]
    tag_metrics = sorted(tag_metrics, key=lambda k: k['total_page_views'], reverse=True)

    if days:
        export_to_csv(f'tag_metrics_past_{days}_days', tag_metrics)
    else:
        export_to_csv('tag_metrics', tag_metrics)


def process_api_data(api_data):

    tags = api_data['tags']
    tags = process_tags(tags)
    tags = process_questions(tags, api_data['questions'])
    tags = process_articles(tags, api_data['articles'])
    #tags = process_users(tags, api_data['users'])
    tags = process_communities(tags, api_data.get('communities'))
    tags = process_webhooks(tags, api_data['webhooks'])

    # tally up miscellaneous metrics for each tag
    for tag in tags:
        # Calculate unique contributors
        tag['metrics']['unique_askers'] = len(tag['contributors']['askers'])
        tag['metrics']['unique_answerers'] = len(tag['contributors']['answerers'])
        tag['metrics']['unique_commenters'] = len(tag['contributors']['commenters'])
        tag['metrics']['unique_article_contributors'] = len(
            tag['contributors']['article_contributors'])
        tag['metrics']['total_unique_contributors'] = len(set(
            tag['contributors']['askers'] + 
            tag['contributors']['answerers'] +
            tag['contributors']['commenters'] + 
            tag['contributors']['article_contributors']))
        
        # Calculate total self-answered questions
        tag['metrics']['questions_self_answered'] = len(tag['self_answered_questions'])
        
        # Calculate median time to first answer and median time to first response
        try:
            tag['metrics']['median_time_to_first_response_hours'] = round(statistics.median(
                    [list(response.values())[0] for response in tag['response_times']]), 2)
        except statistics.StatisticsError: # if there are no responses for a tag
            pass
        
        try:
            tag['metrics']['median_time_to_first_answer_hours'] = round(statistics.median(
                [list(answer.values())[0] for answer in tag['answer_times']]), 2)
        except statistics.StatisticsError: # if there are no answers for a tag
            pass

        # Sort responses and answers by time to first response/answer, in descending order
        tag['response_times'] = sorted(
            tag['response_times'], 
            key=lambda k: list(k.values())[0], 
            reverse=True)
        tag['answer_times'] = sorted(
            tag['answer_times'], 
            key=lambda k: list(k.values())[0], 
            reverse=True)
    
    return tags


def process_tags(tags):

    for tag in tags:
        tag['metrics'] = {
            'tag_name': tag['name'],
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
        tag['contributors'] = {
            'askers': [],
            'answerers': [],
            'article_contributors': [],
            'commenters': [],
            'individual_smes': [],
            'group_smes': []
        }
        tag['answer_times'] = []
        tag['response_times'] = []
        tag['self_answered_questions'] = []

        # calculate total unique SMEs, including individuals and groups
        for user in tag['smes']['users']:
            tag['contributors']['individual_smes'] = add_user_to_list(
                user['id'], tag['contributors']['individual_smes'])
        for group in tag['smes']['userGroups']:
            for user in group['users']:
                tag['contributors']['group_smes'] = add_user_to_list(
                    user['id'], tag['contributors']['group_smes'])
        
        tag['metrics']['total_smes'] = len(set(
            tag['contributors']['individual_smes'] + tag['contributors']['group_smes']))
        
    return tags


def process_questions(tags, questions):

    for question in questions:
        for tag in question['tags']:
            tag_index = get_tag_index(tags, tag)
            tag_data = tags[tag_index]
            asker_id = validate_user_id(question['owner'])
            
            tag_data['contributors']['askers'] = add_user_to_list(
                asker_id, tag_data['contributors']['askers'])

            tag_data['metrics']['question_count'] += 1
            tag_data['metrics']['total_page_views'] += question['view_count']
            tag_data['metrics']['question_upvotes'] += question['up_vote_count']
            tag_data['metrics']['question_downvotes'] += question['down_vote_count']

            # Calculate tag metrics for comments
            if question.get('comments'):
                tag_data, time_to_first_comment = process_question_comments(
                    tag_data, question)
            else:
                time_to_first_comment = 0
            
            # calculate tag metrics for answers
            if question.get('answers'):
                tag_data, time_to_first_answer = process_answers(
                    tag_data, question['answers'], question)
            else:
                tag_data['metrics']['questions_no_answers'] += 1
                time_to_first_answer = 0

            # Calculate time to first response, which is the lesser of the time to first comment
            # and the time to first answer
            if time_to_first_answer > 0 and time_to_first_comment > 0:
                time_to_first_response = min(time_to_first_answer, time_to_first_comment)
            elif time_to_first_answer > 0:
                time_to_first_response = time_to_first_answer
            elif time_to_first_comment > 0:
                # If the question is self-answered, the first comment is not considered a response
                if question['link'] not in tag_data['self_answered_questions']:
                    time_to_first_response = time_to_first_comment
                else:
                    time_to_first_response = None
            else:
                time_to_first_response = None

            if time_to_first_response: # if there are no responses, don't add to list
                tag_data['response_times'].append({question['link']: time_to_first_response})
                                        
            tags[tag_index] = tag_data

    return tags

        
def process_answers(tag_data, answers, question):

    for answer in answers:
        answerer_id = validate_user_id(answer['owner'])
        tag_data['contributors']['answerers'] = add_user_to_list(
            answerer_id, tag_data['contributors']['answerers'])
        if answer['is_accepted']:
            tag_data['metrics']['questions_accepted_answer'] += 1
        tag_data['metrics']['answer_count'] += 1
        tag_data['metrics']['answer_upvotes'] += answer['up_vote_count']
        tag_data['metrics']['answer_downvotes'] += answer['down_vote_count']

        # Calculate number of answers from SMEs
        if (answerer_id in tag_data['contributors']['group_smes'] 
            or answerer_id in tag_data['contributors']['individual_smes']):
            tag_data['metrics']['sme_answers'] += 1

        if answer.get('comments'):
            tag_data['metrics']['answer_comments'] += len(answer['comments'])
            for comment in answer['comments']:
                commenter_id = validate_user_id(comment['owner'])
                tag_data['contributors']['commenters'] = add_user_to_list(
                    commenter_id, tag_data['contributors']['commenters']
                )

    # Calculate time to first answer (i.e. response) for questions
    # Deleted answers do not show up in the API response; they are not included in the calculation
        # This creates an outlier/edge case where the original answer was deleted and the next
        # fastest answer is used instead, which could've been posted at a much later time
    # If the fastest response is from the question asker, then the question is self-answered
    # If the fastest answer owner does not have a `user_id` attribute, the owner was deleted
    # If the owner of the question has a 'user_id', we can validate it was not self-answered
    # If both uers have been deleted, the `display_name` attribute can be compared to see if they
        # are the same person
    time_to_first_answer = 0
    if answers[0]['owner'].get('user_id'): # answer owner is known
        if answers[0]['owner']['user_id'] != question['owner'].get('user_id'):
            time_to_first_answer = (answers[0]['creation_date'] - question['creation_date'])/60/60
        else: # if answer owner is the same as question owner, it's a self-answer
            tag_data['self_answered_questions'].append(question['link'])
    elif question['owner'].get('user_id'): # answer owner is unknown, but question owner is known
        time_to_first_answer = (answers[0]['creation_date'] - question['creation_date'])/60/60
    else: # if both question and answer owner are unknown, check display names for a match
        if answers[0]['owner']['display_name'] == question['owner']['display_name']:
            tag_data['self_answered_questions'].append(question['link'])
        else:
            time_to_first_answer = (answers[0]['creation_date'] - question['creation_date'])/60/60

    if time_to_first_answer:
        tag_data['answer_times'].append({question['link']: time_to_first_answer})

    return tag_data, time_to_first_answer


def process_question_comments(tag_data, question):

    tag_data['metrics']['question_comments'] += len(question['comments'])
    for comment in question['comments']:
        commenter_id = validate_user_id(comment['owner'])
        tag_data['contributors']['commenters'] = add_user_to_list(
            commenter_id, tag_data['contributors']['commenters'])

    # Calculate time to first comment
    # There's an edge case where the first comment is from the question asker,
        # where we may want to consider looking at subsequent comments
        # May need to add a check for this
    # If the fastest response is from the question asker, then disregard it
    # If the fastest answer owner does not have a `user_id` attribute, the owner was deleted
    # If the owner of the question has a 'user_id', we can validate it was not self-answered
    # If both uers have been deleted, the `display_name` attribute can be compared to see if they
        # are the same person
    if question['comments'][0]['owner'].get('user_id'):
        if question['comments'][0]['owner']['user_id'] != question['owner'].get('user_id'):
            time_to_first_comment = (question['comments'][0]['creation_date'] - 
                                    question['creation_date'])/60/60
        else:
            time_to_first_comment = 0
    elif question['owner'].get('user_id'):
        time_to_first_comment = (question['comments'][0]['creation_date'] - 
                                    question['creation_date'])/60/60
    else:
        time_to_first_comment = 0

    return tag_data, time_to_first_comment


def process_articles(tags, articles):

    for article in articles:
        for tag in article['tags']:
            tag_index = get_tag_index(tags, tag)
            tag_data = tags[tag_index]
            tag_data['metrics']['total_page_views'] += article['view_count']
            tag_data['metrics']['article_count'] += 1
            tag_data['metrics']['article_upvotes'] += article['score']
            tag_data['metrics']['article_comments'] += article['comment_count']
            tag_data['metrics']['unique_article_contributors'] = len(
                tag_data['contributors']['article_contributors'])

            # Add article author to list of contributors
            article_author_id = validate_user_id(article['owner'])
            tag_data['contributors']['article_contributors'] = add_user_to_list(
                article_author_id, tag_data['contributors']['article_contributors']
            )

            # As of 2023.05.23, Article comments are slightly innaccurate due to a bug in the API
            # if article.get('comments'):
            #     for comment in article['comments']:
            #         commenter_id = validate_user_id(comment)
            #         tag_contributors[tag]['commenters'] = add_user_to_list(
            #             commenter_id, tag_contributors[tag]['commenters']
            #         )
        
            tags[tag_index] = tag_data

    return tags


def process_users(tags, users):
    ### THIS FUNCTION IS NOT CURRENTLY USED ###

    return tags


def process_communities(tags, communities):

    if communities == None: # if no communities were collected, remove the metric from the report
        for tag in tags:
            del tag['metrics']['communities']
        return tags
    
    # Search for tags in community descriptions and add community count to tag metrics
    for community in communities:
        for tag in community['tags']:
            tag_index = get_tag_index(tags, tag['name'])
            try:
                tags[tag_index]['metrics']['communities'] += 1
                try:
                    tags[tag_index]['communities'] += community
                except KeyError: # if communities key does not exist, create it
                    tags[tag_index]['communities'] = [community]
            except TypeError: # get_tag_index returned None
                pass

    return tags


def process_webhooks(tags, webhooks):

    if webhooks == None: # if no webhooks were collected, remove the metric from the report
        for tag in tags:
            del tag['metrics']['webhooks']
        return tags
    
    # Search for tags in webhook descriptions and add webhook count to tag metrics
    for webhook in webhooks:
        for tag_name in webhook['tags']:
            tag_index = get_tag_index(tags, tag_name)
            try:
                tags[tag_index]['metrics']['webhooks'] += 1
            except TypeError: # get_tag_index returned None
                pass
        
    return tags


def get_tag_index(tags, tag_name):

    for index, tag in enumerate(tags):
        if tag['name'] == tag_name:
            return index
    
    return None # if tag is not found


def add_user_to_list(user_id, user_list):
    """Checks to see if a user_id already exists is in a list. If not, it adds the new user_id to 
    the list.

    Args:
        user_id (int): the unique user ID of a particular user in Stack Overflow
        user_list (list): current user list

    Returns:
        user_list (list): updated user list
    """
    if user_id not in user_list:
        user_list.append(user_id)
    return user_list


def validate_user_id(user):

    try:
        user_id = user['user_id']
    except KeyError: # if user_id is not present, the user was deleted
        user_id = f"{user['display_name']} (DELETED)"

    return user_id


def export_to_csv(data_name, data):

    date = time.strftime("%Y-%m-%d")
    file_name = f"{date}_{data_name}.csv"
    directory = 'csv'

    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, file_name)

    csv_header = [header.replace('_', ' ').title() for header in list(data[0].keys())]
    with open(file_path, 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
        for tag_data in data:
            writer.writerow(list(tag_data.values()))
        
    print(f'CSV file created: {file_name}')


def export_to_json(data_name, data):
    
    file_name = data_name + '.json'
    directory = 'data'

    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, file_name)

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

    print(f'JSON file created: {file_name}')


def read_json(file_name):
    
    directory = 'data'
    file_path = os.path.join(directory, file_name)
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        raise FileNotFoundError
    
    return data


if __name__ == '__main__':

    main()
