# Standard Python libraries
import re
import time

# Third-party libraries
import requests
from selenium import webdriver
from bs4 import BeautifulSoup


class WebClient(object):
    
    def __init__(self, url):
    
        if "stackoverflowteams.com" in url: # Stack Overflow Business or Basic
            self.soe = False
        else: # Stack Overflow Enterprise
            self.soe = True
        
        self.base_url = url
        self.s = self.create_session() # create a Requests session with authentication cookies
        self.admin = self.validate_admin_permissions() # check if user has admin permissions


    def create_session(self):

        s = requests.Session()

        # Configure Chrome driver
        options = webdriver.ChromeOptions()
        options.add_argument("--window-size=500,800")
        options.add_experimental_option("excludeSwitches", ['enable-automation'])
        driver = webdriver.Chrome(options=options)

        # Check if URL is valid
        try:
            response = requests.get(self.base_url)
        except requests.exceptions.SSLError:
            print(f"SSL certificate error when trying to access {self.base_url}.")
            print("Please check your URL and try again.")
            raise SystemExit
        except requests.exceptions.ConnectionError:
            print(f"Connection error when trying to access {self.base_url}.")
            print("Please check your URL and try again.")
            raise SystemExit
        
        if response.status_code != 200:
            print(f"Error when trying to access {self.base_url}.")
            print(f"Status code: {response.status_code}")
            print("Please check your URL and try again.")
            raise SystemExit
        
        # Open a Chrome window and log in to the site
        driver.get(self.base_url)
        while True:
            try:
                # if user card is found, login is complete
                driver.find_element("class name", "s-user-card")
                break
            except:
                time.sleep(1)
        
        # pass authentication cookies from Selenium driver to Requests session
        cookies = driver.get_cookies()
        for cookie in cookies:
            s.cookies.set(cookie['name'], cookie['value'])
        driver.close()
        driver.quit()
        
        return s
    

    def test_session(self):

        soup = self.get_page_soup(f"{self.base_url}/users")
        if soup.find('li', {'role': 'none'}): # this element is only shows if the user is logged in
            return True
        else:
            return False


    def validate_admin_permissions(self):

        # The following URLs are only accessible to users with admin permissions
        # If the user does not have admin permissions, the page will return a 404 error
        if self.soe:
            admin_url = self.base_url + '/enterprise/admin-settings'
        else:
            admin_url = self.base_url + '/admin/settings'

        response = self.get_page_response(admin_url)
        if response.status_code != 200:
            print("User does not have admin permissions.")
            return False
        else:
            return True


    def test_session(self):

        soup = self.get_page_soup(f"{self.base_url}/users")
        if soup.find('div', {'class': 's-avatar'}):
            return True
        else:
            return False


    def get_communities(self):
        """
        This function gets all communities on the Stack Overflow for Teams instance
        Returns:
            communities: list of dictionaries, where each dictionary is a community
        
        Each community has the following keys:
            name: str
            id: int
            url: str
            description: str
            tags: list of dictionaries, where each dictionary is a tag
            members: list of dictionaries, where each dictionary is a user
        """

        print("Getting communities")
        communities_url = f"{self.base_url}/communities"
        communities_page = self.get_page_soup(communities_url)
        community_grid = communities_page.find('div', {'class': 'd-grid'})

        try:
            community_cards = community_grid.find_all('article')
        except AttributeError: # no communities found
            print('Communities feature not turned on.')
            return None

        communities = []
        for card in community_cards:
            community = {
                'name': card.find('h3').text,
                'id': int(card.find('a')['href'].split('/')[-1]),
                'url': f"{communities_url}/{card.find('a')['href'].split('/')[-1]}",
                'description': card.find('p').text,
                'tags': [],
                'members': []
            }

            # Get community tags
            tags = card.find('ul').find_all('li')
            for tag in tags:
                tag_info = {
                    'name': tag.find('span').text,
                    'id': int(tag.find('a')['href'].split('/')[-1]),
                    'url': f"{self.base_url}/tags/{tag.find('a')['href'].split('/')[-1]}"
                }
                community['tags'].append(tag_info)

            # Get community members
            print(f"Getting membership for the {community['name']} community")
            members_url = f"{community['url']}/members"
            member_table = self.get_page_soup(members_url).find('tbody')

            try:
                member_rows = member_table.find_all('tr')
            except AttributeError: # no members found
                print(f"No members found for the {community['name']} community")
                continue

            for row in member_rows:
                name_column = row.find('th')
                name_field = name_column.find_all('a')[-1]
                member = {
                    'name': self.strip_html(name_field.text),
                    'id': int(name_field['href'].split('/')[-1]),
                    'url': f"{self.base_url}/users/{name_field['href'].split('/')[-1]}"
                }
                community['members'].append(member)

            communities.append(community)

        return communities


    def get_user_title_and_dept(self, users):
        """
        This function goes to the profile page of each user and gets their title and department
        Requires that the title and department assertions have been configured in the SAML
        settings; otherwise, the title and department will not be displayed on the profile page
        
        Args:
            users: list of user dictionaries obtained from the /users API endpoint

        Returns:
            users: list of user dictionaries with 'title' and 'department' keys added
        """

        for user in users:
            if user['user_id'] <= 1: # skip the Community user and user groups
                continue

            print(f"Getting title and department for user ID {user['user_id']}")
            user_url = f"{self.base_url}/users/{user['user_id']}"
            soup = self.get_page_soup(user_url)
            title_dept = soup.find('div', {'class': 'mb8 fc-light fs-title lh-xs'})
            try:
                user['department'] = title_dept.text.split(', ')[-1]
                user['title'] = title_dept.text.split(f", {user['department']}")[0]
            except AttributeError: # if no title/dept returned, `text` method will not work on None
                user['department'] = ''
            except IndexError: # if using old title format
                user['title'] = title_dept.text
                user['department'] = ''
        
        return users
    

    def get_user_watched_tags(self, users):
        """
        This function goes to the watched tags page of each user and gets their watched tags
        It requires Stack Overflow Enterprise and admin permissions, both of which are checked for

        Args:
            users: list of user dictionaries obtained from the /users API endpoint

        Returns:
            users: list of user dictionaries with 'watched_tags' key added
        """

        if not self.soe: # check if using Stack Overflow Enterprise
            print('Not able to obtain user watched tags. This is only available on '
                  'Stack Overflow Enterprise.')
            return users
        
        if not self.admin: # check if user has admin permissions
            print('Not able to obtain user watched tags. This requires admin permissions.')
            return users

        for user in users:
            if user['user_id'] <= 1: # skip the Community user and user groups
                continue

            print(f"Getting watched tags for user ID {user['user_id']}")
            watched_tags_url = f"{self.base_url}/users/tag-notifications/{user['user_id']}"
            soup = self.get_page_soup(watched_tags_url)
            try:
                watched_tag_rows = soup.find('table', {'class': '-settings'}).find_all('tr')
                user['watched_tags'] = [self.strip_html(tag.find('td').text) 
                                        for tag in watched_tag_rows]
            except AttributeError: # if user has no watched tags
                print(f"User ID {user['user_id']} does not have a watched tags page")
                user['watched_tags'] = []
                pass

        return users


    def get_user_login_history(self, users):
        """
        This function goes to the account page of each user and gets their login history and
        # presents it as a list of timestamps
        It requires Stack Overflow Enterprise and admin permissions, both of which are checked for

        Args:
            users: list of user dictionaries obtained from the /users API endpoint
        
        Returns:
            users: list of user dictionaries with 'login_history' key added
        """

        if not self.soe: # check if using Stack Overflow Enterprise
            print('Not able to obtain user login history. This is only available on '
                  'Stack Overflow Enterprise.')
            return users
        
        if not self.admin: # check if user has admin permissions
            print('Not able to obtain user login history. This requires admin permissions.')
            return users

        for user in users:
            if user['user_id'] <= 1: # skip the Community user and user groups
                continue

            print(f"Getting login history for account ID {user['account_id']}")
            account_url = f"{self.base_url}/accounts/{user['account_id']}"
            soup = self.get_page_soup(account_url)
            try:
                login_history = soup.find(
                    'h2', string=re.compile('Login Histories')).find_next_sibling('table')
            except AttributeError: # if user has no login history
                user['login_history'] = []
                continue
            
            login_timestamps = []
            for row in login_history.find_all('tr'):
                if row.find('th'): # skip the header row
                    continue
                timestamp = row.find('td').find('span')['title']
                # create datetime object from timestamp string
                # timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%SZ')
                login_timestamps.append(timestamp)
            user['login_history'] = login_timestamps

        return users
    

    def get_webhooks(self, communities=None):
        """
        This function gets all webhooks configured for Stack Overflow for Teams instance
        It requires admin permissions, which is checked for
        The scraped data requires a bit of processing to get it into a usable format, which has
        been split off into a separate process_webhooks function
        
        Returns:
            webhooks: list of dictionaries, where each dictionary is a webhook

        Each webhook has the following keys:
            type: str
            channel: str
            tags: list of strings
            activities: list of strings
            creation_date: str
        """

        if not self.admin: # check if user has admin permissions
            print('Not able to obtain webhook data. User is not an admin or URL is invalid')
            return None
        
        webhooks = []
        if self.soe: # Stack Overflow Enterprise
            webhooks_url = f"{self.base_url}/enterprise/webhooks"
            page_count = self.get_page_count(webhooks_url + '?page=1&pagesize=50')
            for page in range(1, page_count + 1):
                print(f"Getting webhooks from page {page} of {page_count}")
                page_url = webhooks_url + f'?page={page}&pagesize=50'
                webhooks += self.scrape_webhooks_page(page_url, communities)
            print(f"Found {len(webhooks)} webhooks")

        else: # Stack Overflow Business or Basic
            slack_webhooks_url = f"{self.base_url}/admin/integrations/slack"
            print(f"Getting webhooks from {slack_webhooks_url}")
            webhooks += self.scrape_webhooks_page(slack_webhooks_url, communities)
            print(f"Found {len(webhooks)} Slack webhooks")

            msteams_webhooks_url = f"{self.base_url}/admin/integrations/microsoft-teams"
            print(f"Getting webhooks from {msteams_webhooks_url}")
            webhooks += self.scrape_webhooks_page(msteams_webhooks_url, communities)
            print(f"Found {len(webhooks)} Microsoft Teams webhooks")

        return webhooks
    

    def scrape_webhooks_page(self, page_url, communities):
        # For Stack Overflow Enterprise, the webhook_type is a column in the table
        # For Stack Overflow Business or Basic, the webhook type isn't in the table, so it's
        # inferred from the URL

        response = self.get_page_response(page_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        webhook_rows = soup.find_all('tr')

        if self.soe: # Stack Overflow Enterprise
            webhooks = self.process_webhooks(webhook_rows, communities)
        else: # Stack Overflow Business or Basic
            # type should be the the last part of the URL
            type = page_url.split('/')[-1]
            webhooks = self.process_webhooks(webhook_rows, communities, webhook_type=type)

        return webhooks


    def process_webhooks(self, webhook_rows, communities, webhook_type=None):

        # A webhook description has three parts: tags, activity type, and channel
        # Example scenarios to be accounted for:
            # All post activity to Private Channel > Private Channel
            # Any aws kubernetes github amazon-web-services (added via synonyms) kube 
                # (added via synonyms) posts to Engineering > Platform Engineering
            # Any admiral python aws amazon-web-services (added via synonyms) questions, 
                # answers to #admiral
            # Any questions, answers to #help-desk
            # Any machine-learning posts to #mits-demo
            # Any questions, answer in Customer Success to @Jonathan

        activity_types = ['edited questions', 'updated answers', 'accepted answers', 'questions', 
                        'answers', 'comments']
        webhooks = []
        for row in webhook_rows:
            if row.find('th'):
                continue
            columns = row.find_all('td')
            # Description always starts with "Any" unless it's "All post activity to..."
                # Which means all tags and activity types
            # In the description string, the space-delimited words after "Any" are tags
                # unless the notifications trigger for all tags, in which case it skips to activity type
                # some tags have suffixes like "(added via synonyms)"
            # The word "posts" is used to denote all activity types
            # Activity types are comma-delimited; everything else is space-delimited
            # The words after "to" are the channel; also, surrounded by <b></b> tags

            if self.soe: # For Stack Overflow Enterprise
                webhook_type = self.strip_html(columns[0].text)
                description = self.strip_html(columns[2].text).replace(
                    '(added via synonyms) ', '').replace(',', '')
                creator = columns[3].text
                creation_date = columns[4].text
            else: # For Stack Overflow Business or Basic
                description = self.strip_html(columns[0].text).replace(
                    '(added via synonyms) ', '').replace(',', '')
                creator = columns[1].text
                creation_date = columns[2].text
        
            if description.startswith('All post activity to'):
                tags = ['all']
                activities = activity_types
                channel = description.split('All post activity to ')[1]
            elif description.startswith('Any'):
                description = description.split('Any ')[1] # strip "Any"
                channel = description.split(' to ')[1]
                if 'posts to' in description: # i.e. all activity types
                    activities = activity_types
                    tags = description.split(' posts to ')[0].split(' ')
                elif ' in ' in description: # community is specified; use community tags
                    community_name = description.split(' in ')[1].split(' to')[0]
                    for community in communities:
                        if community['name'] == community_name:
                            break
                    tags = [tag['name'] for tag in community['tags']]
                    activities, description = self.process_webhook_activities(
                        description, activity_types)
                else: 
                    # Activity types are specified, but tags may or may not be
                    # Of the remaining words, find which are tags and activity types
                    # Activity types are comma-delimited
                    # Tags are space-delimited
                    # Tags are always first
                    # Tags are always followed by activity types
                    description = description.split(' to ')[0] # strip off channel
                    activities, description = self.process_webhook_activities(
                        description, activity_types)
                    if description:
                        tags = description.split(' ')
                    else:
                        tags = ['all']
            else: # likely a webhook that is disabled
                # If a webhook is disabled, it will usually start with the text:
                # "Notification failed, please re-authorize it."
                print(f"Unable to process webhook description: '{description}'")
                continue

            if channel == 'self':
                # For Microsoft Teams' webhooks, when a user selects private notifications,
                # the channel is reported as "self", which isn't very informative. To improve on 
                # that, append "self" with the user's name, who is the creator of the webhook.
                channel = f"{channel} ({creator})"

            webhook = {
                'type': webhook_type,
                'channel': channel,
                'tags': tags,
                'activities': activities,
                'creation_date': creation_date
            }

            webhooks.append(webhook)

        return webhooks


    def process_webhook_activities(self, description, activity_types):

        activities = []
        for activity_type in activity_types:
            if activity_type in description:
                activities.append(activity_type)
                description = description.replace(activity_type, '').strip()

        return activities, description
    
        
    def get_page_response(self, url):
        # Uses the Requests session to get page response

        response = self.s.get(url)
        if not response.status_code == 200:
            print(f'Error getting page {url}')
            print(f'Response code: {response.status_code}')
        
        return response
    

    def get_page_soup(self, url):
        # Uses the Requests session to get page response and returns a BeautifulSoup object

        response = self.get_page_response(url)
        try:
            return BeautifulSoup(response.text, 'html.parser')
        except AttributeError:
            return None
        

    def get_page_count(self, url):
        # Returns the number of pages that need to be scraped

        response = self.get_page_response(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        pagination = soup.find_all('a', {'class': 's-pagination--item js-pagination-item'})
        try:
            page_count = int(pagination[-2].text)
        except IndexError: # only one page
            page_count = 1

        return page_count


    def strip_html(self, text):
        # Remove HTML tags and newlines from text
        # There are various scenarios where these characters are present in the text when scraped
        return re.sub('<[^<]+?>', '', text).replace('\n', '').replace('\r', '').strip()
   