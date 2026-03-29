from django.shortcuts import render, redirect
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Canzone, Giocatore, RispostaData, StatoQuiz
from django.contrib.auth.decorators import login_required

@login_required
def telecomando(request):
    # 1. Recuperiamo lo stato (o creiamolo se non esiste)
    stato, created = StatoQuiz.objects.get_or_create(id=1)
    
    # 2. DEFINIAMO SUBITO LA VARIABILE (Così evitiamo l'UnboundLocalError)
    totale_domande = Canzone.objects.count()
    
    # 3. Inizializziamo la canzone corrente se lo stato è nuovo
    if created or not stato.canzone_corrente:
        stato.canzone_corrente = Canzone.objects.order_by('ordine_scaletta').first()
        stato.save()

    channel_layer = get_channel_layer()
    
    if request.method == 'POST':
        azione = request.POST.get('azione')
        
        if azione == 'vai_a_preparazione':
            stato.fase = 'PREPARAZIONE'
            stato.save()
            giocatori_totali = Giocatore.objects.count()
            async_to_sync(channel_layer.group_send)(
                'matrimonio_quiz',
                {'type': 'comando_regia', 'comando': 'schermata_preparazione', 'giocatori': giocatori_totali}
            )

        elif azione == 'lancia_canzone':
            canzone = stato.canzone_corrente
            if canzone:
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
                stato.fase = 'DOMANDA'
                stato.save()

        elif azione == 'mostra_classifica_parziale':
            async_to_sync(channel_layer.group_send)(
                'matrimonio_quiz', 
                {'type': 'mostra_classifica', 'is_finale': False}
            )
            # Cerchiamo la prossima canzone
            prossima = Canzone.objects.filter(ordine_scaletta__gt=stato.canzone_corrente.ordine_scaletta).order_by('ordine_scaletta').first()
            if prossima:
                stato.canzone_corrente = prossima
                stato.fase = 'CLASSIFICA'
            else:
                stato.fase = 'PODIO'
            stato.save()

        elif azione == 'mostra_podio_finale':
            async_to_sync(channel_layer.group_send)(
                'matrimonio_quiz', 
                {'type': 'mostra_classifica', 'is_finale': True}
            )

        elif azione == 'reset_quiz':
            RispostaData.objects.all().delete()
            stato.fase = 'PREPARAZIONE'
            stato.canzone_corrente = Canzone.objects.order_by('ordine_scaletta').first()
            stato.save()
            return redirect('regia')

    # 4. Passiamo totale_domande al template
    return render(request, 'telecomando.html', {
        'stato': stato, 
        'totale_domande': totale_domande
    })