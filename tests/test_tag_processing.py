import datetime
import unittest
import sys
import types
from unittest.mock import patch

for module_name, class_name in (
    ('so4t_web_client', 'WebClient'),
    ('so4t_api_v2', 'V2Client'),
    ('so4t_api_v3', 'V3Client'),
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


def make_owner(user_id=1):
    return {
        'user_id': user_id,
        'display_name': f'User {user_id}',
    }


class TagProcessingTests(unittest.TestCase):

    def test_add_last_used_to_tags_derives_dates_from_each_content_type(self):
        tags = [make_tag('question-tag'), make_tag('article-tag')]
        questions = [{'tags': ['question-tag'],
                      'creation_date': utc_timestamp(2025, 1, 2)}]
        articles = [{'tags': ['article-tag'],
                     'creation_date': utc_timestamp(2025, 2, 3)}]

        result = so4t_tag_report.add_last_used_to_tags(tags, questions, articles)

        self.assertIs(tags, result)
        self.assertEqual('2025-01-02', tags[0]['lastUsed'])
        self.assertEqual('2025-02-03', tags[1]['lastUsed'])

    def test_add_last_used_to_tags_uses_latest_valid_timestamp_and_ignores_invalid_content(self):
        tags = [make_tag('used-tag'), make_tag('unused-tag', tag_id=2)]
        questions = [
            {'tags': ['used-tag'], 'creation_date': utc_timestamp(2025, 1, 2)},
            {'tags': ['used-tag'], 'creation_date': 'not-a-timestamp'},
            {'tags': ['used-tag'], 'creation_date': True},
            {'tags': ['used-tag']},
            {'tags': ['unknown-tag'], 'creation_date': utc_timestamp(2026, 1, 1)},
        ]
        articles = [{'tags': ['used-tag'],
                     'creation_date': utc_timestamp(2025, 3, 4)}]

        so4t_tag_report.add_last_used_to_tags(tags, questions, articles)

        self.assertEqual('2025-03-04', tags[0]['lastUsed'])
        self.assertEqual('', tags[1]['lastUsed'])

    @patch('so4t_tag_report.time.time', return_value=utc_timestamp(2026, 1, 10))
    def test_filtering_content_does_not_erase_annotated_last_used(self, mock_time):
        tags = [make_tag('old-tag')]
        api_data = {
            'tags': tags,
            'questions': [{'tags': ['old-tag'],
                           'creation_date': utc_timestamp(2025, 1, 2)}],
            'articles': [],
        }

        so4t_tag_report.add_last_used_to_tags(
            api_data['tags'], api_data['questions'], api_data['articles'])
        filtered_data = so4t_tag_report.filter_api_data_by_date(api_data, days=30)

        self.assertEqual([], filtered_data['questions'])
        self.assertEqual('2025-01-02', filtered_data['tags'][0]['lastUsed'])
        mock_time.assert_called_once_with()

    def test_process_questions_skips_unknown_tags(self):
        tags = so4t_tag_report.process_tags([make_tag('known-tag')])
        questions = [{
            'tags': ['missing-tag'],
            'owner': make_owner(),
            'view_count': 10,
            'up_vote_count': 1,
            'down_vote_count': 0,
            'creation_date': 1000,
            'link': 'https://example.com/q/1',
        }]

        processed_tags = so4t_tag_report.process_questions(tags, questions)

        self.assertEqual(0, processed_tags[0]['metrics']['question_count'])
        self.assertEqual(0, processed_tags[0]['metrics']['total_page_views'])

    def test_process_articles_skips_unknown_tags(self):
        tags = so4t_tag_report.process_tags([make_tag('known-tag')])
        articles = [{
            'tags': ['missing-tag'],
            'owner': make_owner(),
            'view_count': 10,
            'score': 1,
            'comment_count': 1,
        }]

        processed_tags = so4t_tag_report.process_articles(tags, articles)

        self.assertEqual(0, processed_tags[0]['metrics']['article_count'])
        self.assertEqual(0, processed_tags[0]['metrics']['total_page_views'])


if __name__ == '__main__':
    unittest.main()
