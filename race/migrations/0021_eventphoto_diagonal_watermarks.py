from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('race', '0020_eventphoto_watermark_opacity')]

    operations = [
        migrations.AddField(model_name='eventphoto', name='watermark_version',
            field=models.PositiveSmallIntegerField(default=1, db_default=1, editable=False)),
        migrations.AlterField(model_name='eventphoto', name='watermark_version',
            field=models.PositiveSmallIntegerField(default=2, db_default=1, editable=False)),
        migrations.AlterField(model_name='eventphoto', name='watermark_opacity',
            field=models.PositiveSmallIntegerField(default=85, db_default=45, editable=False)),
    ]
