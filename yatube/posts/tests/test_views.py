import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for i in range(2):
            Group.objects.create(
                title='Тестовый заголовок',
                slug=f'test-slug{ i }',
                description='Тестовое описание',
            )
        cls.urls_with_pagination = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test-slug0'}),
            reverse('posts:profile', kwargs={'username': 'ChosenOne'}),
        )
        cls.templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': 'test-slug0'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': 'ChosenOne'}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': 1}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': 1}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        cls.user = User.objects.create_user(username='ChosenOne')
        cls.author = User.objects.create_user(username='Blogger')
        cls.follower = User.objects.create_user(username='Follower')
        cls.client = Client()
        cls.sub = Client()
        cls.group1 = Group.objects.get(slug='test-slug0')
        cls.group2 = Group.objects.get(slug='test-slug1')
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
        self.client.force_login(self.user)
        self.sub.force_login(self.follower)
        for _ in range(13):
            Post.objects.create(
                text='Тестовый текст',
                author=self.user,
                group=self.group1,
                image=self.uploaded,
            )
        cache.clear()

    def test_first_page_contains_ten_records(self):
        """Количество постов на первой странице равно 10."""
        for reverse_name in self.urls_with_pagination:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        """На второй странице должно быть три поста."""
        for reverse_name in self.urls_with_pagination:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 3)

    def test_second_group_is_empty(self):
        """Пост не попал в группу, для которой не был предназначен."""
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug1'})
        )
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_pages_uses_correct_template(self):
        """posts: URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in self.templates_page_names.items():
            with self.subTest(template=template):
                response = self.client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.client.get(reverse('posts:index'))
        post_text_0 = response.context['page_obj'][0].text
        post_image_0 = response.context['page_obj'][0].image
        image_ext = post_image_0.name.split('.')[1]
        self.assertEqual(post_text_0, 'Тестовый текст')
        self.assertEqual(image_ext, 'gif')

    def test_index_page_cache(self):
        """Шаблон index использует кеширование."""
        Post.objects.create(
            text='Temp post',
            author=self.user,
        )
        response = self.client.get(reverse('posts:index'))
        Post.objects.get(text='Temp post').delete()
        self.assertIn(b'Temp post', response.content)
        cache.clear()
        response = self.client.get(reverse('posts:index'))
        self.assertNotIn(b'Temp post', response.content)

    def test_follow_url(self):
        """Проверка подписки и отписки."""
        Follow.objects.create(user=self.follower, author=self.author)
        Post.objects.create(
            text='Awesome post',
            author=self.author,
        )
        response_follower = self.sub.get(reverse('posts:follow_index'))
        response_non_follower = self.client.get(reverse('posts:follow_index'))
        post_text_follower = response_follower.context['page_obj'][0].text
        post_non_follower = response_non_follower.context['page_obj']
        self.assertEqual(post_text_follower, 'Awesome post')
        self.assertFalse(post_non_follower)
        Follow.objects.get(user=self.follower, author=self.author).delete()
        response_unfollower = self.sub.get(reverse('posts:follow_index'))
        post_unfollower = response_unfollower.context['page_obj']
        self.assertFalse(post_unfollower)
        Post.objects.get(text='Awesome post').delete()

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug0'})
        )
        post_text_0 = response.context['page_obj'][0].text
        post_group_slug = response.context['group'].slug
        post_image_0 = response.context['page_obj'][0].image
        image_ext = post_image_0.name.split('.')[1]
        self.assertEqual(post_text_0, 'Тестовый текст')
        self.assertEqual(post_group_slug, 'test-slug0')
        self.assertEqual(image_ext, 'gif')

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': 'ChosenOne'})
        )
        post_text_0 = response.context['page_obj'][0].text
        post_author = response.context['author'].username
        total_author_posts = response.context['total_posts']
        post_image_0 = response.context['page_obj'][0].image
        image_ext = post_image_0.name.split('.')[1]
        self.assertEqual(post_text_0, 'Тестовый текст')
        self.assertEqual(post_author, 'ChosenOne')
        self.assertEqual(total_author_posts, 13)
        self.assertEqual(image_ext, 'gif')

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        Comment.objects.create(
            post=Post.objects.get(pk=1),
            author=self.user,
            text='Тестовый комментарий',
        )
        response = self.client.get(
            reverse('posts:post_detail', kwargs={'post_id': 1})
        )
        post_text = response.context['post'].text
        total_author_posts = response.context['total_posts']
        post_image_0 = response.context['post'].image
        image_ext = post_image_0.name.split('.')[1]
        comment = response.context['comments'][0].text
        self.assertEqual(post_text, 'Тестовый текст')
        self.assertEqual(total_author_posts, 13)
        self.assertEqual(image_ext, 'gif')
        self.assertEqual(comment, 'Тестовый комментарий')

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.client.get(
            reverse('posts:post_edit', kwargs={'post_id': 1})
        )
        post_text = response.context['post'].text
        post_is_edit = response.context['is_edit']
        post_groups = response.context['groups']
        group_list = []
        for group in post_groups:
            group_list.append(group.slug)
        self.assertEqual(post_text, 'Тестовый текст')
        self.assertTrue(post_is_edit)
        self.assertEqual(group_list, ['test-slug0', 'test-slug1'])

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)
