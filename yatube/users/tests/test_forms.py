from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


User = get_user_model()


class UserFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client()

    def test_new_user_signup(self):
        """Валидная форма создает нового пользователя."""
        form_data = {
            'first_name': 'Thomas',
            'last_name': 'Anderson',
            'username': 'Neo',
            'email': 'neo@matrix.com',
            'password1': 'q1w2e3hg',
            'password2': 'q1w2e3hg',
        }
        response = self.client.post(
            reverse('users:signup'), data=form_data, follow=True
        )
        self.assertRedirects(response, reverse('posts:index'))
        self.assertTrue(User.objects.filter(username='Neo').exists())
