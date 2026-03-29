import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Giocatore, Canzone, Opzione, RispostaData
from django.db.models import Sum

class QuizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'matrimonio_quiz'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        tipo = data.get('type')

        if tipo == 'join':
            self.nickname = data.get('nickname')
            await self.salva_giocatore(self.nickname)
            await self.send(text_data=json.dumps({'type': 'join_confirm', 'status': 'ok'}))

        elif tipo == 'risposta':
            canzone_id = data.get('canzone_id')
            opzione_testo = data.get('risposta')
            tempo_risposta = data.get('ms_rimanenti')
            
            punti = await self.calcola_e_salva_punteggio(canzone_id, opzione_testo, tempo_risposta)
            await self.send(text_data=json.dumps({'type': 'risposta_ricevuta', 'punti': punti}))

            tutti_risposto = await self.controlla_risposte_completate(canzone_id)
            if tutti_risposto:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'comando_regia', 'comando': 'tutti_hanno_risposto'}
                )

    async def nuova_domanda(self, event):
        await self.send(text_data=json.dumps({
            'type': 'prossima_domanda',
            'canzone_id': event['id'],
            'opzioni': event['opzioni'],
            'numero': event['numero_domanda'],
            'totale': event['totale_domande']
        }))

    async def mostra_classifica(self, event):
        # Prendiamo tutti i giocatori
        classifica_completa = await self.get_classifica_completa()
        await self.send(text_data=json.dumps({
            'type': 'classifica_parziale',
            'classifica': classifica_completa,
            'is_finale': event.get('is_finale', False)
        }))

    async def comando_regia(self, event):
        await self.send(text_data=json.dumps({
            'type': event['comando'],
            'giocatori': event.get('giocatori', 0)
        }))

    @database_sync_to_async
    def salva_giocatore(self, nickname):
        Giocatore.objects.get_or_create(nickname=nickname)

    @database_sync_to_async
    def calcola_e_salva_punteggio(self, canzone_id, opzione_testo, ms_rimanenti):
        canzone = Canzone.objects.get(id=canzone_id)
        giocatore = Giocatore.objects.get(nickname=self.nickname)
        corretta = Opzione.objects.filter(canzone=canzone, testo=opzione_testo, is_corretta=True).exists()
        
        punti = 0
        if corretta:
            punti = 500 + int(ms_rimanenti / 40) 
            
        RispostaData.objects.update_or_create(
            giocatore=giocatore, canzone=canzone,
            defaults={'tempo_impiegato_ms': 20000 - ms_rimanenti, 'punti_guadagnati': punti}
        )
        
        totale = RispostaData.objects.filter(giocatore=giocatore).aggregate(Sum('punti_guadagnati'))['punti_guadagnati__sum']
        giocatore.punteggio_totale = totale if totale else 0
        giocatore.save()
        return punti

    @database_sync_to_async
    def controlla_risposte_completate(self, canzone_id):
        risposte_date = RispostaData.objects.filter(canzone_id=canzone_id).count()
        totale_giocatori = Giocatore.objects.count()
        return risposte_date >= totale_giocatori

    @database_sync_to_async
    def get_classifica_completa(self):
        # Ordina TUTTI i giocatori dal punteggio più alto al più basso
        tutti = Giocatore.objects.order_by('-punteggio_totale')
        return [{'nickname': g.nickname, 'punti': g.punteggio_totale} for g in tutti]