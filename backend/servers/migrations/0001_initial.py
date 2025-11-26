# Generated migration for servers app
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Server',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hostname', models.CharField(max_length=255)),
                ('ip_address', models.GenericIPAddressField()),
                ('os_name', models.CharField(max_length=100)),
                ('os_version', models.CharField(max_length=100)),
                ('total_ram', models.BigIntegerField(help_text='Total RAM in bytes')),
                ('total_disk', models.BigIntegerField(help_text='Total disk space in bytes')),
                ('cpu_count', models.IntegerField()),
                ('is_local', models.BooleanField(default=True, help_text='Whether this is the local server')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Server',
                'verbose_name_plural': 'Servers',
                'db_table': 'servers_server',
            },
        ),
    ]

