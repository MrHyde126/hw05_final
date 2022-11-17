from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from http import HTTPStatus

User = get_user_model()


class UserURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='ChosenOne')
        cls.authorized_client = Client()
        cls.templates_url_names_authorized = {
            '/auth/password_change/done/': 'users/password_change_done.html',
            '/auth/password_change/': 'users/password_change_form.html',
        }
        cls.templates_url_names_guest = {
            '/auth/logout/': 'users/logged_out.html',
            '/auth/login/': 'users/login.html',
            '/auth/reset/done/': 'users/password_reset_complete.html',
            '/auth/password_reset/done/': 'users/password_reset_done.html',
            '/auth/password_reset/': 'users/password_reset_form.html',
            '/auth/signup/': 'users/signup.html',
        }

    def setUp(self):
        self.authorized_client.force_login(self.user)

    def test_url_uses_correct_template_guest(self):
        """users: URL-адрес использует соответствующий
        шаблон и доступен любому пользователю.
        """
        for url, template in self.templates_url_names_guest.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_uses_correct_template_authorized(self):
        """users: URL-адрес использует соответствующий
        шаблон и доступен авторизованному пользователю.
        """
        for url, template in self.templates_url_names_authorized.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_blocked_for_not_auth_users(self):
        """Страницы /auth/password_change/done/ и /auth/password_change/
        недоступны анонимному пользователю.
        """
        for url in self.templates_url_names_authorized.keys():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)
