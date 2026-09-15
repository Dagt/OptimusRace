import stripe
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from django.utils import timezone
from race.models import Payment,Registration
from race.services import fulfill,audit,payment_mode
from django.core.exceptions import ValidationError

class Command(BaseCommand):
    help='Consulta Stripe para recuperar confirmaciones/expiraciones perdidas. No cobra.'
    def handle(self,*args,**options):
        key=settings.STRIPE_SECRET_KEY
        try: live=payment_mode()
        except ValidationError as exc: raise CommandError(' '.join(exc.messages))
        for p in Payment.objects.filter(state__in=['creating','pending']).select_related('registration'):
            if p.livemode!=live:
                self.stderr.write(f'{p.id}: modo distinto, se conserva reserva.');continue
            try:
                if p.session_id: session=stripe.checkout.Session.retrieve(p.session_id,api_key=key)
                else:
                    sessions=stripe.checkout.Session.list(api_key=key,created={'gte':int(p.created_at.timestamp())-60},limit=100)
                    session=next((s for s in sessions.auto_paging_iter() if s.metadata.get('payment_id')==str(p.id)),None)
                    if not session:
                        # Expired creation timestamp cannot create a future Checkout.
                        if timezone.now()>p.expires_at:
                            with transaction.atomic():
                                locked=Payment.objects.select_for_update().get(pk=p.id)
                                if locked.state=='creating' and not locked.session_id:
                                    locked.state='expired';locked.save();Registration.objects.filter(pk=p.registration_id,state='reserved').update(state='expired')
                                    audit(p.registration.event,None,'reconciled_no_session',{'payment':p.id})
                        self.stdout.write(f'{p.id}: sin sesión encontrada');continue
                if session.payment_status=='paid': kind='checkout.session.completed'
                elif session.status=='expired': kind='checkout.session.expired'
                else:
                    Payment.objects.filter(pk=p.id,state='creating').update(session_id=session.id,url=session.url or '',state='pending')
                    self.stdout.write(f'{p.id}: pendiente');continue
                fulfill({'id':f'reconcile:{session.id}:{session.status}:{session.payment_status}','type':kind,'data':{'object':session}})
                self.stdout.write(f'{p.id}: conciliado')
            except (stripe.StripeError,ValidationError) as exc: self.stderr.write(f'{p.id}: conciliación pendiente ({type(exc).__name__}). Se conserva reserva para revisión.')
