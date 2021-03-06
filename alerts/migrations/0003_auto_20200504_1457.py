# Generated by Django 3.0.5 on 2020-05-04 13:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0002_auto_20200504_1440'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ebayitem',
            options={'verbose_name': 'Ebay Item', 'verbose_name_plural': 'Ebay Items'},
        ),
        migrations.AlterModelOptions(
            name='notification',
            options={'verbose_name': 'Notification', 'verbose_name_plural': 'Notifications'},
        ),
        migrations.AlterModelOptions(
            name='wanteditem',
            options={'verbose_name': 'Wanted Item', 'verbose_name_plural': 'Wanted Items'},
        ),
        migrations.AddField(
            model_name='wanteditem',
            name='deleted',
            field=models.BooleanField(default=False),
        ),
    ]
