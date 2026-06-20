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
        self.data_nascita = data_nascita  # Stringa o datetime.date

class Stanza:
    def __init__(self, nome):
        self.nome = nome

class Prenotazione:
    def __init__(self, ospite: Ospite, stanza: Stanza, check_in: date, check_out: date, sorgente="Manuale"):
        self.ospite = ospite
        self.stanza = stanza
        self.check_in = check_in
        self.check_out = check_out
        self.sorgente = sorgente  # "Manuale" o "Booking"

class GestionaleBnb:
    def __init__(self):
        self.FILE_OSPITI = "ospiti.json"
        self.FILE_PRENOTAZIONI = "prenotazioni.json"
        
        self.ELENCO_CASE = ["Casa Mariateresa", "Casa Antonetta", "Casa Peppino"]
        self.stanze = [Stanza(c) for c in self.ELENCO_CASE]
        
        # LINK ICAL DI BOOKING.COM (Inserisci qui i tuoi link reali racchiusi tra virgolette)
        self.URL_ICAL_BOOKING = {
            "Casa Mariateresa": "https://ical.booking.com/v1/export?t=456404a9-4c7e-4b8c-aaf6-a3be7d50105d",
            "Casa Antonetta": "https://ical.booking.com/v1/export?t=b5998ab5-6b80-4574-bbae-91543acbbf08",
            "Casa Peppino": "https://ical.booking.com/v1/export?t=94aed5b5-4871-444d-89bb-95bf736eebce"
        }
        
        self.ospiti = []
        self.prenotazioni = []
        self.prenotazioni_booking = []  # Sincronizzate temporaneamente in memoria
        
        self._carica_dati()

    def _carica_dati(self):
        # Carica Ospiti
        if os.path.exists(self.FILE_OSPITI):
            try:
                with open(self.FILE_OSPITI, "r", encoding="utf-8") as f:
                    dati = json.load(f)
                    for o in dati:
                        self.ospiti.append(Ospite(o['id'], o['nome'], o['cognome'], o['luogo_nascita'], o['data_nascita']))
            except Exception:
                self.ospiti = []
        
        # Carica Prenotazioni Locali
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
                            self.prenotazioni.append(Prenotazione(ospite_sel, stanza_sel, cin, cout, "Manuale"))
            except Exception:
                self.prenotazioni = []

    def _salva_ospiti(self):
        dati = []
        for o in self.ospiti:
            dati.append({'id': o.id, 'nome': o.nome, 'cognome': o.cognome, 'luogo_nascita': o.luogo_nascita, 'data_nascita': str(o.data_nascita)})
        with open(self.FILE_OSPITI, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=4)

    def _salva_prenotazioni(self):
        dati = []
        for p in self.prenotazioni:
            if p.sorgente == "Manuale":
                dati.append({'ospite_id': p.ospite.id, 'stanza_nome': p.stanza.nome, 'check_in': str(p.check_in), 'check_out': str(p.check_out)})
        with open(self.FILE_PRENOTAZIONI, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=4)

    def aggiungi_ospite(self, nome, cognome, luogo_nascita, data_nascita):
        nuovo_id = max([o.id for o in self.ospiti], default=0) + 1
        nuovo_ospite = Ospite(nuovo_id, nome, cognome, luogo_nascita, data_nascita)
        self.ospiti.append(nuovo_ospite)
        self._salva_ospiti()
        return nuovo_ospite

    def aggiungi_prenotazione(self, ospite, stanza, check_in, check_out):
        nuova_p = Prenotazione(ospite, stanza, check_in, check_out, "Manuale")
        self.prenotazioni.append(nuova_p)
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
                                
                                if isinstance(cin_dt, datetime): cin = cin_dt.date()
                                else: cin = cin_dt
                                if isinstance(cout_dt, datetime): cout = cout_dt.date()
                                else: cout = cout_dt
                                
                                self.prenotazioni_booking.append(Prenotazione(ospite_fittizio, stanza_sel, cin, cout, "Booking"))
            except Exception as e:
                st.sidebar.error(f"Errore sincronizzazione {nome_casa}: {e}")

    def tutte_le_prenotazioni(self):
        return self.prenotazioni + self.prenotazioni_booking

    def elenco_case_disponibili(self, check_in, check_out, ignora_idx=None):
        case_occupate = set()
        # Controllo prenotazioni manuali
        for idx, p in enumerate(self.prenotazioni):
            if ignora_idx is not None and idx == ignora_idx:
                continue
            if not (check_out <= p.check_in or check_in >= p.check_out):
                case_occupate.add(p.stanza.nome)
        # Controllo prenotazioni Booking
        for p in self.prenotazioni_booking:
            if not (check_out <= p.check_in or check_in >= p.check_out):
                case_occupate.add(p.stanza.nome)
                
        return [c for c in self.ELENCO_CASE if c not in case_occupate]

# --- INIZIALIZZAZIONE ---
if 'g' not in st.session_state:
    st.session_state.g = GestionaleBnb()
g = st.session_state.g

# --- INTERFACCIA UTENTE (SIDEBAR) ---
st.sidebar.title("🏨 Menu Gestionale")
menu = st.sidebar.radio("Vai a:", ["Tabellone Disponibilità", "Gestione Prenotazioni", "Anagrafica Ospiti", "Elenco Case"])

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Sincronizza Canali Esterni", type="primary"):
    with st.spinner("Scaricamento calendari da Booking.com..."):
        g.sincronizza_booking()
    st.sidebar.success("Sincronizzazione completata!")

# --- SEZIONE: TABELLONE DISPONIBILITÀ ---
if menu == "Tabellone Disponibilità":
    st.header("📅 Tabellone Occupazione Case")
    
    col1, col2 = st.columns(2)
    with col1:
        data_inizio = st.date_input("Data inizio visualizzazione", date.today())
    with col2:
        giorni_mostrati = st.slider("Numero di giorni da mostrare", 7, 30, 15)
        
    date_tabella = [data_inizio + timedelta(days=i) for i in range(giorni_mostrati)]
    
    matrice_dati = []
    for casa in g.ELENCO_CASE:
        riga = {"Casa": casa}
        for d in date_tabella:
            stato = "🟢 Libera"
            for p in g.tutte_le_prenotazioni():
                if p.stanza.nome == casa and p.check_in <= d < p.check_out:
                    if p.sorgente == "Booking":
                        stato = "🌐 Bloccato da Booking.com"
                    else:
                        stato = f"🔴 {p.ospite.nome} {p.ospite.cognome}"
                    break
            riga[d.strftime("%d/%m")] = stato
        matrice_dati.append(riga)
        
    df_tabellone = pd.DataFrame(matrice_dati)
    st.dataframe(df_tabellone.set_index("Casa"), use_container_width=True)

# --- SEZIONE: GESTIONE PRENOTAZIONI ---
elif menu == "Gestione Prenotazioni":
    st.header("📝 Gestione delle Prenotazioni Locali")
    
    tab1, tab2 = st.tabs(["➕ Nuova Prenotazione Manuale", "✏️ Modifica / Elimina Prenotazione"])
    
    with tab1:
        if not g.ospiti:
            st.warning("Per favore, registra almeno un ospite nell'Anagrafica prima di inserire una prenotazione.")
        else:
            st.subheader("Inserisci Prenotazione Telefonica o Diretta")
            opzioni_ospiti = {f"{o.nome} {o.cognome} (ID: {o.id})": o for o in g.ospiti}
            ospite_scelto = st.selectbox("Seleziona Ospite", list(opzioni_ospiti.keys()))
            
            c1, c2 = st.columns(2)
            with c1:
                data_in = st.date_input("Data di Check-in", date.today())
            with c2:
                data_out = st.date_input("Data di Check-out", date.today() + timedelta(days=1))
                
            if data_in >= data_out:
                st.error("Errore: Il check-out deve essere successivo al check-in!")
            else:
                case_disponibili = g.elenco_case_disponibili(data_in, data_out)
                if not case_disponibili:
                    st.error("Nessuna casa disponibile nelle date selezionate (controllo incrociato locale + Booking attivo).")
                else:
                    casa_assegnata = st.selectbox("Seleziona la struttura libera", case_disponibili)
                    if st.button("Salva Prenotazione Manuale"):
                        stanza_obj = next(s for s in g.stanze if s.nome == casa_assegnata)
                        g.aggiungi_prenotazione(opzioni_ospiti[ospite_scelto], stanza_obj, data_in, data_out)
                        st.success("Prenotazione salvata sul gestionale!")
                        st.rerun()
                        
    with tab2:
        st.subheader("Modifica le prenotazioni registrate a mano")
        if not g.prenotazioni:
            st.info("Non ci sono prenotazioni manuali registrate.")
        else:
            elenco_p_testo = []
            for idx, p in enumerate(g.prenotazioni):
                elenco_p_testo.append(f"{idx} - {p.stanza.nome}: {p.ospite.nome} {p.ospite.cognome} ({p.check_in} al {p.check_out})")
                
            p_selezionata = st.selectbox("Seleziona la prenotazione da gestire", elenco_p_testo)
            pren_idx = int(p_selezionata.split(" - ")[0])
            p_da_mod = g.prenotazioni[pren_idx]
            
            col_mod1, col_mod2 = st.columns(2)
            with col_mod1:
                if st.button("❌ Elimina Prenotazione", type="secondary"):
                    g.elimina_prenotazione(pren_idx)
                    st.success("Prenotazione rimossa.")
                    st.rerun()
            with col_mod2:
                st.markdown("**Modifica Date o Alloggio:**")
                c_in = st.date_input("Cambia Check-in", p_da_mod.check_in)
                c_out = st.date_input("Cambia Check-out", p_da_mod.check_out)
                casa_attuale = p_da_mod.stanza.nome
                
                if c_in >= c_out:
                    st.error("Il check-out deve essere successivo al check-in!")
                else:
                    # CORRETTO: ignora_idx al posto di idx_ignora
                    case_libere = g.elenco_case_disponibili(c_in, c_out, ignora_idx=pren_idx)
                    if casa_attuale not in case_libere: 
                        case_libere.append(casa_attuale)
                    case_libere.sort()
                    
                    idx_casa_corr = case_libere.index(casa_attuale)
                    casa_scelta = st.selectbox("Cambia Casa", case_libere, index=idx_casa_corr, key="mod_p_casa")
                    
                    if st.button("Aggiorna Prenotazione"):
                        p_da_mod.check_in = c_in
                        p_da_mod.check_out = c_out
                        p_da_mod.stanza = next(s for s in g.stanze if s.nome == casa_scelta)
                        g._salva_prenotazioni()
                        st.success("Modifiche salvate correttamente!")
                        st.rerun()

# --- SEZIONE: ANAGRAFICA OSPITI ---
elif menu == "Anagrafica Ospiti":
    st.header("👥 Anagrafica Ospiti (Schedine Alloggiati)")
    
    tab_o1, tab_o2 = st.tabs(["➕ Registra Nuovo Ospite", "📋 Elenco Clienti Salvati"])
    
    with tab_o1:
        st.subheader("Inserisci i dati personali dell'ospite principale")
        with st.form("form_ospite"):
            n = st.text_input("Nome")
            c = st.text_input("Cognome")
            luogo_n = st.text_input("Luogo di Nascita (Comune o Stato estero)")
            data_n_input = st.text_input("Data di Nascita (formato: GG/MM/AAAA)", placeholder="es. 24/07/1985")
            
            invia_o = st.form_submit_button("Salva Ospite in Archivio")
            if invia_o:
                if n and c and luogo_n and data_n_input:
                    g.aggiungi_ospite(n, c, luogo_n, data_n_input)
                    st.success(f"Ospite {n} {c} registrato con successo!")
                else:
                    st.error("Tutti i campi sono obbligatori per la successiva schedina alloggiati.")
                    
    with tab_o2:
        st.subheader("Archivio Clienti")
        if not g.ospiti:
            st.info("Nessun ospite registrato in memoria.")
        else:
            tabella_ospiti = []
            for o in g.ospiti:
                tabella_ospiti.append({
                    "ID": o.id,
                    "Cognome": o.cognome,
                    "Nome": o.nome,
                    "Luogo di Nascita": o.luogo_nascita,
                    "Data di Nascita": o.data_nascita
                })
            st.dataframe(pd.DataFrame(tabella_ospiti), use_container_width=True, hide_index=True)

# --- SEZIONE: ELENCO CASE ---
elif menu == "Elenco Case":
    st.header("🏠 Elenco delle strutture gestite")
    st.success("Sincronizzazione iCal attiva con i canali ufficiali di Booking.com.")
    st.table(pd.DataFrame([{"Casa": k, "Stato Collegamento": "🟢 Connesso / Configurato"} for k in g.URL_ICAL_BOOKING.keys()]))
