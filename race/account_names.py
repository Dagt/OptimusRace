from .models import AccountName

def name_parts(user):
    parts=AccountName.objects.filter(user=user).first()
    return {'name':user.first_name,'paternal':parts.paternal if parts else user.last_name,'maternal':parts.maternal if parts else ''}

def save_name(user,data):
    user.first_name=data['name'].strip()
    paternal=data.get('paternal','').strip();maternal=data.get('maternal','').strip()
    user.last_name=' '.join(x for x in [paternal,maternal] if x)
    user.save(update_fields=['first_name','last_name'])
    AccountName.objects.update_or_create(user=user,defaults={'paternal':paternal,'maternal':maternal})
