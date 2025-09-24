# Standard Python libraries
import time
import json

# Third-party libraries
import requests

# Local libraries
from so4t_request_validate import *


class V2Client(object):
    def __init__(self, url, key=None, token=None, proxy=None):

        print("Initializing API v2.3 client...")

        if not url: # check if URL is provided; if not, exit
            print("Missing required argument. Please provide a URL.")
            raise SystemExit
        
        # Establish the class variables based on which product is being used
        if "stackoverflowteams.com" in url: # Stack Overflow Business or Basic
            self.soe = False
            self.api_url = "https://api.stackoverflowteams.com/2.3"
            self.team_slug = url.split("https://stackoverflowteams.com/c/")[1]
            self.token = token
            self.api_key = key
            self.headers = {
            # Updated User-Agent
            'X-API-Access-Token': self.token,
            'User-Agent': 'so4t_tag_report/1.0 (http://your-app-url.com; your-contact@email.com)'
            } 
            if not self.token:
                print("Missing required argument. Please provide an API token.")
                raise SystemExit
        else: # Stack Overflow Enterprise
            self.soe = True
            self.api_url = url + "/api/2.3"
            self.team_slug = None
            self.token = token
            self.api_key = key
            self.headers = {
            #Updated User-Agent
            'X-API-Key': self.api_key,
            'User-Agent': 'so4t_tag_report/1.0 (http://your-app-url.com; your-contact@email.com)'
            } 
            if not self.api_key:
                print("Missing required argument. Please provide an API key.")
                raise SystemExit
            
        self.proxies = {'https': proxy} if proxy else {'https': None}

        # Test the API connection and set the SSL verification variable
        self.ssl_verify = self.test_connection()


    def test_connection(self):

        url = self.api_url + "/tags"
        ssl_verify = True

        params = {}
        if self.soe:
            headers = {'X-API-Key': self.api_key}
        else:
            headers = {'X-API-Access-Token': self.token}
            params['team'] = self.team_slug

        print("Testing API 2.3 connection...")
        try:
            response = requests.get(url, params=params, headers=headers, 
                                    proxies=self.proxies)
        except requests.exceptions.SSLError:
            print("SSL error. Trying again without SSL verification...")
            response = requests.get(url, params=params, headers=headers, 
                                    verify=False, proxies=self.proxies)
            ssl_verify = False
        
        if response.status_code == 200:
            print("API connection successful")
            return ssl_verify
        else:
            print("Unable to connect to API. Please check your URL and API key/token.")
            print(f"Status code: {response.status_code}")
            print(f"Response from server: {response.text}")
            raise SystemExit
        

    def create_filter(self, filter_attributes='', base='default'):
        # filter_attributes should be a list variable containing strings of the attributes
        # base can be 'default', 'withbody', 'none', or 'total'

        # Filter documentation: https://api.stackexchange.com/docs/filters
        # Documentation for API endpoint: https://api.stackexchange.com/docs/create-filter
        endpoint = "/filters/create"
        endpoint_url = self.api_url + endpoint

        params = {
            'base': base,
            'unsafe': False
        }

        if filter_attributes:
            # The API endpoint requires a semi-colon separated string of attributes
            # This converts the list of attributes into a string
            params['include'] = ';'.join(filter_attributes)

        response = self.get_items(endpoint_url, params)
        filter_string = response[0]['filter']
        print(f"Filter created: {filter_string}")

        return filter_string


    def get_all_questions(self, filter_string=''):

        # API endpoint documentation: https://api.stackexchange.com/docs/questions
        endpoint = "/questions"
        endpoint_url = self.api_url + endpoint

        params = {
            'page': 1,
            'pagesize': 100,
        }
        if filter_string:
            params['filter'] = filter_string
    
        return self.get_items(endpoint_url, params)


    def get_all_articles(self, filter_string=''):

        # API endpoint documentation: https://api.stackexchange.com/docs/articles
        endpoint = "/articles"
        endpoint_url = self.api_url + endpoint

        params = {
            'page': 1,
            'pagesize': 100,
        }
        if filter_string:
            params['filter'] = filter_string

        return self.get_items(endpoint_url, params)
    

    def get_all_users(self, filter_string=''):
        
        # API endpoint documentation: https://api.stackexchange.com/docs/users
        endpoint = "/users"
        endpoint_url = self.api_url + endpoint

        params = {
            'page': 1,
            'pagesize': 100,
        }
        if filter_string:
            params['filter'] = filter_string

        return self.get_items(endpoint_url, params)
    

    def get_items(self, endpoint_url, params):
        # SO Business and Basic require a team slug parameter
        if not self.soe:
            params['team'] = self.team_slug

        items = []
        while True: # Keep performing API calls until all items are received
            if params.get('page'):
                print(f"Getting page {params['page']} from {endpoint_url}")
            else:
                print(f"Getting data from {endpoint_url}")
            
            try:
                global timeout
                response = requests.get(endpoint_url, headers=self.headers, params=params, 
                                    verify=self.ssl_verify, proxies=self.proxies, timeout=timeout)
            except Exception as ex:
                handle_except(ex)
                continue
            
            if response.status_code != 200:
            # Many API call failures result in an HTTP 400 status code (Bad Request)
            # To understand the reason for the 400 error, specific API error codes can be 
            # found here: https://api.stackoverflowteams.com/docs/error-handling
                print(f"/{endpoint_url} API call failed with status code: {response.status_code}.")
                print(response.text)
                print(f"Failed request URL and params: {response.request.url}")
                raise SystemExit
            
            try:
                json_data = response.json()
            except json.decoder.JSONDecodeError: # some API calls do not return JSON data
                print(f"API request successfully sent to {endpoint_url}")
                break
        
            items += json_data.get('items')

            # If the endpoint gets overloaded, it will send a backoff request in the response
            # Failure to backoff will result in a 502 error (throttle_violation)
            # Rate limiting documentation: https://api.stackexchange.com/docs/throttle
            if json_data.get('backoff'):
                backoff_time = json_data.get('backoff') + 1
                print(f"API backoff request received. Waiting {backoff_time} seconds...")
                time.sleep(backoff_time)
        
            if not json_data.get('has_more'):
                break

            params['page'] += 1
            global retry_count
            retry_count = 0

        return items
  