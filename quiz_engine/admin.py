from django.contrib import admin
from .models import Giocatore, Canzone, Opzione, RispostaData

# Questo serve per inserire le 4 opzioni direttamente dentro la pagina della canzone
class OpzioneInline(admin.TabularInline):
    model = Opzione
    extra = 4 # Ti mostra subito 4 spazi da riempire

@admin.register(Canzone)
class CanzoneAdmin(admin.ModelAdmin):
    inlines = [OpzioneInline]
    list_display = ('ordine_scaletta', 'titolo')

admin.site.register(Giocatore)
admin.site.register(RispostaData)