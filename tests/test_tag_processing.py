import unittest
import sys
import types

for module_name, class_name in (
    ('so4t_web_client', 'WebClient'),
    ('so4t_api_v2', 'V2Client'),
    ('so4t_api_v3', 'V3Client'),
):
    module = types.ModuleType(module_name)
    setattr(module, class_name, object)
    sys.modules[module_name] = module

import so4t_tag_report


def make_tag(name):
    return {
        'name': name,
        'creationDate': '2026-01-01T00:00:00Z',
        'watcherCount': 0,
        'smes': {
            'users': [],
            'userGroups': [],
        },
    }


def make_owner(user_id=1):
    return {
        'user_id': user_id,
        'display_name': f'User {user_id}',
    }


class TagProcessingTests(unittest.TestCase):

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
