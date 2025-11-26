"""
Tests for accounts app.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import SSHProfile

User = get_user_model()


class UserModelTest(TestCase):
    """Test User model."""
    
    def test_create_user(self):
        """Test user creation."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)


class SSHProfileTest(TestCase):
    """Test SSHProfile model."""
    
    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
    
    def test_create_ssh_profile(self):
        """Test SSH profile creation."""
        profile = SSHProfile.objects.create(
            user=self.user,
            ssh_username='root',
            auth_type=SSHProfile.AUTH_TYPE_PASSWORD
        )
        profile.set_password('testpassword')
        profile.save()
        
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.ssh_username, 'root')
        self.assertIsNotNone(profile.ssh_password)
        
        # Test password retrieval
        retrieved_password = profile.get_password()
        self.assertEqual(retrieved_password, 'testpassword')

