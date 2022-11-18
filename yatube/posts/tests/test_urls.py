from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from http import HTTPStatus

from posts.models import Group, Post


User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='ChosenOne')
        cls.authorized_client = Client()
        cls.templates_url_names_authorized = {
            '/posts/1/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        cls.templates_url_names_guest = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/ChosenOne/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
        }
        cls.templates_url_names_guest_redirect = {
            '/create/': '/auth/login/?next=/create/',
            '/posts/1/comment/': '/auth/login/?next=/posts/1/comment/',
            '/profile/ChosenOne/follow/': (
                '/auth/login/?next=/profile/ChosenOne/follow/'
            ),
            '/profile/ChosenOne/unfollow/': (
                '/auth/login/?next=/profile/ChosenOne/unfollow/'
            ),
        }

    def setUp(self):
        self.authorized_client.force_login(self.user)
        Post.objects.create(text='Тестовый текст', author=self.user)

    def test_post_edit_url(self):
        """Страница /posts/1/edit/ доступна только автору поста."""
        response_non_author = self.guest_client.get('/posts/1/edit/')
        self.assertEqual(response_non_author.status_code, HTTPStatus.FOUND)

    def test_unexisting_url(self):
        """Несуществующая страница возвращает ошибку 404
        и  использует кастомный шаблон
        """
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_url_uses_correct_template_guest(self):
        """posts: URL-адрес использует соответствующий
        шаблон и доступен любому пользователю.
        """
        for url, template in self.templates_url_names_guest.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_uses_correct_template_authorized(self):
        """posts: URL-адрес использует соответствующий
        шаблон и доступен авторизованному пользователю.
        """
        for url, template in self.templates_url_names_authorized.items():
            with self.subTest(url=url):
                response_auth = self.authorized_client.get(url)
                self.assertTemplateUsed(response_auth, template)
                self.assertEqual(response_auth.status_code, HTTPStatus.OK)

    def test_url_redirects_guest(self):
        """posts: URL-адрес перенаправит анонимного пользователя
        на страницу логина.
        """
        for url, redirect in self.templates_url_names_guest_redirect.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url, follow=True)
                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assertRedirects(response, redirect)
