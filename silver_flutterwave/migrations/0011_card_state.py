# Generated by Django 4.2 on 2023-07-10 12:19

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("silver_flutterwave", "0010_card_fingerprint"),
    ]

    operations = [
        migrations.AddField(
            model_name="card",
            name="state",
            field=models.CharField(
                blank=True,
                choices=[("active", "Active"), ("fraud", "Fraud")],
                default="active",
                max_length=255,
                null=True,
            ),
        ),
    ]
