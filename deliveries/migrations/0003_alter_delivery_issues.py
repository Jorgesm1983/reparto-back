# Generated by Django 5.1.1 on 2024-09-09 18:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deliveries', '0002_delivery_delivery_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='delivery',
            name='issues',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
