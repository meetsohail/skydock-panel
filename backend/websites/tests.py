"""
Tests for websites app.
"""
from django.test import TestCase
from .models import Website, DatabaseCredential


class WebsiteModelTest(TestCase):
    """Test Website model."""
    
    def test_create_php_website(self):
        """Test PHP website creation."""
        website = Website.objects.create(
            domain='example.com',
            root_path='/var/www/example.com',
            type=Website.TYPE_PHP,
            web_server=Website.WEB_SERVER_NGINX,
            php_version='8.1',
            status=Website.STATUS_ACTIVE
        )
        self.assertEqual(website.domain, 'example.com')
        self.assertEqual(website.type, Website.TYPE_PHP)
        self.assertEqual(website.status, Website.STATUS_ACTIVE)
    
    def test_create_wordpress_website(self):
        """Test WordPress website creation."""
        website = Website.objects.create(
            domain='wp.example.com',
            root_path='/var/www/wp.example.com',
            type=Website.TYPE_WORDPRESS,
            web_server=Website.WEB_SERVER_NGINX,
            php_version='8.1',
            status=Website.STATUS_ACTIVE
        )
        
        # Create database credential
        db_cred = DatabaseCredential.objects.create(
            website=website,
            db_name='wp_example',
            db_user='wp_user',
            db_password='wp_pass123',
            db_host='localhost'
        )
        
        self.assertEqual(website.type, Website.TYPE_WORDPRESS)
        self.assertEqual(db_cred.website, website)
        self.assertEqual(db_cred.db_name, 'wp_example')

