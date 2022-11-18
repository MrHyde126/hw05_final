import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Post


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='ChosenOne')
        cls.authorized_client = Client()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif', content=cls.small_gif, content_type='image/gif'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client.force_login(self.user)
        Post.objects.create(
            text='Тестовый пост',
            author=self.user,
        )

    def test_create_post_authorized(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Matrix has you',
            'author': 'ChosenOne',
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        form_fields = {
            'text': models.fields.TextField,
            'pub_date': models.fields.DateTimeField,
            'author': models.fields.related.ForeignKey,
            'group': models.fields.related.ForeignKey,
            'image': models.fields.files.ImageField,
        }
        post = Post.objects.get(text='Matrix has you')
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = post._meta.get_field(value)
                self.assertIsInstance(form_field, expected)
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': 'ChosenOne'}),
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Matrix has you',
                author=self.user,
            ).exists()
        )

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        posts_count = Post.objects.count()
        original_post = Post.objects.get(pk=1)
        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': 1}),
            data={'text': 'Новый текст поста'},
        )
        self.assertTrue(
            Post.objects.filter(
                pk=1,
                text='Новый текст поста',
            ).exists()
        )
        self.assertEqual(Post.objects.count(), posts_count)
        edited_post = Post.objects.get(pk=1)
        self.assertEqual('Новый текст поста', edited_post.text)
        self.assertEqual(original_post.author, edited_post.author)
        self.assertEqual(original_post.group, edited_post.group)

    def test_create_post_guest(self):
        """Форма перенаправит анонимного пользователя
        на страницу логина.
        """
        posts_count = Post.objects.count()
        form_data = {'text': 'Matrix has you', 'author': self.guest_client}
        response = self.guest_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/create/')
        self.assertEqual(Post.objects.count(), posts_count)
