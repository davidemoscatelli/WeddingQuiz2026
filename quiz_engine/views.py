from django.shortcuts import render, redirect
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Canzone, Giocatore, RispostaData, StatoQuiz
from django.contrib.auth.decorators import login_required

@login_required
def telecomando(request):
    # 1. Recuperiamo lo stato (o creiamolo se non esiste)
    stato, created = StatoQuiz.objects.get_or_create(id=1)
    
    # 2. Variabili globali per il template
    totale_domande = Canzone.objects.count()
    
    # 3. Inizializziamo la canzone corrente se manca
    if not stato.canzone_corrente:
        stato.canzone_corrente = Canzone.objects.order_by('ordine_scaletta').first()
        stato.save()

    channel_layer = get_channel_layer()
    
    if request.method == 'POST':
        azione = request.POST.get('azione')
        
        if azione == 'vai_a_preparazione':
            stato.fase = 'LANCIO'
            stato.save()
            giocatori_totali = Giocatore.objects.filter(is_online=True).count()
            async_to_sync(channel_layer.group_send)(
                'matrimonio_quiz',
                {
                    'type': 'comando_regia', 
                    'comando': 'schermata_preparazione', 
                    'giocatori': giocatori_totali
                }
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
            # 1. Inviamo sempre il segnale ai telefoni per aggiornare la classifica
            async_to_sync(channel_layer.group_send)(
                'matrimonio_quiz', 
                {'type': 'mostra_classifica', 'is_finale': False}
            )
            
            # 2. CAMBIO CANZONE: Solo se veniamo dalla fase di gioco!
            # Se siamo già in fase CLASSIFICA e clicchiamo "Aggiorna", non deve saltare alla successiva.
            if stato.fase == 'DOMANDA':
                prossima = Canzone.objects.filter(
                    ordine_scaletta__gt=stato.canzone_corrente.ordine_scaletta
                ).order_by('ordine_scaletta').first()
                
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

        elif azione == 'annulla':
            # Cancelliamo le risposte della canzone corrente per permettere di rigiocarla pulita
            RispostaData.objects.filter(canzone=stato.canzone_corrente).delete()
            
            stato.fase = 'LANCIO'
            stato.save()
            async_to_sync(channel_layer.group_send)(
                'matrimonio_quiz',
                {'type': 'comando_regia', 'comando': 'annulla_tutto'}
            )

        elif azione == 'reset_quiz':
            RispostaData.objects.all().delete()
            stato.fase = 'PREPARAZIONE'
            stato.canzone_corrente = Canzone.objects.order_by('ordine_scaletta').first()
            stato.save()
            return redirect('regia')

    return render(request, 'telecomando.html', {
        'stato': stato, 
        'totale_domande': totale_domande
    })