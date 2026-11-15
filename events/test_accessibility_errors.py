from html.parser import HTMLParser

from django.contrib.auth.models import User
from django.test import TestCase

from .models import UserProfile


class FormMarkup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids = set()
        self.invalid_descriptions = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if attrs.get('aria-invalid') == 'true':
            self.invalid_descriptions.append(attrs.get('aria-describedby', '').split())


class AccessibleErrorTests(TestCase):
    def assert_error_descriptions_resolve(self, response):
        self.assertEqual(response.status_code, 200)
        markup = FormMarkup(response.content.decode())
        self.assertIn('error-summary', markup.ids)
        self.assertTrue(markup.invalid_descriptions)
        for descriptions in markup.invalid_descriptions:
            self.assertTrue(descriptions)
            self.assertTrue(set(descriptions) <= markup.ids)

    def test_registration_errors_have_resolvable_descriptions(self):
        response = self.client.post('/accounts/register/', {})
        self.assert_error_descriptions_resolve(response)
        self.assertFalse(User.objects.exists())

    def test_organizer_errors_have_resolvable_descriptions(self):
        user = User.objects.create_user(username='organizer')
        UserProfile.objects.update_or_create(
            user=user, defaults={'role': 'organizer', 'email_verified': True}
        )
        self.client.force_login(user)
        self.assert_error_descriptions_resolve(self.client.post('/events/create/', {}))
