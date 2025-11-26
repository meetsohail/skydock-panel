# Generated migration for websites app - add user field and WordPress fields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('websites', '0001_initial'),
    ]

    operations = [
        # Remove unique constraint on domain first
        migrations.AlterField(
            model_name='website',
            name='domain',
            field=models.CharField(max_length=255, validators=[django.core.validators.MinLengthValidator(3)]),
        ),
        # Add user field (nullable first for existing records)
        migrations.AddField(
            model_name='website',
            name='user',
            field=models.ForeignKey(
                help_text='Owner of this website',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='websites',
                to=settings.AUTH_USER_MODEL,
                null=True,
                blank=True
            ),
        ),
        # Add WordPress fields
        migrations.AddField(
            model_name='website',
            name='wp_admin_email',
            field=models.EmailField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='website',
            name='wp_admin_user',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='website',
            name='wp_admin_password',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        # Add unique_together constraint for user + domain
        migrations.AlterUniqueTogether(
            name='website',
            unique_together={('user', 'domain')},
        ),
    ]

