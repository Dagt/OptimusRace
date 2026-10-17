from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('race', '0019_event_photo_gallery')]

    operations = [
        # Existing photos were processed at approximately 45%; new uploads use 75%.
        migrations.AddField(
            model_name='eventphoto', name='watermark_opacity',
            field=models.PositiveSmallIntegerField(default=45, db_default=45, editable=False)),
        migrations.AlterField(
            model_name='eventphoto', name='watermark_opacity',
            field=models.PositiveSmallIntegerField(default=75, db_default=45, editable=False)),
    ]
