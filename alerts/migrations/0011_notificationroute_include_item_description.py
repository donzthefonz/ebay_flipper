# Generated by Django 3.0.5 on 2020-05-05 10:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0010_auto_20200505_1112'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationroute',
            name='include_item_description',
            field=models.BooleanField(default=False),
        ),
    ]