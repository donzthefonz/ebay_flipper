# Generated by Django 3.0.5 on 2020-05-04 17:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0006_auto_20200504_1625'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationroute',
            name='type',
            field=models.CharField(choices=[('DIS', 'Discord'), ('SLK', 'Slack')], default='DIS', max_length=3),
            preserve_default=False,
        ),
    ]
