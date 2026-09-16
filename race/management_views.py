from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User,Group
from django.db import transaction,IntegrityError
from django.db.models import Q
from .views import administrator
from .models import Profile,Exercise
from .management_forms import TeamForm,CatalogForm

def role_of(user):
    return 'admin' if user.is_superuser else 'coach' if user.groups.filter(name='Coach').exists() else 'athlete'

@administrator
def team(request):
    query=request.GET.get('q','').strip()
    accounts=User.objects.select_related('profile').prefetch_related('groups').order_by('first_name','username')
    if query:accounts=accounts.filter(Q(first_name__icontains=query)|Q(email__icontains=query)|Q(username__icontains=query))
    selected=request.GET.get('role','')
    if selected=='admin':accounts=accounts.filter(is_superuser=True)
    elif selected=='coach':accounts=accounts.filter(is_superuser=False,groups__name='Coach')
    elif selected=='athlete':accounts=accounts.filter(is_superuser=False).exclude(groups__name='Coach')
    rows=[{'account':u,'label':{'admin':'Administrador','coach':'Coach','athlete':'Participante'}[role_of(u)]} for u in accounts.distinct()]
    return render(request,'team.html',{'rows':rows,'query':query,'selected_role':selected})

@administrator
def team_edit(request,pk=None):
    account=get_object_or_404(User,pk=pk) if pk else None
    initial={'name':account.first_name,'email':account.email or account.username,'role':role_of(account),'active':account.is_active,'birth_date':account.profile.birth_date if hasattr(account,'profile') else None,'sex':account.profile.sex if hasattr(account,'profile') else ''} if account else {}
    form=TeamForm(request.POST or None,account=account,initial=initial)
    if request.method=='POST' and form.is_valid():
        d=form.cleaned_data
        if account and account.pk==request.user.pk and (not d['active'] or d['role']!='admin'):
            form.add_error(None,'No puedes desactivar tu propio acceso ni quitarte el rol de administrador.')
        else:
            try:
                with transaction.atomic():
                    saved=User.objects.select_for_update().get(pk=account.pk) if account else User()
                    saved.username=d['email'];saved.email=d['email'];saved.first_name=d['name'];saved.is_active=d.get('active',True);saved.is_superuser=d['role']=='admin';saved.is_staff=saved.is_superuser
                    if d['password']:saved.set_password(d['password'])
                    saved.save()
                    group,_=Group.objects.get_or_create(name='Coach')
                    if d['role']=='coach':saved.groups.add(group)
                    else:saved.groups.remove(group)
                    if d['role']=='athlete':
                        profile,_=Profile.objects.get_or_create(user=saved,defaults={'sex':d['sex']});profile.sex=d['sex'];profile.birth_date=d.get('birth_date');profile.save(update_fields=['sex','birth_date'])
                if saved.pk==request.user.pk and d['password']:update_session_auth_hash(request,saved)
                messages.success(request,'Usuario actualizado.' if account else 'Usuario creado. Ya puede ingresar con su correo y contraseña.')
                return redirect('team')
            except IntegrityError:form.add_error('email','Este correo ya pertenece a otra cuenta.')
    return render(request,'management_edit.html',{'form':form,'heading':'Editar usuario' if account else 'Crear usuario','kind':'team','account':account})

@administrator
def catalog(request):
    query=request.GET.get('q','').strip()
    exercises=Exercise.objects.order_by('capacity','name')
    if query:exercises=exercises.filter(Q(name__icontains=query)|Q(capacity__icontains=query))
    return render(request,'catalog.html',{'exercises':exercises,'query':query})

@administrator
def catalog_edit(request,pk=None):
    exercise=get_object_or_404(Exercise,pk=pk) if pk else None
    form=CatalogForm(request.POST or None,instance=exercise)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():form.save()
            messages.success(request,'Prueba guardada. Las reglas de eventos existentes se conservan.')
            return redirect('catalog')
        except IntegrityError:form.add_error('name','Ya existe una prueba con ese nombre.')
    return render(request,'management_edit.html',{'form':form,'heading':'Editar prueba' if exercise else 'Crear prueba','kind':'catalog'})
