# Generated by Django 4.2 on 2023-04-27 07:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver_flutterwave', '0009_card_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='fingerprint',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
