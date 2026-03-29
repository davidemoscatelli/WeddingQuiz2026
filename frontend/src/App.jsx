import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Trophy, Clock, PartyPopper, AlertCircle, Music, Medal } from 'lucide-react';
import confetti from 'canvas-confetti';

const WS_URL = "ws://localhost:8000/ws/quiz/"; 

function App() {
  const [fase, setFase] = useState('LOGIN'); 
  const [nickname, setNickname] = useState('');
  const [errore, setErrore] = useState('');
  const [socket, setSocket] = useState(null);
  const [domanda, setDomanda] = useState(null);
  
  // STATI DEL TIMER AGGIORNATI
  const [timer, setTimer] = useState(60);
  const [endTime, setEndTime] = useState(null); // NUOVO: Memorizza l'ora esatta di fine
  
  const [classifica, setClassifica] = useState([]);
  const [giocatoriConnessi, setGiocatoriConnessi] = useState(0);
  const [progresso, setProgresso] = useState({ numero: 0, totale: 0 });
  const [isFinale, setIsFinale] = useState(false);

  useEffect(() => {
    let ws;

    const connectWebSocket = () => {
      ws = new WebSocket(WS_URL);
      
      ws.onopen = () => {
        const nomeSalvato = localStorage.getItem('wedding_quiz_nickname');
        if (nomeSalvato) {
          setNickname(nomeSalvato);
          ws.send(JSON.stringify({ type: 'join', nickname: nomeSalvato }));
          setFase('ATTESA');
        }
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const utenteRegistrato = localStorage.getItem('wedding_quiz_nickname');
        
        // Se non hai ancora inserito il nome, ignora i comandi della regia!
        if (!utenteRegistrato) {
            return; 
        }

        if (data.type === 'prossima_domanda') {
          setDomanda(data);
          
          // IMPOSTIAMO LA SCADENZA ESATTA (Ora attuale + 60 secondi)
          const scadenza = Date.now() + 60000;
          setEndTime(scadenza);
          setTimer(60);
          
          setProgresso({ numero: data.numero, totale: data.totale });
          setFase('DOMANDA');
        } else if (data.type === 'classifica_parziale') {
          setClassifica(data.classifica);
          setIsFinale(data.is_finale);
          setFase('PODIO');
          
          if (data.is_finale) {
            confetti({ particleCount: 350, spread: 130, origin: { y: 0.5 }, colors: ['#d97706', '#fbbf24', '#ffffff', '#ef4444', '#3b82f6'] });
          } else {
            confetti({ particleCount: 150, spread: 80, origin: { y: 0.6 }, colors: ['#d97706', '#fbbf24', '#ffffff'] });
          }
          
        } else if (data.type === 'schermata_preparazione') {
          setGiocatoriConnessi(data.giocatori);
          setFase('PREPARAZIONE');
        } else if (data.type === 'annulla_tutto') {
          setEndTime(null);
          setFase('ATTESA'); 
        } else if (data.type === 'tutti_hanno_risposto') {
          setTimer(0);
          setEndTime(null);
          setFase('ATTESA_CLASSIFICA');
        }
      };

      ws.onclose = () => setTimeout(connectWebSocket, 2000);
      setSocket(ws);
    };

    connectWebSocket();
    return () => { if (ws) ws.close(); };
  }, []);

  // --- NUOVO USE-EFFECT PER IL TIMER ANTI-BLOCCO ---
  useEffect(() => {
    let interval;
    
    // Il timer gira solo se siamo in queste due fasi e se esiste un endTime
    if ((fase === 'DOMANDA' || fase === 'RISPOSTA_DATA') && endTime) {
      // Usiamo 200ms invece di 1000ms per rendere la barra fluidissima e super reattiva
      interval = setInterval(() => {
        const now = Date.now();
        const msRimanenti = endTime - now;
        const secondiRimanenti = Math.ceil(msRimanenti / 1000);

        if (msRimanenti > 0) {
          // Se scende sotto il secondo precedente, aggiorna l'UI
          if (secondiRimanenti !== timer) {
            setTimer(secondiRimanenti);
          }
        } else {
          // TEMPO SCADUTO!
          setTimer(0);
          setFase('ATTESA_CLASSIFICA');
          clearInterval(interval);
        }
      }, 200); 
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [fase, endTime, timer]);

  const handleJoin = (e) => {
    e.preventDefault();
    if (!nickname.trim()) { setErrore("Ehi! Non hai inserito il nome! 😅"); return; }
    if (nickname.trim().length < 2) { setErrore("Troppo corto, non fare il timido! 🕵️‍♂️"); return; }
    
    setErrore('');
    // SALVA IL NOME: Da questo momento in poi ascolterà la regia!
    localStorage.setItem('wedding_quiz_nickname', nickname.trim());
    
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'join', nickname: nickname.trim() }));
      setFase('ATTESA');
    }
  };

  const inviaRisposta = (opzione) => {
    if (!socket) return;
    
    // Calcoliamo i millisecondi ESATTI in cui è stata data la risposta
    const msEsattiRimanenti = endTime ? Math.max(0, endTime - Date.now()) : 0;
    
    socket.send(JSON.stringify({
      type: 'risposta', canzone_id: domanda.canzone_id,
      risposta: opzione, ms_rimanenti: msEsattiRimanenti
    }));
    setFase('RISPOSTA_DATA');
  };

  const getMieStats = () => {
    const mioIndex = classifica.findIndex(u => u.nickname.toLowerCase() === nickname.toLowerCase());
    if (mioIndex === -1) return { posizione: '-', punti: 0 };
    return { posizione: mioIndex + 1, punti: classifica[mioIndex].punti };
  };

  // --- SCHERMATE ---
  if (fase === 'LOGIN') return (
    <div className="app-container">
      <motion.div initial={{ scale: 0.8 }} animate={{ scale: 1 }} className="card">
        <PartyPopper size={64} color="#d97706" style={{marginBottom: '1rem'}} />
        <h1 style={{fontSize: '2.5rem', marginBottom: '0'}}>Wedding</h1>
        <h1 style={{fontSize: '1.8rem', marginTop: 0}}>Soundtrack Challenge</h1>
        <form onSubmit={handleJoin}>
          <input type="text" placeholder="Es. Il Testimone" value={nickname} onChange={(e) => { setNickname(e.target.value); setErrore(''); }} maxLength={20} />
          {errore && <p style={{ color: '#ef4444', fontWeight: 'bold' }}>{errore}</p>}
          <button type="submit">INIZIA A FESTEGGIARE!</button>
        </form>
      </motion.div>
    </div>
  );

  if (fase === 'ATTESA') return (
    <div className="app-container">
      <div className="loader-wedding">❤️</div>
      <h2>Scalda le orecchie, {nickname}!</h2>
      <p>L'orchestra sta accordando gli strumenti... <br/>Il quiz sta per iniziare!</p>
    </div>
  );

  if (fase === 'PREPARAZIONE') return (
    <div className="app-container">
      <motion.div animate={{ scale: [1, 1.1, 1] }} transition={{ repeat: Infinity, duration: 1.5 }}>
        <AlertCircle size={80} color="#d97706" style={{margin: '0 auto'}}/>
      </motion.div>
      <h1 style={{fontSize: '2.5rem', color: '#ef4444', marginTop: '1rem'}}>ATTENZIONE!</h1>
      <h2>Stiamo per partire!</h2>
      <p>Siete in <b>{giocatoriConnessi}</b> pronti a sfidarvi. La prima canzone sta arrivando...</p>
    </div>
  );

  const renderHeaderDomanda = () => (
    <div style={{ background: '#e2e8f0', borderRadius: '1rem', padding: '10px', marginBottom: '1rem', color: '#1e293b', fontWeight: 'bold' }}>
      {progresso.numero === progresso.totale 
        ? <span style={{color: '#ef4444'}}>🔥 ULTIMA CANZONE! DAI IL MASSIMO! 🔥</span> 
        : <span>🎧 Brano {progresso.numero} di {progresso.totale}</span>
      }
    </div>
  );

  if (fase === 'DOMANDA') return (
    <div className="app-container">
      {renderHeaderDomanda()}
      <div className="timer-bar-bg"><div className="timer-bar-fill" style={{ width: `${(timer/60)*100}%`, transition: 'width 0.2s linear' }}></div></div>
      <div style={{fontSize: '24px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px'}}><Clock size={24} color="#d97706" /> {timer}s</div>
      <h2 style={{marginTop: '1rem'}}>Ascolta la band... <br/> Che canzone è?</h2>
      <div className="opzioni-grid">
        {domanda.opzioni.map((opt, i) => (
          <motion.button whileTap={{ scale: 0.95 }} key={i} onClick={() => inviaRisposta(opt)}>{opt}</motion.button>
        ))}
      </div>
    </div>
  );

  if (fase === 'RISPOSTA_DATA') return (
    <div className="app-container">
      {renderHeaderDomanda()}
      <div className="timer-bar-bg"><div className="timer-bar-fill" style={{ width: `${(timer/60)*100}%`, transition: 'width 0.2s linear' }}></div></div>
      <div style={{fontSize: '24px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px'}}><Clock size={24} color="#d97706" /> {timer}s</div>
      <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} style={{marginTop: '2rem'}}>
        <Clock size={80} color="#94a3b8" style={{animation: 'pulse 2s infinite', margin: '0 auto'}} />
        <h2>Presa! 📩</h2>
        <p>Ottima mossa, {nickname}. <br/> Aspettiamo che scada il tempo (o che rispondano tutti).</p>
      </motion.div>
    </div>
  );

  if (fase === 'ATTESA_CLASSIFICA') return (
    <div className="app-container">
      <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}>
        <Music size={80} color="#d97706" style={{margin: '0 auto', animation: 'bounce 2s infinite'}} />
        <h2 style={{marginTop: '1.5rem', fontSize: '2rem'}}>Tempo Scaduto! 🛑</h2>
        <p style={{fontSize: '1.2rem', margin: '1rem 0'}}>Metti giù il telefono e goditi l'orchestra 🎻</p>
        <p style={{opacity: 0.8, fontStyle: 'italic'}}>La classifica arriverà a breve, appena lo sposo darà l'ok...</p>
      </motion.div>
    </div>
  );

  if (fase === 'PODIO') {
    const top3 = classifica.slice(0, 3);
    const mieStats = getMieStats();
    
    return (
      <div className="app-container">
        <motion.div initial={{ scale: 0.5 }} animate={{ scale: 1 }}>
          <Trophy size={80} color="#d97706" style={{marginBottom: '0.5rem'}} />
        </motion.div>
        
        {isFinale ? (
          <h1 style={{color: '#ef4444', fontSize: '2.5rem', marginTop: 0}}>🎉 PODIO FINALE 🎉</h1>
        ) : (
          <h1 style={{marginTop: 0}}>Classifica Temporanea</h1>
        )}

        <div className="classifica-list">
          {top3.length === 0 && <p>Nessuno ha indovinato? Siete un disastro! 😂</p>}
          {top3.map((user, i) => (
            <motion.div initial={{ x: -50, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: i * 0.3 }} key={i} className={`rank-item rank-${i+1}`}>
              <span style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                {i === 0 && '🥇'} {i === 1 && '🥈'} {i === 2 && '🥉'} {user.nickname}
              </span>
              <b className="rank-points">{user.punti} PT</b>
            </motion.div>
          ))}
        </div>

        <motion.div 
          initial={{ y: 50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 1 }}
          style={{ marginTop: '2rem', padding: '1.5rem', background: '#ffffff', borderRadius: '1rem', border: '2px solid #cbd5e1', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}
        >
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
            <Medal size={28} color="#1e293b" />
            <h3 style={{ margin: 0, color: '#1e293b' }}>I TUOI RISULTATI</h3>
          </div>
          
          <p style={{ fontSize: '1.2rem', margin: '5px 0' }}>
            Sei attualmente <b>{mieStats.posizione}°</b> su <b>{classifica.length}</b>
          </p>
          <p style={{ fontSize: '1.1rem', margin: '5px 0', opacity: 0.8 }}>Punti totali: <b>{mieStats.punti}</b></p>
          
          {isFinale && (
            <p style={{ marginTop: '15px', fontWeight: 'bold', color: '#d97706' }}>Grazie per aver giocato con noi! 🥂</p>
          )}
        </motion.div>

        {!isFinale && (
          <p style={{marginTop: '2rem', fontStyle: 'italic', opacity: 0.8}}>Fai un respiro profondo... <br/> La prossima canzone sta per arrivare.</p>
        )}
      </div>
    );
  }
}

export default App;