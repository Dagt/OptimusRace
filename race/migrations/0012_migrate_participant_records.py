from django.db import migrations

def migrate_people(apps,schema_editor):
    User=apps.get_model('auth','User');Person=apps.get_model('race','Participant');Profile=apps.get_model('race','Profile');Names=apps.get_model('race','AccountName');Registration=apps.get_model('race','Registration')
    for user in User.objects.all().iterator():
        staff=user.is_superuser or user.is_staff or user.groups.filter(name='Coach').exists()
        if staff and not Registration.objects.filter(user_id=user.pk).exists():continue
        profile=Profile.objects.filter(user_id=user.pk).first();names=Names.objects.filter(user_id=user.pk).first()
        person=Person.objects.create(legacy_user_id=user.pk,name=user.first_name or user.username,paternal=names.paternal if names else user.last_name,maternal=names.maternal if names else '',email=user.email,sex=profile.sex if profile else '',birth_date=profile.birth_date if profile else None,photo=profile.photo.name if profile else '',original_photo=profile.original_photo.name if profile else '')
        Registration.objects.filter(user_id=user.pk).update(participant_id=person.pk)
        if not staff:User.objects.filter(pk=user.pk).update(is_active=False)

class Migration(migrations.Migration):
    dependencies=[('race','0011_alter_registration_user_participant_and_more')]
    operations=[migrations.RunPython(migrate_people)]
