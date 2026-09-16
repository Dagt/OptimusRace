from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    sex = models.CharField(max_length=1, choices=[('M','Hombres'),('F','Mujeres')])
    birth_date = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to='athletes/', blank=True)

class Exercise(models.Model):
    name = models.CharField(max_length=100, unique=True)
    unit = models.CharField(max_length=15)
    capacity = models.CharField(max_length=20, choices=[(x,x) for x in ['Fuerza','Resistencia','Velocidad','Potencia']])
    parameters = models.JSONField(default=dict, blank=True)
    higher = models.BooleanField(default=True)
    base = models.FloatField(null=True, blank=True)
    elite = models.FloatField(null=True, blank=True)
    def __str__(self): return self.name

class Event(models.Model):
    name = models.CharField(max_length=150)
    date = models.DateTimeField()
    registration_end = models.DateTimeField()
    location = models.CharField(max_length=200)
    price = models.PositiveIntegerField(default=50000, help_text='Centavos MXN')
    capacity = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=15, default='draft', choices=[('draft','Borrador'),('open','Inscripciones abiertas'),('live','En competencia'),('closed','Cerrado')])
    demo = models.BooleanField(default=False)
    rules = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    active_test = models.PositiveIntegerField(default=0)
    active_batch = models.PositiveIntegerField(default=1)
    final_board = models.JSONField(default=list)
    closed_at = models.DateTimeField(null=True)
    description = models.TextField(blank=True)
    allow_onsite = models.BooleanField(default=False)
    @property
    def current_price(self):
        from .event_policy import current_price
        return current_price(self)
    def __str__(self): return self.name

class Registration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    name = models.CharField(max_length=150)
    sex = models.CharField(max_length=1)
    birth_date = models.DateField(null=True, blank=True)
    bib = models.PositiveIntegerField()
    state = models.CharField(max_length=15, default='reserved')
    attendance = models.CharField(max_length=15, default='pending')
    weight = models.FloatField(null=True)
    category = models.CharField(max_length=100, blank=True)
    batch = models.PositiveIntegerField(default=1)
    pricing_code = models.CharField(max_length=40, blank=True)
    pricing_snapshot = models.JSONField(default=dict, blank=True)
    amount = models.PositiveIntegerField(default=0)
    method = models.CharField(max_length=10, blank=True)
    paid_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name='cash_collected')
    paid_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revision = models.PositiveIntegerField(default=0)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['event','user'],name='one_entry'), models.UniqueConstraint(fields=['event','bib'],name='one_bib')]

class Payment(models.Model):
    registration = models.ForeignKey(Registration,on_delete=models.PROTECT)
    key = models.CharField(max_length=100, unique=True)
    session_id = models.CharField(max_length=150, unique=True, null=True)
    url = models.URLField(max_length=2000,blank=True)
    state = models.CharField(max_length=15,default='creating')
    amount = models.PositiveIntegerField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    livemode = models.BooleanField(default=False)

class Webhook(models.Model):
    stripe_id = models.CharField(max_length=150,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Result(models.Model):
    registration = models.ForeignKey(Registration,on_delete=models.PROTECT)
    test = models.PositiveIntegerField()
    value = models.FloatField(null=True)
    points = models.FloatField(null=True)
    load = models.FloatField(null=True)
    status = models.CharField(max_length=15,default='done')
    revision = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['registration','test'],name='one_mark')]

class Audit(models.Model):
    actor = models.ForeignKey(User,null=True,on_delete=models.PROTECT)
    event = models.ForeignKey(Event,on_delete=models.PROTECT)
    action = models.CharField(max_length=60)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

class LoginAttempt(models.Model):
    key = models.CharField(max_length=64,unique=True)
    count = models.PositiveIntegerField(default=0)
    until = models.DateTimeField()


class TieBreak(models.Model):
    event = models.ForeignKey(Event,on_delete=models.PROTECT)
    category = models.CharField(max_length=100)
    total = models.FloatField()
    order = models.JSONField(default=list)
    fingerprint = models.CharField(max_length=64)
    challenge = models.CharField(max_length=150)
    details = models.TextField()
    judge = models.CharField(max_length=150)
    actor = models.ForeignKey(User,on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
