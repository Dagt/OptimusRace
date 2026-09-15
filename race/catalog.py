from .models import Exercise

CATALOG=[('Sentadilla','reps','Fuerza',True,30,60),('Press banca','reps','Fuerza',True,None,None),('1000 m','seg','Resistencia',False,300,210),('Burpees 5 min','reps','Resistencia',True,50,90),('50 m','seg','Velocidad',False,8,6.5),('Shuttle 10x10','seg','Velocidad',False,30,22),('Salto horizontal','m','Potencia',True,1.8,2.7),('Salto vertical','cm','Potencia',True,45,75),('Dominadas','reps','Fuerza',True,8,20)]

def seed_catalog():
    for name,unit,capacity,higher,base,elite in CATALOG:
        Exercise.objects.get_or_create(name=name,defaults=dict(unit=unit,capacity=capacity,higher=higher,base=base,elite=elite))
