import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Giocatore, Canzone, Opzione, RispostaData
from django.db.models import Sum

class QuizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'matrimonio_quiz'
        self.nickname = None
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        # All'apertura del socket, notifichiamo la regia
        await self.notifica_cambio_utenti()

    async def disconnect(self, close_code):
        if self.nickname:
            # Quando un utente chiude l'app, lo segniamo come offline
            await self.set_online_status(self.nickname, False)
        
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.notifica_cambio_utenti()

    async def receive(self, text_data):
        data = json.loads(text_data)
        tipo = data.get('type')

        if tipo == 'join':
            self.nickname = data.get('nickname')
            # Segnamo l'utente come online nel DB
            await self.set_online_status(self.nickname, True)
            await self.send(text_data=json.dumps({'type': 'join_confirm', 'status': 'ok'}))
            await self.notifica_cambio_utenti()

        elif tipo == 'risposta':
            if not self.nickname: return
            canzone_id = data.get('canzone_id')
            opzione_testo = data.get('risposta')
            ms_rimanenti = data.get('ms_rimanenti', 0)
            
            # 1. Salvataggio punteggio
            punti = await self.calcola_e_salva_punteggio(canzone_id, opzione_testo, ms_rimanenti)
            await self.send(text_data=json.dumps({'type': 'risposta_ricevuta', 'punti': punti}))

            # 2. CALCOLO PROGRESSO (X su Y)
            progresso = await self.get_progresso_risposte(canzone_id)
            
            # Inviato a tutti (così la regia aggiorna il contatore "Risposte: 5/10")
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'notifica_progresso_risposte',
                    'risposte': progresso['risposte'],
                    'totale': progresso['totale']
                }
            )

            # 3. Se tutti hanno risposto, invia il comando di stop timer alla regia
            if progresso['risposte'] >= progresso['totale'] and progresso['totale'] > 0:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'comando_regia', 'comando': 'tutti_hanno_risposto'}
                )

    # --- HANDLERS (Messaggi ricevuti dal Channel Layer e inviati al Browser) ---

    async def notifica_progresso_risposte(self, event):
        """Invia alla regia il conteggio aggiornato delle risposte ricevute"""
        await self.send(text_data=json.dumps({
            'type': 'progresso_risposte',
            'risposte': event['risposte'],
            'totale': event['totale']
        }))

    async def comando_regia(self, event):
        await self.send(text_data=json.dumps({
            'type': event['comando'],
            'giocatori': event.get('giocatori', 0)
        }))

    async def aggiornamento_utenti(self, event):
        await self.send(text_data=json.dumps({
            'type': 'aggiornamento_utenti',
            'totale': event['totale']
        }))

    async def nuova_domanda(self, event):
        await self.send(text_data=json.dumps({
            'type': 'prossima_domanda',
            'canzone_id': event['id'],
            'opzioni': event['opzioni'],
            'numero': event['numero_domanda'],
            'totale': event['totale_domande']
        }))

    async def mostra_classifica(self, event):
        classifica = await self.get_classifica_completa()
        await self.send(text_data=json.dumps({
            'type': 'classifica_parziale',
            'classifica': classifica,
            'is_finale': event.get('is_finale', False)
        }))

    # --- HELPER ASINCRONI PER NOTIFICHE ---

    async def notifica_cambio_utenti(self):
        totale_online = await self.get_count_giocatori_online()
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'aggiornamento_utenti', 'totale': totale_online}
        )

    # --- METODI DATABASE (Sync to Async) ---

    @database_sync_to_async
    def set_online_status(self, nickname, status):
        Giocatore.objects.update_or_create(nickname=nickname, defaults={'is_online': status})

    @database_sync_to_async
    def get_count_giocatori_online(self):
        return Giocatore.objects.filter(is_online=True).count()

    @database_sync_to_async
    def get_progresso_risposte(self, canzone_id):
        risposte_ricevute = RispostaData.objects.filter(canzone_id=canzone_id).count()
        totale_online = Giocatore.objects.filter(is_online=True).count()
        return {'risposte': risposte_ricevute, 'totale': totale_online}

    @database_sync_to_async
    def calcola_e_salva_punteggio(self, canzone_id, opzione_testo, ms_rimanenti):
        canzone = Canzone.objects.get(id=canzone_id)
        giocatore = Giocatore.objects.get(nickname=self.nickname)
        corretta = Opzione.objects.filter(canzone=canzone, testo=opzione_testo, is_corretta=True).exists()
        
        punti = 500 + int(ms_rimanenti / 40) if corretta else 0
        
        RispostaData.objects.update_or_create(
            giocatore=giocatore, canzone=canzone,
            defaults={'tempo_impiegato_ms': 20000 - ms_rimanenti, 'punti_guadagnati': punti}
        )
        
        totale = RispostaData.objects.filter(giocatore=giocatore).aggregate(Sum('punti_guadagnati'))['punti_guadagnati__sum']
        giocatore.punteggio_totale = totale or 0
        giocatore.save()
        return punti

    @database_sync_to_async
    def get_classifica_completa(self):
        tutti = Giocatore.objects.order_by('-punteggio_totale')
        return [{'nickname': g.nickname, 'punti': g.punteggio_totale} for g in tutti]