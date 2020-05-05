# Generated by Django 3.0.5 on 2020-05-05 10:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0009_auto_20200505_1106'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ebayitem',
            name='description',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='wanteditem',
            name='notifications',
            field=models.ManyToManyField(related_name='wanted_items', to='alerts.NotificationRoute'),
        ),
    ]