import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Giocatore, Canzone, Opzione, RispostaData
from django.db.models import Sum

class QuizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'matrimonio_quiz'
        self.nickname = None

        # Unisciti al gruppo
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        
        # Notifica alla regia (e a tutti) che il numero di connessioni è cambiato
        await self.notifica_cambio_utenti()

    async def disconnect(self, close_code):
        # Lascia il gruppo
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        # Notifica il cambio (diminuzione) degli utenti connessi
        await self.notifica_cambio_utenti()

    async def receive(self, text_data):
        data = json.loads(text_data)
        tipo = data.get('type')

        if tipo == 'join':
            self.nickname = data.get('nickname')
            await self.salva_giocatore(self.nickname)
            await self.send(text_data=json.dumps({
                'type': 'join_confirm', 
                'status': 'ok'
            }))
            # Notifichiamo di nuovo dopo il join perché un nuovo giocatore è registrato nel DB
            await self.notifica_cambio_utenti()

        elif tipo == 'risposta':
            if not self.nickname:
                return
                
            canzone_id = data.get('canzone_id')
            opzione_testo = data.get('risposta')
            tempo_risposta = data.get('ms_rimanenti')
            
            punti = await self.calcola_e_salva_punteggio(canzone_id, opzione_testo, tempo_risposta)
            await self.send(text_data=json.dumps({
                'type': 'risposta_ricevuta', 
                'punti': punti
            }))

            # Controllo se tutti hanno risposto
            tutti_risposto = await self.controlla_risposte_completate(canzone_id)
            if tutti_risposto:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'comando_regia_msg', 'comando': 'tutti_hanno_risposto'}
                )

    # --- GESTORI DEI MESSAGGI DI GRUPPO ---

    async def aggiornamento_utenti(self, event):
        """Invia il conteggio utenti al browser (Regia o Ospiti)"""
        await self.send(text_data=json.dumps({
            'type': 'aggiornamento_utenti',
            'totale': event['totale']
        }))

    async def nuova_domanda(self, event):
        """Invia i dati della prossima canzone a tutti gli ospiti"""
        await self.send(text_data=json.dumps({
            'type': 'prossima_domanda',
            'canzone_id': event['id'],
            'opzioni': event['opzioni'],
            'numero': event['numero_domanda'],
            'totale': event['totale_domande']
        }))

    async def mostra_classifica(self, event):
        """Invia la classifica parziale o finale a tutti"""
        classifica_completa = await self.get_classifica_completa()
        await self.send(text_data=json.dumps({
            'type': 'classifica_parziale',
            'classifica': classifica_completa,
            'is_finale': event.get('is_finale', False)
        }))

    async def comando_regia_msg(self, event):
        """Invia comandi generici (preparazione, annulla, tutti_risposto)"""
        await self.send(text_data=json.dumps({
            'type': event['comando'],
            'giocatori': event.get('giocatori', 0)
        }))

    # --- HELPER PER LA NOTIFICA ---

    async def notifica_cambio_utenti(self):
        """Invia a tutto il gruppo il conteggio aggiornato dei giocatori"""
        totale = await self.get_count_giocatori()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'aggiornamento_utenti',
                'totale': totale
            }
        )

    # --- METODI DATABASE (SYNC TO ASYNC) ---

    @database_sync_to_async
    def get_count_giocatori(self):
        return Giocatore.objects.count()

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
        
        # Aggiorno il totale del giocatore
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
        tutti = Giocatore.objects.order_by('-punteggio_totale')
        return [{'nickname': g.nickname, 'punti': g.punteggio_totale} for g in tutti]