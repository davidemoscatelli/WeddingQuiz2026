from django.shortcuts import render
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Canzone, Giocatore, RispostaData
from django.contrib.auth.decorators import login_required


@login_required
def telecomando(request):
    canzoni = Canzone.objects.all().order_by('ordine_scaletta')
    totale_domande = canzoni.count() # Contiamo le canzoni totali
    
    if request.method == 'POST':
        canzone_id = request.POST.get('canzone_id')
        azione = request.POST.get('azione')
        channel_layer = get_channel_layer()

        if azione == 'start_canzone':
            canzone = Canzone.objects.get(id=canzone_id)
            opzioni = list(canzone.opzioni.values_list('testo', flat=True))
            async_to_sync(channel_layer.group_send)(
                'matrimonio_quiz',
                {
                    'type': 'nuova_domanda', 
                    'id': canzone.id, 
                    'opzioni': opzioni,
                    'numero_domanda': canzone.ordine_scaletta,
                    'totale_domande': totale_domande
                }
            )

        elif azione == 'mostra_classifica':
            async_to_sync(channel_layer.group_send)(
                'matrimonio_quiz', 
                {'type': 'mostra_classifica', 'is_finale': False}
            )

        elif azione == 'mostra_classifica_finale':
            async_to_sync(channel_layer.group_send)(
                'matrimonio_quiz', 
                {'type': 'mostra_classifica', 'is_finale': True}
            )

        elif azione == 'preparatevi':
            giocatori_totali = Giocatore.objects.count()
            async_to_sync(channel_layer.group_send)(
                'matrimonio_quiz',
                {'type': 'comando_regia', 'comando': 'schermata_preparazione', 'giocatori': giocatori_totali}
            )

        elif azione == 'annulla':
            if canzone_id:
                RispostaData.objects.filter(canzone_id=canzone_id).delete()
            async_to_sync(channel_layer.group_send)(
                'matrimonio_quiz',
                {'type': 'comando_regia', 'comando': 'annulla_tutto'}
            )

    return render(request, 'telecomando.html', {'canzoni': canzoni})