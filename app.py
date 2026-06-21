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
        self.max_ospiti = max_ospiti

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
        if os.path.exists(self.FILE_OSPITI):
            try:
                with open(self.FILE_OSPITI, "r", encoding="utf-8") as f:
                    dati = json.load(f)
                    for o in dati:
                        self.ospiti.append(Ospite(o['id'], o['nome'], o['cognome'], o['luogo_nascita'], o['data_nascita']))
            except Exception: pass
                
        if not self.ospiti:
            storico_ospiti = [
                (1, "bruno", "balestrieri", "N.D.", ""), (2, "marcela", "halamikova palkova", "N.D.", ""),
                (3, "claudia", "loiodice", "N.D.", ""), (21, "PASQUAE", "MEMOLA", "Terlizzi", "04/11/1973"), 
                (22, "ALESSANDRO", "ULGHARAITA", "Torre del Greco", "15/08/1973")
            ]
            for id_o, n, c, ln, dn in storico_ospiti:
                self.ospiti.append(Ospite(id_o, n, c, ln, dn))
            self._salva_ospiti()

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
            except Exception: pass

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

    def aggiungi_prenotazione(self, ospite, stanza, check_in, check_out, numero_ospiti, colazione):
        self.prenotazioni.append(Prenotazione(ospite, stanza, check_in, check_out, numero_ospiti, colazione, "Manuale"))
        self._salva_prenotazioni()

    def elimina_prenotazione_obj(self, prenotazione_obj):
        if prenotazione_obj in self.prenotazioni:
            self.prenotazioni.remove(prenotazione_obj)
            self._salva_prenotazioni()

    def sincronizza_booking(self):
        self.prenotazioni_booking = []
        ospite_fittizio = Ospite(0, "Cliente", "Booking.com", "Online", "2000-01-01")
        for nome_casa, url in self.URL_ICAL_BOOKING.items():
            if not url or "INSERISCI_QUI" in url: continue
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
                                self.prenotazioni_booking.append(Prenotazione(ospite_fittizio, stanza_sel, cin, cout, 2, False, "Booking"))
            except Exception: pass

    def tutte_le_prenotazioni(self):
        return self.prenotazioni + self.prenotazioni_booking

    # CORREZIONE LOGICA: Adesso esclude correttamente se stessa durante la modifica
    def elenco_case_disponibili(self, check_in, check_out, ignora_p=None):
        case_occupate = set()
        for p in self.prenotazioni:
            if ignora_p is not None and p == ignora_p: 
                continue
            # Verifica sovrapposizione date standard
            if not (check_out <= p.check_in or check_in >= p.check_out): 
                case_occupate.add(p.stanza.nome)
        for p in self.prenotazioni_booking:
            if not (check_out <= p.check_in or check_in >= p.check_out): 
                case_occupate.add(p.stanza.nome)
        return [c for c in self.ELENCO_CASE if c not in case_occupate]

# --- INIZIALIZZAZIONE ---
if 'g' not in st.session_state:
    st.session_state.g = GestionaleBnb()
    st.session_state.g.sincronizza_booking()
if 'p_da_modificare' not in st.session_state:
    st.session_state.p_da_modificare = None

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
    st.caption("Clicca su una cella rossa per modificare rapidamente quella specifica prenotazione.")
    
    col1, col2 = st.columns(2)
    with col1: data_inizio = st.date_input("Data inizio visualizzazione", date.today())
    with col2: giorni_mostrati = st.slider("Giorni da mostrare nel tabellone", 5, 15, 10)
        
    date_tabella = [data_inizio + timedelta(days=i) for i in range(giorni_mostrati)]
    
    for casa in g.ELENCO_CASE:
        st.markdown(f"### 🏠 {casa}")
        col_giorni = st.columns(giorni_mostrati)
        
        for i, d in enumerate(date_tabella):
            with col_giorni[i]:
                st.markdown(f"<p style='text-align: center; margin-bottom: 2px; font-weight: bold; color:#555;'>{d.strftime('%d/%m')}</p>", unsafe_allow_html=True)
                
                # Identifica se il giorno specifico ricade in qualche prenotazione
                trovata = None
                for p in g.tutte_le_prenotazioni():
                    if p.stanza.nome == casa and p.check_in <= d < p.check_out:
                        trovata = p
                        break
                
                if trovata:
                    if trovata.sorgente == "Booking":
                        st.button("🌐 iCal", key=f"btn_{casa}_{d}", use_container_width=True, disabled=True, help="Bloccato da Booking.com")
                    else:
                        col_icon = "🥐" if trovata.colazione else "❌"
                        label = f"🔴 {trovata.ospite.cognome[:7].upper()}\n{trovata.numero_ospiti}👥 {col_icon}"
                        
                        # Al click, passiamo l'oggetto esatto alla sessione per evitare bug di indice
                        if st.button(label, key=f"btn_{casa}_{d}", use_container_width=True):
                            st.session_state.p_da_modificare = trovata
                            st.rerun()
                else:
                    st.button("🟢 Libera", key=f"btn_{casa}_{d}", use_container_width=True, disabled=True)
        st.markdown("---")

    # PANNELLO RAPIDO SOTTO IL TABELLONE
    if st.session_state.p_da_modificare:
        p_mod = st.session_state.p_da_modificare
        
        # Doppia sicurezza: verifichiamo che la prenotazione esista ancora nel sistema locale
        if p_mod in g.prenotazioni:
            st.markdown(f"## ⚙️ Modifica Prenotazione: {p_mod.ospite.nome.upper()} {p_mod.ospite.cognome.upper()}")
            
            with st.form("form_modifica_rapida"):
                col_in1, col_in2, col_in3, col_in4 = st.columns(4)
                with col_in1:
                    nuovo_cin = st.date_input("Check-in", p_mod.check_in)
                with col_in2:
                    nuovo_cout = st.date_input("Check-out", p_mod.check_out)
                with col_in3:
                    nuovo_pax = st.number_input("Ospiti (Max 4)", min_value=1, max_value=4, value=int(p_mod.numero_ospiti))
                with col_in4:
                    st.markdown("<br>", unsafe_allow_html=True)
                    nuova_colaz = st.checkbox("🥐 Colazione Inclusa", value=bool(p_mod.colazione))
                
                # Calcola le case libere escludendo lo stato attuale di questa prenotazione per non generare falsi blocchi
                case_libere = g.elenco_case_disponibili(nuovo_cin, nuovo_cout, ignora_p=p_mod)
                if p_mod.stanza.nome not in case_libere:
                    case_libere.append(p_mod.stanza.nome)
                case_libere.sort()
                
                nuova_casa = st.selectbox("Sposta Struttura", case_libere, index=case_libere.index(p_mod.stanza.nome))
                
                c_btn1, c_btn2, c_btn3 = st.columns(3)
                with c_btn1:
                    submit_save = st.form_submit_button("💾 Salva Modifiche", type="primary")
                with c_btn2:
                    submit_del = st.form_submit_button("❌ Elimina Prenotazione")
                with c_btn3:
                    submit_cancel = st.form_submit_button("Annulla")
                
                if submit_save:
                    if nuovo_cin >= nuovo_cout:
                        st.error("Errore: Il check-out deve essere successivo al check-in.")
                    else:
                        p_mod.check_in = nuovo_cin
                        p_mod.check_out = nuovo_cout
                        p_mod.numero_ospiti = nuovo_pax
                        p_mod.colazione = nuova_colaz
                        p_mod.stanza = next(s for s in g.stanze if s.nome == nuova_casa)
                        g._salva_prenotazioni()
                        st.session_state.p_da_modificare = None
                        st.toast("Modifiche salvate con successo!")
                        st.rerun()
                        
                elif submit_del:
                    g.elimina_prenotazione_obj(p_mod)
                    st.session_state.p_da_modificare = None
                    st.toast("Prenotazione eliminata.")
                    st.rerun()
                    
                elif submit_cancel:
                    st.session_state.p_da_modificare = None
                    st.rerun()
        else:
            st.session_state.p_da_modificare = None

# --- SEZIONE: NUOVA PRENOTAZIONE MANUALE ---
elif menu == "Gestione Prenotazioni":
    st.header("📝 Nuova Prenotazione Manuale")
    if not g.ospiti:
        st.warning("Registra prima un ospite nell'Anagrafica!")
    else:
        opzioni_ospiti = {f"{o.nome.upper()} {o.cognome.upper()} (ID: {o.id})": o for o in g.ospiti}
        ospite_scelto = st.selectbox("Seleziona l'Ospite", list(opzioni_ospiti.keys()))
        
        c1, c2 = st.columns(2)
        with c1: data_in = st.date_input("Data Check-in", date.today())
        with c2: data_out = st.date_input("Data Check-out", date.today() + timedelta(days=1))
        
        c3, c4 = st.columns(2)
        with c3: num_persone = st.number_input("Numero di persone (Max 4)", min_value=1, max_value=4, value=2)
        with c4: servicio_colazione = st.checkbox("🥐 Include Colazione?", value=False)
            
        if data_in >= data_out: 
            st.error("Il check-out deve essere successivo al check-in!")
        else:
            case_disponibili = g.elenco_case_disponibili(data_in, data_out)
            if not case_disponibili: 
                st.error("Nessuna struttura disponibile in queste date.")
            else:
                casa_assegnata = st.selectbox("Seleziona la casa da assegnare", case_disponibili)
                if st.button("Conferma e Salva Prenotazione", type="primary"):
                    stanza_obj = next(s for s in g.stanze if s.nome == casa_assegnata)
                    g.aggiungi_prenotazione(opzioni_ospiti[ospite_scelto], stanza_obj, data_in, data_out, num_persone, servicio_colazione)
                    st.success("Prenotazione registrata!")
                    st.rerun()

# --- ANAGRAFICA OSPITI ---
elif menu == "Anagrafica Ospiti":
    st.header("👥 Anagrafica Ospiti")
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
        tabella_ospiti = [{"ID": o.id, "Cognome": o.cognome.upper(), "Nome": o.nome.upper(), "Luogo di Nascita": o.luogo_nascita, "Data di Nascita / Info": o.data_nascita} for o in g.ospiti]
        st.dataframe(pd.DataFrame(tabella_ospiti), use_container_width=True, hide_index=True)

# --- ELENCO CASE ---
elif menu == "Elenco Case":
    st.header("🏠 Elenco delle strutture gestite")
    st.table(pd.DataFrame([{"Struttura": s.nome, "Capienza Massima": f"{s.max_ospiti} Persone", "Servizio Colazione Gestito": "Sì"} for s in g.stanze]))
