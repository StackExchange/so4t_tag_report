import unittest
import sys
import types
from unittest.mock import Mock, call, patch

try:
    import requests
except ModuleNotFoundError:
    requests = types.ModuleType('requests')
    requests.get = Mock()
    requests.exceptions = types.SimpleNamespace(SSLError=Exception)
    sys.modules['requests'] = requests

from so4t_api_v3 import V3Client


class V3ClientTests(unittest.TestCase):

    def make_client(self):
        client = V3Client.__new__(V3Client)
        client.api_url = 'https://example.com/api/v3'
        client.headers = {'Authorization': 'Bearer test-token'}
        client.proxies = {'https': None}
        client.ssl_verify = True
        return client

    @patch('so4t_api_v3.requests.get')
    def test_paginated_requests_use_v3_page_size_and_retrieve_every_page(self, get):
        first = Mock(status_code=200, headers={})
        first.json.return_value = {'items': [{'id': 1}], 'totalPages': 2}
        second = Mock(status_code=200, headers={})
        second.json.return_value = {'items': [{'id': 2}], 'totalPages': 2}
        responses = iter([first, second])
        params_seen = []

        def respond(*args, **kwargs):
            params_seen.append(kwargs['params'].copy())
            return next(responses)

        get.side_effect = respond

        articles = self.make_client().get_all_articles()

        self.assertEqual([{'id': 1}, {'id': 2}], articles)
        self.assertEqual(2, get.call_count)
        self.assertEqual(1, params_seen[0]['page'])
        self.assertEqual(2, params_seen[1]['page'])
        self.assertEqual(100, params_seen[0]['pageSize'])
        self.assertNotIn('pagesize', params_seen[0])

    def test_questions_include_all_answer_and_comment_resources(self):
        client = self.make_client()
        question = {'id': 10, 'answerCount': 1, 'commentCount': 1}
        answer = {'id': 20, 'commentCount': 1}

        def response(method, endpoint, params=None):
            return {
                '/questions': [question],
                '/questions/10/comments': [{'id': 30}],
                '/questions/10/answers': [answer],
                '/questions/10/answers/20/comments': [{'id': 40}],
            }[endpoint]

        with patch.object(client, 'send_api_call', side_effect=response) as send:
            questions = client.get_all_questions()

        self.assertEqual([{'id': 30}], questions[0]['comments'])
        self.assertEqual([{'id': 40}], questions[0]['answers'][0]['comments'])
        self.assertIn(call('get', '/questions/10/answers',
                           {'page': 1, 'pageSize': 100, 'sort': 'creation',
                            'order': 'asc'}), send.call_args_list)
        self.assertIn(call('get', '/questions/10/answers/20/comments'),
                      send.call_args_list)


if __name__ == '__main__':
    unittest.main()
