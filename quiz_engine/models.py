from django.db import models

class Giocatore(models.Model):
    nickname = models.CharField(max_length=50, unique=True)
    punteggio_totale = models.IntegerField(default=0)
    is_online = models.BooleanField(default=False) # <--- Usato per il contatore real-time

    def __str__(self):
        return self.nickname

class Canzone(models.Model):
    titolo = models.CharField(max_length=100)
    ordine_scaletta = models.IntegerField(unique=True)
    testo_domanda = models.TextField(default="Che canzone è questa?")
    
    def __str__(self):
        return f"{self.ordine_scaletta} - {self.titolo}"

class Opzione(models.Model):
    canzone = models.ForeignKey(Canzone, related_name='opzioni', on_delete=models.CASCADE)
    testo = models.CharField(max_length=100)
    is_corretta = models.BooleanField(default=False)

    def __str__(self):
        return self.testo

class RispostaData(models.Model):
    giocatore = models.ForeignKey(Giocatore, on_delete=models.CASCADE)
    canzone = models.ForeignKey(Canzone, on_delete=models.CASCADE)
    tempo_impiegato_ms = models.IntegerField()
    punti_guadagnati = models.IntegerField(default=0)

    class Meta:
        unique_together = ('giocatore', 'canzone')

# Spostata fuori e indentata correttamente
class StatoQuiz(models.Model):
    FASI = [
        ('PREPARAZIONE', 'Schermata Iniziale'),
        ('DOMANDA', 'Canzone in corso'),
        ('CLASSIFICA', 'Classifica della canzone'),
        ('PODIO', 'Podio Finale'),
    ]
    canzone_corrente = models.ForeignKey(Canzone, on_delete=models.SET_NULL, null=True, blank=True)
    fase = models.CharField(max_length=20, choices=FASI, default='PREPARAZIONE')

    class Meta:
        verbose_name_plural = "Stato Quiz"