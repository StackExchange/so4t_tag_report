import datetime
import unittest
import sys
import types
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import requests
except ModuleNotFoundError:
    requests = types.ModuleType('requests')
    requests.get = Mock()
    requests.exceptions = types.SimpleNamespace(SSLError=Exception)
    sys.modules['requests'] = requests

for module_name, class_name in (
    ('so4t_web_client', 'WebClient'),
):
    module = types.ModuleType(module_name)
    setattr(module, class_name, object)
    sys.modules[module_name] = module

import so4t_tag_report


def make_tag(name, tag_id=1, last_used=''):
    return {
        'id': tag_id,
        'name': name,
        'lastUsed': last_used,
        'creationDate': '2026-01-01T00:00:00Z',
        'watcherCount': 0,
        'smes': {
            'users': [],
            'userGroups': [],
        },
    }


def utc_timestamp(year, month, day):
    return int(datetime.datetime(
    year, month, day, tzinfo=datetime.timezone.utc).timestamp())


def iso_date(year, month, day):
    return f'{year:04d}-{month:02d}-{day:02d}T00:00:00Z'


def named_tag(name):
    return {'name': name}


def make_owner(user_id=1):
    return {
        'id': user_id,
        'name': f'User {user_id}',
    }


class TagProcessingTests(unittest.TestCase):

    def test_add_last_used_to_tags_derives_dates_from_each_content_type(self):
        tags = [make_tag('question-tag'), make_tag('article-tag')]
        questions = [{'tags': [named_tag('question-tag')],
                      'creationDate': iso_date(2025, 1, 2)}]
        articles = [{'tags': [named_tag('article-tag')],
                     'creationDate': iso_date(2025, 2, 3)}]

        result = so4t_tag_report.add_last_used_to_tags(tags, questions, articles)

        self.assertIs(tags, result)
        self.assertEqual('2025-01-02', tags[0]['lastUsed'])
        self.assertEqual('2025-02-03', tags[1]['lastUsed'])

    def test_add_last_used_to_tags_uses_latest_valid_timestamp_and_ignores_invalid_content(self):
        tags = [
            make_tag('used-tag'),
            make_tag('unused-tag', tag_id=2),
            make_tag('boolean-only-tag', tag_id=3),
        ]
        questions = [
            {'tags': [named_tag('used-tag')], 'creationDate': iso_date(2025, 1, 2)},
            {'tags': [named_tag('used-tag')], 'creationDate': 'not-a-timestamp'},
            {'tags': [named_tag('used-tag')]},
            {'tags': [named_tag('boolean-only-tag')], 'creationDate': True},
            {'tags': [named_tag('unknown-tag')], 'creationDate': iso_date(2026, 1, 1)},
        ]
        articles = [{'tags': [named_tag('used-tag')],
                     'creationDate': iso_date(2025, 3, 4)}]

        so4t_tag_report.add_last_used_to_tags(tags, questions, articles)

        self.assertEqual('2025-03-04', tags[0]['lastUsed'])
        self.assertEqual('', tags[1]['lastUsed'])
        self.assertEqual('', tags[2]['lastUsed'])

    def test_add_last_used_ignores_deleted_content(self):
        tags = [make_tag('python')]
        questions = [
            {'tags': [named_tag('python')], 'creationDate': iso_date(2025, 1, 2)},
            {'tags': [named_tag('python')], 'creationDate': iso_date(2026, 1, 2),
             'isDeleted': True},
        ]

        so4t_tag_report.add_last_used_to_tags(tags, questions, [])

        self.assertEqual('2025-01-02', tags[0]['lastUsed'])

    @patch('so4t_tag_report.time.time', return_value=utc_timestamp(2026, 1, 10))
    @patch('so4t_tag_report.export_to_json')
    def test_filtering_content_does_not_erase_annotated_last_used(
            self, mock_export_to_json, mock_time):
        tags = [make_tag('old-tag')]
        api_data = {
            'tags': tags,
            'questions': [{'tags': [named_tag('old-tag')],
                           'creationDate': iso_date(2025, 1, 2)}],
            'articles': [],
        }

        so4t_tag_report.add_last_used_to_tags(
            api_data['tags'], api_data['questions'], api_data['articles'])
        filtered_data = so4t_tag_report.filter_api_data_by_date(api_data, days=30)

        self.assertEqual([], filtered_data['questions'])
        self.assertEqual('2025-01-02', filtered_data['tags'][0]['lastUsed'])
        mock_time.assert_called_once_with()
        mock_export_to_json.assert_called_once_with('filtered_api_data', api_data)

    def test_process_questions_skips_unknown_tags(self):
        tags = so4t_tag_report.process_tags([make_tag('known-tag')])
        questions = [{
            'tags': [named_tag('missing-tag')],
            'owner': make_owner(),
            'viewCount': 10,
            'score': 1,
            'creationDate': iso_date(2026, 1, 1),
            'webUrl': 'https://example.com/q/1',
        }]

        processed_tags = so4t_tag_report.process_questions(tags, questions)

        self.assertEqual(0, processed_tags[0]['metrics']['question_count'])
        self.assertEqual(0, processed_tags[0]['metrics']['total_page_views'])

    def test_process_articles_skips_unknown_tags(self):
        tags = so4t_tag_report.process_tags([make_tag('known-tag')])
        articles = [{
            'tags': [named_tag('missing-tag')],
            'owner': make_owner(),
            'viewCount': 10,
            'score': 1,
            'commentCount': 1,
        }]

        processed_tags = so4t_tag_report.process_articles(tags, articles)

        self.assertEqual(0, processed_tags[0]['metrics']['article_count'])
        self.assertEqual(0, processed_tags[0]['metrics']['total_page_views'])

    def test_process_tags_includes_tag_id_and_last_used_metrics(self):
        tags = so4t_tag_report.process_tags([
            make_tag('known-tag', tag_id=42, last_used='2026-07-08')])

        metrics = tags[0]['metrics']
        self.assertEqual(42, metrics['tag_id'])
        self.assertEqual('2026-07-08', metrics['last_used'])

    def test_v3_content_produces_scores_contributors_and_response_times(self):
        tag = make_tag('python')
        tag['smes']['users'] = [make_owner(2)]
        question = {
            'id': 10, 'tags': [named_tag('python')], 'owner': make_owner(1),
            'creationDate': '2026-01-01T00:00:00Z', 'webUrl': 'https://example.com/q/10',
            'viewCount': 10, 'score': 2,
            'comments': [
                {'ownerUserId': 4, 'ownerDisplayName': 'User 4',
                 'creationDate': '2026-01-01T03:00:00Z'},
                {'ownerUserId': 1, 'ownerDisplayName': 'User 1',
                 'creationDate': '2026-01-01T01:00:00Z'},
            ],
            'answers': [{
                'owner': make_owner(2), 'creationDate': '2026-01-01T02:00:00Z',
                'score': 3, 'isAccepted': True, 'comments': [],
            }],
        }
        article = {
            'tags': [named_tag('python')], 'owner': make_owner(3),
            'viewCount': 5, 'score': 1, 'commentCount': 2,
        }
        result = so4t_tag_report.process_api_data({
            'tags': [tag], 'questions': [question], 'articles': [article],
            'webhooks': None, 'communities': None,
        })[0]
        metrics = result['metrics']
        self.assertEqual(15, metrics['total_page_views'])
        self.assertEqual(2, metrics['question_score'])
        self.assertEqual(3, metrics['answer_score'])
        self.assertEqual(1, metrics['article_score'])
        self.assertEqual(1, metrics['sme_answers'])
        self.assertEqual(4, metrics['total_unique_contributors'])
        self.assertEqual(2, metrics['median_time_to_first_response_hours'])
        self.assertEqual(2, metrics['median_time_to_first_answer_hours'])
        self.assertNotIn('question_upvotes', metrics)
        self.assertNotIn('answer_downvotes', metrics)

    def test_external_comment_counts_as_response_to_self_answered_question(self):
        tag = so4t_tag_report.process_tags([make_tag('python')])
        question = {
            'tags': [named_tag('python')], 'owner': make_owner(1),
            'creationDate': '2026-01-01T00:00:00Z', 'webUrl': 'https://example.com/q/1',
            'viewCount': 1, 'score': 0,
            'answers': [{'owner': make_owner(1), 'isAccepted': False,
                         'creationDate': '2026-01-01T01:00:00Z', 'score': 0}],
            'comments': [{'ownerUserId': 2, 'ownerDisplayName': 'User 2',
                          'creationDate': '2026-01-01T03:00:00Z'}],
        }
        result = so4t_tag_report.process_questions(tag, [question])[0]
        self.assertEqual(1, len(result['self_answered_questions']))
        self.assertEqual([{'https://example.com/q/1': 3}], result['response_times'])

    def test_external_answer_after_self_answer_counts_as_first_answer(self):
        tag = so4t_tag_report.process_tags([make_tag('python')])
        question = {
            'tags': [named_tag('python')], 'owner': make_owner(1),
            'creationDate': '2026-01-01T00:00:00Z', 'webUrl': 'https://example.com/q/1',
            'viewCount': 1, 'score': 0, 'comments': [],
            'answers': [
                {'owner': make_owner(2), 'isAccepted': False,
                 'creationDate': '2026-01-01T04:00:00Z', 'score': 0},
                {'owner': make_owner(1), 'isAccepted': False,
                 'creationDate': '2026-01-01T01:00:00Z', 'score': 0},
            ],
        }

        result = so4t_tag_report.process_questions(tag, [question])[0]

        self.assertEqual(1, len(result['self_answered_questions']))
        self.assertEqual([{'https://example.com/q/1': 4}], result['answer_times'])

    @patch('so4t_tag_report.export_to_json')
    @patch('so4t_tag_report.V3Client')
    def test_collector_uses_v3_for_all_api_content(self, client_class, export):
        client = client_class.return_value
        client.get_all_questions.return_value = []
        client.get_all_articles.return_value = []
        client.get_all_tags.return_value = []
        args = SimpleNamespace(web_client=False, url='https://example.com',
                               token='token', proxy=None)

        data = so4t_tag_report.data_collector(args)

        self.assertEqual({'questions': [], 'articles': [], 'tags': [],
                          'webhooks': None, 'communities': None}, data)
        client_class.assert_called_once_with(args.url, args.token, None)
        client.get_all_questions.assert_called_once_with()
        client.get_all_articles.assert_called_once_with()
        client.get_all_tags.assert_called_once_with()

    @patch('so4t_tag_report.create_tag_report')
    @patch('so4t_tag_report.filter_api_data_by_date')
    @patch('so4t_tag_report.data_collector')
    @patch('so4t_tag_report.get_args')
    def test_main_adds_last_used_before_days_filtering(
            self, mock_get_args, mock_data_collector, mock_filter, mock_create_report):
        args = SimpleNamespace(no_api=False, days=30)
        api_data = {
            'tags': [make_tag('known-tag', tag_id=42)],
            'questions': [{
                'tags': [named_tag('known-tag')],
                'creationDate': iso_date(2020, 1, 2),
            }],
            'articles': [],
        }
        mock_get_args.return_value = args
        mock_data_collector.return_value = api_data

        def assert_last_used_before_filtering(data, days):
            self.assertEqual('2020-01-02', data['tags'][0]['lastUsed'])
            return data

        mock_filter.side_effect = assert_last_used_before_filtering

        so4t_tag_report.main()

        mock_filter.assert_called_once_with(api_data, 30)
        mock_create_report.assert_called_once_with(api_data, 30)

    @patch('so4t_tag_report.create_tag_report')
    @patch('so4t_tag_report.filter_api_data_by_date')
    @patch('so4t_tag_report.read_json')
    @patch('so4t_tag_report.get_args')
    def test_main_no_api_adds_last_used_before_days_filtering(
            self, mock_get_args, mock_read_json, mock_filter, mock_create_report):
        args = SimpleNamespace(no_api=True, days=30)
        api_data = {
            'tags': [make_tag('known-tag', tag_id=42)],
            'questions': [{
                'tags': [named_tag('known-tag')],
                'creationDate': iso_date(2020, 1, 2),
            }],
            'articles': [],
            'webhooks': [],
            'communities': [],
        }
        filtered_data = {'filtered': True}
        mock_get_args.return_value = args
        mock_read_json.side_effect = lambda filename: {
            'questions.json': api_data['questions'],
            'articles.json': api_data['articles'],
            'tags.json': api_data['tags'],
            'webhooks.json': api_data['webhooks'],
            'communities.json': api_data['communities'],
        }[filename]

        def assert_last_used_before_filtering(data, days):
            self.assertEqual('2020-01-02', data['tags'][0]['lastUsed'])
            return filtered_data

        mock_filter.side_effect = assert_last_used_before_filtering

        so4t_tag_report.main()

        mock_filter.assert_called_once_with(api_data, 30)
        mock_create_report.assert_called_once_with(filtered_data, 30)


if __name__ == '__main__':
    unittest.main()
