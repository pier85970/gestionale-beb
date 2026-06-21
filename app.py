import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import json
import os
import requests
from icalendar import Calendar

# Configurazione Pagina
st.set_page_config(page_title="Gestionale B&B", layout="wide", initial_sidebar_state="expanded")

# --- CLASSI CORE ---
class Ospite:
    def __init__(self, id_ospite, nome, cognome, luogo_nascita, data_nascita):
        self.id = id_ospite
        self.nome = nome
        self.cognome = cognome
        self.luogo_nascita = luogo_nascita
        self.data_nascita = data_nascita

class Stanza:
    def __init__(self, nome, max_ospiti=4):
        self.nome = nome
        self.max_ospiti = max_ospiti # Limite massimo impostato a 4

class Prenotazione:
    def __init__(self, ospite: Ospite, stanza: Stanza, check_in: date, check_out: date, numero_ospiti=1, colazione=False, sorgente="Manuale"):
        self.ospite = ospite
        self.stanza = stanza
        self.check_in = check_in
        self.check_out = check_out
        self.numero_ospiti = numero_ospiti
        self.colazione = colazione
        self.sorgente = sorgente

class GestionaleBnb:
    def __init__(self):
        self.FILE_OSPITI = "ospiti.json"
        self.FILE_PRENOTAZIONI = "prenotazioni.json"
        
        self.ELENCO_CASE = ["Casa Mariateresa", "Casa Antonetta", "Casa Peppino"]
        # Inizializziamo tutte le stanze con un massimo di 4 ospiti
        self.stanze = [Stanza(c, max_ospiti=4) for c in self.ELENCO_CASE]
        
        self.URL_ICAL_BOOKING = {
            "Casa Mariateresa": "https://ical.booking.com/v1/export?t=INSERISCI_QUI_IL_LINK_MARIATERESA",
            "Casa Antonetta": "https://ical.booking.com/v1/export?t=b5998ab5-6b80-4574-bbae-91543acbbf08",
            "Casa Peppino": "https://ical.booking.com/v1/export?t=INSERISCI_QUI_IL_LINK_PEPPINO"
        }
        
        self.ospiti = []
        self.prenotazioni = []
        self.prenotazioni_booking = []
        
        self._carica_dati()

    def _carica_dati(self):
        # 1. Caricamento Ospiti
        if os.path.exists(self.FILE_OSPITI):
            try:
                with open(self.FILE_OSPITI, "r", encoding="utf-8") as f:
                    dati = json.load(f)
                    for o in dati:
                        self.ospiti.append(Ospite(o['id'], o['nome'], o['cognome'], o['luogo_nascita'], o['data_nascita']))
            except Exception:
                pass
                
        if not self.ospiti:
            storico_ospiti = [
                (1, "bruno", "balestrieri", "N.D.", ""), (2, "marcela", "halamikova palkova", "N.D.", ""),
                (3, "claudia", "loiodice", "N.D.", ""), (21, "PASQUAE", "MEMOLA", "Terlizzi", "04/11/1973"), 
                (22, "ALESSANDRO", "ULGHARAITA", "Torre del Greco", "15/08/1973")
            ]
            for id_o, n, c, ln, dn in storico_ospiti:
                self.ospiti.append(Ospite(id_o, n, c, ln, dn))
            self._salva_ospiti()

        # 2. Caricamento Prenotazioni
        if os.path.exists(self.FILE_PRENOTAZIONI):
            try:
                with open(self.FILE_PRENOTAZIONI, "r", encoding="utf-8") as f:
                    dati = json.load(f)
                    for p in dati:
                        ospite_sel = next((o for o in self.ospiti if o.id == p['ospite_id']), None)
                        stanza_sel = next((s for s in self.stanze if s.nome == p['stanza_nome']), None)
                        if ospite_sel and stanza_sel:
                            cin = datetime.strptime(p['check_in'], "%Y-%m-%d").date()
                            cout = datetime.strptime(p['check_out'], "%Y-%m-%d").date()
                            num_o = p.get('numero_ospiti', 1)
                            colaz = p.get('colazione', False)
                            self.prenotazioni.append(Prenotazione(ospite_sel, stanza_sel, cin, cout, num_o, colaz, "Manuale"))
            except Exception:
                pass

    def _salva_ospiti(self):
        dati = [{'id': o.id, 'nome': o.nome, 'cognome': o.cognome, 'luogo_nascita': o.luogo_nascita, 'data_nascita': str(o.data_nascita)} for o in self.ospiti]
        with open(self.FILE_OSPITI, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=4)

    def _salva_prenotazioni(self):
        dati = [{
            'ospite_id': p.ospite.id, 
            'stanza_nome': p.stanza.nome, 
            'check_in': str(p.check_in), 
            'check_out': str(p.check_out),
            'numero_ospiti': p.numero_ospiti,
            'colazione': p.colazione
        } for p in self.prenotazioni if p.sorgente == "Manuale"]
        with open(self.FILE_PRENOTAZIONI, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=4)

    def aggiungi_ospite(self, nome, cognome, luogo_nascita, data_nascita):
        nuovo_id = max([o.id for o in self.ospiti], default=0) + 1
        nuovo_ospite = Ospite(nuovo_id, nome, cognome, luogo_nascita, data_nascita)
        self.ospiti.append(nuovo_ospite)
        self._salva_ospiti()
        return nuovo_ospite

    def aggiungi_prenotazione(self, ospite, stanza, check_in, check_out, numero_ospiti, colazione):
        self.prenotazioni.append(Prenotazione(ospite, stanza, check_in, check_out, numero_ospiti, colazione, "Manuale"))
        self._salva_prenotazioni()

    def elimina_prenotazione(self, index):
        if 0 <= index < len(self.prenotazioni):
            self.prenotazioni.pop(index)
            self._salva_prenotazioni()

    def sincronizza_booking(self):
        self.prenotazioni_booking = []
        ospite_fittizio = Ospite(0, "Cliente", "Booking.com", "Online", "2000-01-01")
        
        for nome_casa, url in self.URL_ICAL_BOOKING.items():
            if not url or "INSERISCI_QUI" in url:
                continue
            try:
                risposta = requests.get(url, timeout=10)
                if risposta.status_code == 200:
                    cal = Calendar.from_ical(risposta.text)
                    stanza_sel = next((s for s in self.stanze if s.nome == nome_casa), None)
                    if stanza_sel:
                        for componente in cal.walk():
                            if componente.name == "VEVENT":
                                cin_dt = componente.get('dtstart').dt
                                cout_dt = componente.get('dtend').dt
                                cin = cin_dt.date() if isinstance(cin_dt, datetime) else cin_dt
                                cout = cout_dt.date() if isinstance(cout_dt, datetime) else cout_dt
                                # Nota: iCal di Booking non include nativamente i dettagli colazione/persone in modo pulito, assumiamo default
                                self.prenotazioni_booking.append(Prenotazione(ospite_fittizio, stanza_sel, cin, cout, 2, False, "Booking"))
            except Exception as e:
                st.sidebar.error(f"Errore {nome_casa}: {e}")

    def tutte_le_prenotazioni(self):
        return self.prenotazioni + self.prenotazioni_booking

    def elenco_case_disponibili(self, check_in, check_out, ignora_idx=None):
        case_occupate = set()
        for idx, p in enumerate(self.prenotazioni):
            if ignora_idx is not None and idx == ignora_idx: continue
            if not (check_out <= p.check_in or check_in >= p.check_out): case_occupate.add(p.stanza.nome)
        for p in self.prenotazioni_booking:
            if not (check_out <= p.check_in or check_in >= p.check_out): case_occupate.add(p.stanza.nome)
        return [c for c in self.ELENCO_CASE if c not in case_occupate]

# --- INIZIALIZZAZIONE ---
if 'g' not in st.session_state:
    st.session_state.g = GestionaleBnb()
    st.session_state.g.sincronizza_booking()
g = st.session_state.g

# --- INTERFACCIA UTENTE ---
st.sidebar.title("🏨 Menu Gestionale")
menu = st.sidebar.radio("Vai a:", ["Tabellone Disponibilità", "Gestione Prenotazioni", "Anagrafica Ospiti", "Elenco Case"])

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Forza Sincronizzazione", type="primary"):
    with st.spinner("Scaricamento calendari..."):
        g.sincronizza_booking()
    st.sidebar.success("Sincronizzazione completata!")
    st.rerun()

# --- SEZIONE: TABELLONE ---
if menu == "Tabellone Disponibilità":
    st.header("📅 Tabellone Occupazione Case")
    st.caption("Legenda: 🥐 = Colazione Inclusa | 👥 = Numero Ospiti")
    col1, col2 = st.columns(2)
    with col1: data_inizio = st.date_input("Data inizio visualizzazione", date.today())
    with col2: giorni_mostrati = st.slider("Numero di giorni da mostrare", 7, 30, 15)
        
    date_tabella = [data_inizio + timedelta(days=i) for i in range(giorni_mostrati)]
    matrice_dati = []
    for casa in g.ELENCO_CASE:
        riga = {"Casa": casa}
        for d in date_tabella:
            stato = "🟢 Libera"
            for p in g.tutte_le_prenotazioni():
                if p.stanza.nome == casa and p.check_in <= d < p.check_out:
                    if p.sorgente == "Booking":
                        stato = "🌐 Booking.com"
                    else:
                        col_icon = "🥐" if p.colazione else "❌"
                        stato = f"🔴 {p.ospite.cognome.upper()} ({p.numero_ospiti}👥 - Colaz: {col_icon})"
                    break
            riga[d.strftime("%d/%m")] = stato
        matrice_dati.append(riga)
    st.dataframe(pd.DataFrame(matrice_dati).set_index("Casa"), use_container_width=True)

# --- SEZIONE: PRENOTAZIONI ---
elif menu == "Gestione Prenotazioni":
    st.header("📝 Gestione delle Prenotazioni Locali")
    tab1, tab2 = st.tabs(["➕ Nuova Prenotazione Manuale", "✏️ Modifica / Elimina Prenotazione"])
    
    with tab1:
        opzioni_ospiti = {f"{o.nome} {o.cognome} (ID: {o.id})": o for o in g.ospiti}
        ospite_scelto = st.selectbox("Seleziona Ospite", list(opzioni_ospiti.keys()))
        
        c1, c2 = st.columns(2)
        with c1: data_in = st.date_input("Data di Check-in", date.today())
        with c2: data_out = st.date_input("Data di Check-out", date.today() + timedelta(days=1))
        
        # NUOVI CAMPI RICHIESTI
        c3, c4 = st.columns(2)
        with c3:
            num_persone = st.number_input("Numero di persone (Max 4)", min_value=1, max_value=4, value=2, step=1)
        with c4:
            servizio_colazione = st.checkbox("🥐 Include Colazione?", value=False)
            
        if data_in >= data_out: 
            st.error("Il check-out deve essere successivo al check-in!")
        else:
            case_disponibili = g.elenco_case_disponibili(data_in, data_out)
            if not case_disponibili: 
                st.error("Nessuna casa disponibile nelle date selezionate.")
            else:
                casa_assegnata = st.selectbox("Seleziona la struttura libera", case_disponibili)
                if st.button("Salva Prenotazione Manuale"):
                    stanza_obj = next(s for s in g.stanze if s.nome == casa_assegnata)
                    
                    # Controllo di sicurezza aggiuntivo per la capienza
                    if num_persone > stanza_obj.max_ospiti:
                        st.error(f"Errore: {casa_assegnata} può ospitare al massimo {stanza_obj.max_ospiti} persone.")
                    else:
                        g.aggiungi_prenotazione(opzioni_ospiti[ospite_scelto], stanza_obj, data_in, data_out, num_persone, servicio_colazione)
                        st.success("Prenotazione salvata con successo!")
                        st.rerun()
                        
    with tab2:
        if not g.prenotazioni: 
            st.info("Non ci sono prenotazioni manuali registrate.")
        else:
            elenco_p_testo = [f"{idx} - {p.stanza.nome}: {p.ospite.nome} {p.ospite.cognome} [{p.numero_ospiti} Pax]" for idx, p in enumerate(g.prenotazioni)]
            p_selezionata = st.selectbox("Seleziona la prenotazione da gestire", elenco_p_testo)
            pren_idx = int(p_selezionata.split(" - ")[0])
            p_da_mod = g.prenotazioni[pren_idx]
            
            col_mod1, col_mod2 = st.columns(2)
            with col_mod1:
                if st.button("❌ Elimina Prenotazione"):
                    g.elimina_prenotazione(pren_idx)
                    st.success("Prenotazione rimossa.")
                    st.rerun()
            with col_mod2:
                c_in = st.date_input("Cambia Check-in", p_da_mod.check_in)
                c_out = st.date_input("Cambia Check-out", p_da_mod.check_out)
                m_persone = st.number_input("Cambia Numero Persone", min_value=1, max_value=4, value=int(p_da_mod.numero_ospiti))
                m_colazione = st.checkbox("Cambia Opzione Colazione", value=bool(p_da_mod.colazione))
                
                casa_attuale = p_da_mod.stanza.nome
                if c_in >= c_out: 
                    st.error("Il check-out deve essere successivo al check-in!")
                else:
                    case_libere = g.elenco_case_disponibili(c_in, c_out, ignora_idx=pren_idx)
                    if casa_attuale not in case_libere: case_libere.append(casa_attuale)
                    case_libere.sort()
                    casa_scelta = st.selectbox("Cambia Casa", case_libere, index=case_libere.index(casa_attuale))
                    
                    if st.button("Aggiorna Prenotazione"):
                        p_da_mod.check_in, p_da_mod.check_out = c_in, c_out
                        p_da_mod.numero_ospiti = m_persone
                        p_da_mod.colazione = m_colazione
                        p_da_mod.stanza = next(s for s in g.stanze if s.nome == casa_scelta)
                        g._salva_prenotazioni()
                        st.success("Modifiche salvate!")
                        st.rerun()

# --- SEZIONI RESTANTI (ANAGRAFICA & CASE) ---
elif menu == "Anagrafica Ospiti":
    st.header("👥 Anagrafica Ospiti (Schedine Alloggiati)")
    tab_o1, tab_o2 = st.tabs(["➕ Registra Nuovo Ospite", "📋 Elenco Clienti Salvati"])
    with tab_o1:
        with st.form("form_ospite"):
            n, c, luogo_n = st.text_input("Nome"), st.text_input("Cognome"), st.text_input("Luogo di Nascita")
            data_n_input = st.text_input("Data di Nascita o Info")
            if st.form_submit_button("Salva Ospite"):
                if n and c:
                    g.aggiungi_ospite(n, c, luogo_n if luogo_n else "N.D.", data_n_input if data_n_input else "N.D.")
                    st.success(f"Ospite {n} {c} registrato!")
                    st.rerun()
                else: st.error("Nome e Cognome obbligatori.")
    with tab_o2:
        tabella_ospiti = [{"ID": o.id, "Cognome": o.cognome, "Nome": o.nome, "Luogo di Nascita": o.luogo_nascita, "Data di Nascita / Info": o.data_nascita} for o in g.ospiti]
        st.dataframe(pd.DataFrame(tabella_ospiti), use_container_width=True, hide_index=True)

elif menu == "Elenco Case":
    st.header("🏠 Elenco delle strutture gestite")
    st.table(pd.DataFrame([{"Struttura": s.nome, "Capienza Massima": f"{s.max_ospiti} Persone", "Servizio Colazione Gestito": "Sì"} for s in g.stanze]))
