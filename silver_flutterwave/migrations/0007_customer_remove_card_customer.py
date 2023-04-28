# Generated by Django 4.2 on 2023-04-27 06:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0057_alter_billingdocumentbase_id_alter_billinglog_id_and_more'),
        ('silver_flutterwave', '0006_alter_card_country'),
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('customer_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='silver.customer')),
                ('stripe_customer_id', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('silver.customer',),
        ),
        migrations.RemoveField(
            model_name='card',
            name='customer',
        ),
    ]
