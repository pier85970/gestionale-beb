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
    def __init__(self, nome):
        self.nome = nome

class Prenotazione:
    def __init__(self, ospite: Ospite, stanza: Stanza, check_in: date, check_out: date, sorgente="Manuale"):
        self.ospite = ospite
        self.stanza = stanza
        self.check_in = check_in
        self.check_out = check_out
        self.sorgente = sorgente

class GestionaleBnb:
    def __init__(self):
        self.FILE_OSPITI = "ospiti.json"
        self.FILE_PRENOTAZIONI = "prenotazioni.json"
        
        self.ELENCO_CASE = ["Casa Mariateresa", "Casa Antonetta", "Casa Peppino"]
        self.stanze = [Stanza(c) for c in self.ELENCO_CASE]
        
        # LINK ICAL DI BOOKING.COM (Assicurati di inserire i link reali completi!)
        self.URL_ICAL_BOOKING = {
            "Casa Mariateresa": "https://ical.booking.com/v1/export?t=689502a9-31d5-49fb-bd9c-957a025a0d7a",
            "Casa Antonetta": "https://ical.booking.com/v1/export?t=45ea0953-e271-4120-b36b-62882e1e1f12",
            "Casa Peppino": "https://ical.booking.com/v1/export?t=6bbe16be-276d-41bd-89cd-aaad238d0d65"
        }
        
        self.ospiti = []
        self.prenotazioni = []
        self.prenotazioni_booking = []
        
        self._carica_dati()

    def _carica_dati(self):
        # 1. Caricamento o Inizializzazione Storico Ospiti
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
                (3, "claudia", "loiodice", "N.D.", ""), (4, "ALESSANDRA", "GHERSI", "N.D.", ""),
                (5, "CHIARA", "PELLEGRINO", "N.D.", ""), (6, "MARCO", "GIACOBAZZI", "N.D.", ""),
                (7, "EMANUELE", "SANTINI", "N.D.", ""), (8, "PAOLA", "PATRUNO", "N.D.", ""),
                (9, "PIA", "PAROLINI", "N.D.", ""), (10, "ANTONINO", "NIFOSI'", "N.D.", ""),
                (11, "FABRIZION PAOLO SALVATORE", "SANDINU", "N.D.", ""), (12, "MARIE", "PONS", "N.D.", ""),
                (13, "CARLO", "CASTANO", "N.D.", ""), (14, "KAMILLA", "BOLTUC", "N.D.", ""),
                (15, "ROBERTO", "QUARISA", "N.D.", "Tel: 3460913066"), (16, "SILVANA", "SDAU", "N.D.", "Tel: 3403123776"),
                (17, "VALERIO", "ROCCHETTI", "N.D.", "Tel: 3485627555"), (18, "pasquale", "cocatrix", "N.D.", "Tel: 33 699187901"),
                (19, "EMIDIO", "GROTTOLA", "N.D.", "Tel: 3282796232"), (20, "ROBERTO", "QUARISA", "N.D.", "Tel: 3460913066"),
                (21, "PASQUAE", "MEMOLA", "Terlizzi", "04/11/1973"), (22, "ALESSANDRO", "ULGHARAITA", "Torre del Greco", "15/08/1973")
            ]
            for id_o, n, c, ln, dn in storico_ospiti:
                self.ospiti.append(Ospite(id_o, n, c, ln, dn))
            self._salva_ospiti()

        # 2. Caricamento o Inizializzazione Storico Prenotazioni Locali
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
                pass
                
        if not self.prenotazioni:
            storico_prenotazioni = [
                (14, "Casa Mariateresa", "2026-05-22", "2026-05-25"), (15, "Casa Mariateresa", "2026-08-28", "2026-08-30"),
                (15, "Casa Peppino", "2026-08-28", "2026-08-30"), (16, "Casa Antonetta", "2026-08-28", "2026-08-30"),
                (17, "Casa Peppino", "2026-05-14", "2026-05-15"), (18, "Casa Mariateresa", "2026-05-31", "2026-06-03"),
                (19, "Casa Mariateresa", "2026-05-22", "2026-05-25"), (20, "Casa Peppino", "2026-06-17", "2026-06-20"),
                (21, "Casa Mariateresa", "2026-06-19", "2026-06-20")
            ]
            for o_id, c_nome, cin_s, cout_s in storico_prenotazioni:
                ospite_sel = next((o for o in self.ospiti if o.id == o_id), None)
                stanza_sel = next((s for s in self.stanze if s.nome == c_nome), None)
                if ospite_sel and stanza_sel:
                    cin = datetime.strptime(cin_s, "%Y-%m-%d").date()
                    cout = datetime.strptime(cout_s, "%Y-%m-%d").date()
                    self.prenotazioni.append(Prenotazione(ospite_sel, stanza_sel, cin, cout, "Manuale"))
            self._salva_prenotazioni()

    def _salva_ospiti(self):
        dati = [{'id': o.id, 'nome': o.nome, 'cognome': o.cognome, 'luogo_nascita': o.luogo_nascita, 'data_nascita': str(o.data_nascita)} for o in self.ospiti]
        with open(self.FILE_OSPITI, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=4)

    def _salva_prenotazioni(self):
        dati = [{'ospite_id': p.ospite.id, 'stanza_nome': p.stanza.nome, 'check_in': str(p.check_in), 'check_out': str(p.check_out)} for p in self.prenotazioni if p.sorgente == "Manuale"]
        with open(self.FILE_PRENOTAZIONI, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=4)

    def aggiungi_ospite(self, nome, cognome, luogo_nascita, data_nascita):
        nuovo_id = max([o.id for o in self.ospiti], default=0) + 1
        nuovo_ospite = Ospite(nuovo_id, nome, cognome, luogo_nascita, data_nascita)
        self.ospiti.append(nuovo_ospite)
        self._salva_ospiti()
        return nuovo_ospite

    def aggiungi_prenotazione(self, ospite, stanza, check_in, check_out):
        self.prenotazioni.append(Prenotazione(ospite, stanza, check_in, check_out, "Manuale"))
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
                st.sidebar.warning(f"⚠️ Link iCal mancante per {nome_casa}")
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
                                self.prenotazioni_booking.append(Prenotazione(ospite_fittizio, stanza_sel, cin, cout, "Booking"))
                else:
                    st.sidebar.error(f"❌ Errore HTTP {risposta.status_code} per {nome_casa}")
            except Exception as e:
                st.sidebar.error(f"❌ Errore connessione {nome_casa}: {e}")

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

# --- INIZIALIZZAZIONE STATO ---
if 'g' not in st.session_state:
    st.session_state.g = GestionaleBnb()
    # Eseguiamo una sincronizzazione automatica solo al primo avvio assoluto dell'app
    st.session_state.g.sincronizza_booking()
    st.session_state.sincronizzato = True

g = st.session_state.g

# --- INTERFACCIA UTENTE ---
st.sidebar.title("🏨 Menu Gestionale")
menu = st.sidebar.radio("Vai a:", ["Tabellone Disponibilità", "Gestione Prenotazioni", "Anagrafica Ospiti", "Elenco Case"])

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Forza Sincronizzazione", type="primary"):
    with st.spinner("Scaricamento calendari in corso..."):
        g.sincronizza_booking()
    st.sidebar.success("Sincronizzazione completata!")
    st.rerun() # Forza il rinfresco immediato del tabellone grafico

# --- SEZIONE: TABELLONE ---
if menu == "Tabellone Disponibilità":
    st.header("📅 Tabellone Occupazione Case")
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
                    stato = "🌐 Bloccato da Booking.com" if p.sorgente == "Booking" else f"🔴 {p.ospite.nome} {p.ospite.cognome}"
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
            
        if data_in >= data_out: st.error("Il check-out deve essere successivo al check-in!")
        else:
            case_disponibili = g.elenco_case_disponibili(data_in, data_out)
            if not case_disponibili: st.error("Nessuna casa disponibile nelle date selezionate.")
            else:
                casa_assegnata = st.selectbox("Seleziona la struttura libera", case_disponibili)
                if st.button("Salva Prenotazione Manuale"):
                    g.aggiungi_prenotazione(opzioni_ospiti[ospite_scelto], next(s for s in g.stanze if s.nome == casa_assegnata), data_in, data_out)
                    st.success("Prenotazione salvata!")
                    st.rerun()
                        
    with tab2:
        if not g.prenotazioni: st.info("Non ci sono prenotazioni manuali registrate.")
        else:
            elenco_p_testo = [f"{idx} - {p.stanza.nome}: {p.ospite.nome} {p.ospite.cognome} ({p.check_in} al {p.check_out})" for idx, p in enumerate(g.prenotazioni)]
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
                casa_attuale = p_da_mod.stanza.nome
                if c_in >= c_out: st.error("Il check-out deve essere successivo al check-in!")
                else:
                    case_libere = g.elenco_case_disponibili(c_in, c_out, ignora_idx=pren_idx)
                    if casa_attuale not in case_libere: case_libere.append(casa_attuale)
                    case_libere.sort()
                    casa_scelta = st.selectbox("Cambia Casa", case_libere, index=case_libere.index(casa_attuale))
                    if st.button("Aggiorna Prenotazione"):
                        p_da_mod.check_in, p_da_mod.check_out = c_in, c_out
                        p_da_mod.stanza = next(s for s in g.stanze if s.nome == casa_scelta)
                        g._salva_prenotazioni()
                        st.success("Modifiche salvate!")
                        st.rerun()

# --- SEZIONE: ANAGRAFICA ---
elif menu == "Anagrafica Ospiti":
    st.header("👥 Anagrafica Ospiti (Schedine Alloggiati)")
    tab_o1, tab_o2 = st.tabs(["➕ Registra Nuovo Ospite", "📋 Elenco Clienti Salvati"])
    
    with tab_o1:
        with st.form("form_ospite"):
            n, c, luogo_n = st.text_input("Nome"), st.text_input("Cognome"), st.text_input("Luogo di Nascita")
            data_n_input = st.text_input("Data di Nascita o Info (es. 24/07/1985 o numero di Telefono)")
            if st.form_submit_button("Salva Ospite"):
                if n and c:
                    g.aggiungi_ospite(n, c, luogo_n if luogo_n else "N.D.", data_n_input if data_n_input else "N.D.")
                    st.success(f"Ospite {n} {c} registrato!")
                    st.rerun()
                else: st.error("Nome e Cognome obbligatori.")
                    
    with tab_o2:
        tabella_ospiti = [{"ID": o.id, "Cognome": o.cognome, "Nome": o.nome, "Luogo di Nascita": o.luogo_nascita, "Data di Nascita / Info": o.data_nascita} for o in g.ospiti]
        st.dataframe(pd.DataFrame(tabella_ospiti), use_container_width=True, hide_index=True)

# --- SEZIONE: ELENCO CASE ---
elif menu == "Elenco Case":
    st.header("🏠 Elenco delle strutture gestite")
    st.success("Sincronizzazione iCal attiva con i canali ufficiali di Booking.com.")
    
    status_case = []
    for k, url in g.URL_ICAL_BOOKING.items():
        stato = "🟢 Connesso" if "INSERISCI_QUI" not in url else "🔴 Link Mancante"
        status_case.append({"Casa": k, "Stato Collegamento": stato})
        
    st.table(pd.DataFrame(status_case))
