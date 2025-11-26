# Generated migration for websites app
from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Website',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(max_length=255, unique=True, validators=[django.core.validators.MinLengthValidator(3)])),
                ('root_path', models.CharField(help_text='Document root path', max_length=500)),
                ('type', models.CharField(choices=[('php', 'PHP Application'), ('wordpress', 'WordPress Site')], default='php', max_length=20)),
                ('web_server', models.CharField(choices=[('nginx', 'Nginx'), ('apache', 'Apache')], default='nginx', max_length=20)),
                ('php_version', models.CharField(default='8.1', help_text='PHP version (e.g., 8.1, 8.2)', max_length=10)),
                ('status', models.CharField(choices=[('active', 'Active'), ('disabled', 'Disabled')], default='active', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Website',
                'verbose_name_plural': 'Websites',
                'db_table': 'websites_website',
            },
        ),
        migrations.CreateModel(
            name='DatabaseCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('db_name', models.CharField(max_length=100)),
                ('db_user', models.CharField(max_length=100)),
                ('db_password', models.CharField(max_length=255)),
                ('db_host', models.CharField(default='localhost', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('website', models.OneToOneField(on_delete=models.CASCADE, related_name='database', to='websites.website')),
            ],
            options={
                'verbose_name': 'Database Credential',
                'verbose_name_plural': 'Database Credentials',
                'db_table': 'websites_databasecredential',
            },
        ),
    ]

