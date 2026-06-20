import streamlit as st
import json
from datetime import datetime, date, timedelta
import pandas as pd
import uuid
import requests
from icalendar import Calendar

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Gestionale B&B + Booking Sync", page_icon="📒", layout="wide")

# ----------------------
# Modelli dati
# ----------------------
class Ospite:
    def __init__(self, nome: str, cognome: str, telefono: str = "", email: str = "", luogo_nascita: str = "", data_nascita: date = None, id_ospite: str = None):
        self.id = id_ospite if id_ospite else str(uuid.uuid4())[:8]
        self.nome = nome
        self.cognome = cognome
        self.telefono = telefono
        self.email = email
        self.luogo_nascita = luogo_nascita
        self.data_nascita = data_nascita  

    def display(self) -> str:
        extra = []
        if self.data_nascita: 
            extra.append(f"Nato il {self.data_nascita.strftime('%d/%m/%Y')}")
        if self.telefono: 
            extra.append(self.telefono)
        extra_str = f" ({' / '.join(extra)})" if extra else " (Nessun dato)"
        return f"{self.nome} {self.cognome}{extra_str}"

class Stanza:
    def __init__(self, nome: str, posti: int):
        self.nome = nome
        self.posti = posti

class Prenotazione:
    def __init__(self, ospite: Ospite, stanza: Stanza, check_in: date, check_out: date, sorgente: str = "Manuale"):
        self.ospite = ospite
        self.stanza = stanza  
        self.check_in = check_in
        self.check_out = check_out
        self.sorgente = sorgente # "Manuale" o "Booking.com"

# ----------------------
# Logica Gestionale con Integrazione iCal
# ----------------------
class GestionaleBnb:
    def __init__(self, file_dati: str = "dati.json"):
        self.file_dati = file_dati
        self.ospiti = []
        self.stanze = []
        self.prenotazioni = []
        self.ELENCO_CASE = ["Casa Mariateressa", "Casa Antonetta", "Casa Peppino"]
        
        # LINK ICAL DI BOOKING.COM (Sostituisci questi URL con i tuoi link reali presi dall'extranet di Booking)
        self.URL_ICAL_BOOKING = {
            "Casa Mariateressa": "https://ical.booking.com/v1/export?t=a6882451-6b55-47e3-990b-ddcc2be78ec2"
            "Casa Antonetta": "https://ical.booking.com/v1/export?t=b5998ab5-6b80-4574-bbae-91543acbbf08"
            "Casa Peppino": "https://ical.booking.com/v1/export?t=76e590db-7cb7-40fe-81e6-ab406552ea5a"
        }
        
        # Memoria temporanea per le prenotazioni importate da Booking durante la sessione
        self.prenotazioni_booking = []
        
        self._carica()
        self.sincronizza_booking() # Sincronizzazione automatica all'avvio

    def sincronizza_booking(self):
        """Scarica i calendari iCal da Booking.com e popola le prenotazioni esterne per evitare overbooking"""
        self.prenotazioni_booking = []
        ospite_booking = Ospite("Cliente", "Booking.com", "", "", "Online", None, "BOOKING_EXT")
        
        for casa, url in self.URL_ICAL_BOOKING.items():
            if "CHIAVE_ESEMPIO" in url:
                continue # Salta i link di esempio non configurati
                
            try:
                risposta = requests.get(url, timeout=10)
                if risposta.status_code == 200:
                    cal = Calendar.from_ical(risposta.text)
                    # Troviamo la stanza base (es. "Casa Mariateressa - 4 Persone") per bloccare l'intera struttura
                    stanza_obj = next((s for s in self.stanze if s.nome.startswith(casa)), None)
                    
                    if stanza_obj:
                        for componente in cal.walk('vevent'):
                            # Estrazione date check-in e check-out dall'iCal
                            c_in = componente.get('dtstart').dt
                            c_out = componente.get('dtend').dt
                            
                            # Se l'iCal restituisce datetime, convertiamo in date
                            if isinstance(c_in, datetime): c_in = c_in.date()
                            if isinstance(c_out, datetime): c_out = c_out.date()
                            
                            # Crea una prenotazione virtuale bloccante
                            self.prenotazioni_booking.append(
                                Prenotazione(ospite_booking, stanza_obj, c_in, c_out, sorgente="Booking.com")
                            )
            except Exception as e:
                print(f"Errore sincronizzazione {casa}: {e}")

    def ottieni_tutte_prenotazioni(self):
        """Unisce le prenotazioni manuali salvate e quelle in tempo reale di Booking"""
        return self.prenotazioni + self.prenotazioni_booking

    def casa_disponibile(self, nome_casa: str, check_in: date, check_out: date, ignora_idx = None) -> bool:
        # Controlliamo su TUTTE le prenotazioni (locali + Booking)
        for i, p in enumerate(self.ottieni_tutte_prenotazioni()):
            if i == ignora_idx and p.sorgente == "Manuale": 
                continue
            p_casa = p.stanza.nome.split(" - ")[0]
            if p_casa == nome_casa:
                # Formula di collisione date
                if not (check_out <= p.check_in or check_in >= p.check_out):
                    return False
        return True

    def elenco_case_disponibili(self, check_in: date, check_out: date, ignora_idx = None):
        return [casa for casa in self.ELENCO_CASE if self.casa_disponibile(casa, check_in, check_out, ignora_idx)]

    def _carica(self):
        conversione_nomi = {
            "Singola": "1 Persona", "Doppia": "2 Persone",
            "Tripla": "3 Persone", "Quadrupla": "4 Persone"
        }
        tipologies = [("1 Persona", 1), ("2 Persone", 2), ("3 Persone", 3), ("4 Persone", 4)]
        self.stanze = [Stanza(f"{c} - {t}", posti) for c in self.ELENCO_CASE for t, posti in tipologies]

        try:
            with open(self.file_dati, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.ospiti = []
            for o in data.get("ospiti", []):
                tel = o.get("telefono", o.get("telephone", ""))
                d_nas = o.get("data_nascita", "")
                dt_nas = datetime.strptime(d_nas, "%Y-%m-%d").date() if d_nas else None
                
                self.ospiti.append(Ospite(o.get("nome", ""), o.get("cognome", ""), tel, o.get("email", ""), o.get("luogo_nascita", ""), dt_nas, o.get("id")))
            
            mappa_ospiti = {o.id: o for o in self.ospiti}
            mappa_stanze = {s.nome: s for s in self.stanze}

            self.prenotazioni = []
            for p in data.get("prenotazioni", []):
                try:
                    id_p_ospite = p["ospite"]
                    o = mappa_ospiti.get(str(id_p_ospite))
                    nome_stanza = p["stanza"]
                    s = mappa_stanze.get(nome_stanza)
                    ci = datetime.strptime(p["check_in"], "%Y-%m-%d").date()
                    co = datetime.strptime(p["check_out"], "%Y-%m-%d").date()
                    
                    if o and s:
                        self.prenotazioni.append(Prenotazione(o, s, ci, co, sorgente="Manuale"))
                except: 
                    continue
            self._salva()
        except (FileNotFoundError, json.JSONDecodeError):
            self._salva()

    def _salva(self):
        data = {
            "ospiti": [
                {
                    "id": o.id, "nome": o.nome, "cognome": o.cognome, "telefono": o.telefono, 
                    "email": o.email, "luogo_nascita": o.luogo_nascita,
                    "data_nascita": o.data_nascita.strftime("%Y-%m-%d") if o.data_nascita else ""
                } for o in self.ospiti
            ],
            "prenotazioni": [
                {
                    "ospite": p.ospite.id, "stanza": p.stanza.nome, 
                    "check_in": p.check_in.strftime("%Y-%m-%d"), "check_out": p.check_out.strftime("%Y-%m-%d")
                } for p in self.prenotazioni if p.sorgente == "Manuale" # Salva solo quelle manuali
            ]
        }
        with open(self.file_dati, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

# Inizializzazione dello stato di Streamlit
if "g" not in st.session_state:
    st.session_state.g = GestionaleBnb()
g = st.session_state.g

# ----------------------
# Interfaccia Grafica Web
# ----------------------
st.title("📒 Gestionale B&B — Con Sincronizzazione Booking Channel")

# Bottone manuale in sidebar per forzare l'aggiornamento da Booking
if st.sidebar.button("🔄 Sincronizza Canali Esterni", type="primary"):
    with st.spinner("Scaricamento calendari di Booking..."):
        g.sincronizza_booking()
    st.sidebar.success("Sincronizzato!")

menu = st.sidebar.radio("Navigazione Menu", ["Prenotazioni", "Anagrafica Ospiti", "Verifica Disponibilità", "Elenco Case"])

# --- SEZIONE: PRENOTAZIONI ---
if menu == "Prenotazioni":
    st.header("📆 Registro Prenotazioni Totali")
    st.subheader("🗓️ Tabellone Occupazione Case (Incluso Booking.com)")
    
    data_inizio = date.today()
    giorni_tabellone = [data_inizio + timedelta(days=i) for i in range(15)]
    colonne_date = [d.strftime("%d/%m") for d in giorni_tabellone]
    
    matrice_dati = []
    for casa in g.ELENCO_CASE:
        riga = {"Struttura / Casa": casa}
        for d in giorni_tabellone:
            stato = "🟢 Libera"
            # Cicla su prenotazioni manuali + Booking
            for p in g.ottieni_tutte_prenotazioni():
                p_casa = p.stanza.nome.split(" - ")[0]
                if p_casa == casa and p.check_in <= d < p.check_out:
                    if p.sorgente == "Booking.com":
                        stato = "🌐 Bloccato da Booking.com"
                    else:
                        num_persone = p.stanza.nome.split(" - ")[1]
                        stato = f"🔴 {p.ospite.nome} {p.ospite.cognome} ({num_persone})"
                    break
            riga[d.strftime("%d/%m")] = stato
        matrice_dati.append(riga)
        
    df_griglia = pd.DataFrame(matrice_dati)
    
    def colora_celle(val):
        if "🔴" in str(val):
            return "background-color: #ffcccc; color: #cc0000; font-weight: bold;"
        if "🌐" in str(val):
            return "background-color: #cce5ff; color: #004085; font-weight: bold;"
        if "🟢" in str(val):
            return "background-color: #e2f0d9; color: #385723;"
        return ""
    
    df_stilizzato = df_griglia.style.map(colora_celle, subset=colonne_date)
    st.dataframe(df_stilizzato, use_container_width=True, hide_index=True)
    st.divider()
    
    # Visualizzazione tabella testuale
    anni = sorted(list({p.check_in.year for p in g.ottieni_tutte_prenotazioni()} | {date.today().year}), reverse=True)
    anno_sel = st.selectbox("Filtra elenco testuale per anno", anni)
    
    pren_filtrate = [
        p for p in g.ottieni_tutte_prenotazioni() 
        if p.check_in.year == anno_sel or p.check_out.year == anno_sel
    ]
    
    if pren_filtrate:
        tabella_dati = []
        for i, p in enumerate(pren_filtrate):
            parti = p.stanza.nome.split(" - ")
            tabella_dati.append({
                "Ospite / Blocco": f"{p.ospite.nome} {p.ospite.cognome}",
                "Casa": parti[0],
                "Provenienza": p.sorgente,
                "Check-in": p.check_in.strftime("%d/%m/%Y"),
                "Check-out": p.check_out.strftime("%d/%m/%Y")
            })
        df = pd.DataFrame(tabella_dati)
        st.dataframe(df, use_container_width=True)
    else:
        st.info(f"Nessuna prenotazione trovata per il {anno_sel}.")
        
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.expander("➕ Nuova Prenotazione Manuale"):
            if not g.ospiti:
                st.warning("Crea prima un ospite in Anagrafica!")
            else:
                ospiti_nomi = [o.display() for o in g.ospiti]
                osp_scelto_idx = st.selectbox("Seleziona Ospite", range(len(ospiti_nomi)), format_func=lambda x: ospiti_nomi[x])
                
                c_in = st.date_input("Data di Check-in", date.today(), key="new_p_in")
                c_out = st.date_input("Data di Check-out", date.today() + timedelta(days=1), key="new_p_out")
                
                if c_in >= c_out:
                    st.error("Il check-out deve essere successivo al check-in!")
                else:
                    # Questa funzione adesso scarterà anche le case occupate su Booking nelle stesse date
                    case_libere = g.elenco_case_disponibili(c_in, c_out)
                    if not case_libere:
                        st.error("❌ Tutte le case sono occupate (o bloccate da Booking) in queste date!")
                    else:
                        casa_scelta = st.selectbox("Seleziona la Casa", case_libere)
                        persone = st.selectbox("Numero di persone", ["1 Persona", "2 Persone", "3 Persone", "4 Persone"])
                        
                        if st.button("Salva Prenotazione", type="primary"):
                            stringa_stanza = f"{casa_scelta} - {persone}"
                            stanza_obj = next((s for s in g.stanze if s.nome == stringa_stanza), None)
                            if stanza_obj:
                                g.prenotazioni.append(Prenotazione(g.ospiti[osp_scelto_idx], stanza_obj, c_in, c_out, sorgente="Manuale"))
                                g._salva()
                                st.success("Prenotazione manuale inserita!")
                                st.rerun()

    with col2:
        with st.expander("✏️ Modifica Prenotazione Locale"):
            if not g.prenotazioni:
                st.info("Nessuna prenotazione manuale presente modificabile.")
            else:
                opzioni_pren = [f"ID {i} - {p.ospite.nome} ({p.stanza.nome})" for i, p in enumerate(g.prenotazioni)]
                pren_idx = st.selectbox("Scegli la prenotazione", range(len(g.prenotazioni)), format_func=lambda x: opzioni_pren[x])
                
                p_da_mod = g.prenotazioni[pren_idx]
                casa_attuale, persone_attuali = p_da_mod.stanza.nome.split(" - ")
                
                ospiti_nomi = [o.display() for o in g.ospiti]
                curr_osp_idx = g.ospiti.index(p_da_mod.ospite) if p_da_mod.ospite in g.ospiti else 0
                osp_scelto_idx = st.selectbox("Cambia Ospite", range(len(ospiti_nomi)), index=curr_osp_idx)
                
                c_in = st.date_input("Cambia Check-in", p_da_mod.check_in)
                c_out = st.date_input("Cambia Check-out", p_da_mod.check_out)
                
                if c_in >= c_out:
                    st.error("Il check-out deve essere successivo al check-in!")
                else:
                    case_libere = g.elenco_case_disponibili(c_in, c_out, ignora_idx=pren_idx)
                    if casa_attuale not in case_libere: case_libere.append(casa_attuale)
                    casa_libere.sort()
                    
                    casa_scelta = st.selectbox("Cambia Casa", case_libere, index=case_libere.index(casa_attuale))
                    persone = st.selectbox("Cambia Numero Persone", ["1 Persona", "2 Persone", "3 Persone", "4 Persone"], index=0)
                    
                    if st.button("Aggiorna Prenotazione"):
                        g.prenotazioni[pren_idx].ospite = g.ospiti[osp_scelto_idx]
                        g.prenotazioni[pren_idx].check_in = c_in
                        g.prenotazioni[pren_idx].check_out = c_out
                        g.prenotazioni[pren_idx].stanza = next(s for s in g.stanze if s.nome == f"{casa_scelta} - {persone}")
                        g._salva()
                        st.success("Modificata!")
                        st.rerun()

    with col3:
        with st.expander("🗑️ Elimina Prenotazione Locale"):
            if not g.prenotazioni:
                st.info("Nessuna prenotazione locale.")
            else:
                opzioni_pren = [f"ID {i} - {p.ospite.nome}" for i, p in enumerate(g.prenotazioni)]
                del_idx = st.selectbox("Scegli da eliminare", range(len(g.prenotazioni)), format_func=lambda x: opzioni_pren[x])
                if st.button("Elimina Definitivamente"):
                    g.prenotazioni.pop(del_idx)
                    g._salva()
                    st.rerun()

# --- SEZIONE: ANAGRAFICA OSPITI ---
elif menu == "Anagrafica Ospiti":
    st.header("👥 Anagrafica Ospiti")
    
    if g.ospiti:
        tabella_ospiti = []
        for o in g.ospiti:
            tabella_ospiti.append({
                "ID": o.id, "Nome": o.nome, "Cognome": o.cognome,
                "Luogo di Nascita": o.luogo_nascita,
                "Data di Nascita": o.data_nascita.strftime("%d/%m/%Y") if o.data_nascita else "", 
                "Telefono": o.telefono, "Email": o.email
            })
        st.dataframe(pd.DataFrame(tabella_ospiti).set_index("ID"), use_container_width=True)
    else:
        st.info("Nessun ospite registrato.")
        
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("➕ Nuovo Ospite"):
            n = st.text_input("Nome*").strip()
            c = st.text_input("Cognome*").strip()
            l_nas = st.text_input("Luogo di Nascita").strip()
            d_nas_str = st.text_input("Data di Nascita (GG/MM/AAAA)*", placeholder="es. 03/10/1985").strip()
            t = st.text_input("Telefono").strip()
            e = st.text_input("Email").strip()
            
            if st.button("Aggiungi Ospite"):
                if not n or not c or not d_nas_str:
                    st.error("I campi contrassegnati con * sono obbligatori!")
                else:
                    try:
                        dt = datetime.strptime(d_nas_str, "%d/%m/%Y").date()
                        g.ospiti.append(Ospite(n, c, t, e, l_nas, dt))
                        g._salva()
                        st.success("Ospite salvato!")
                        st.rerun()
                    except ValueError:
                        st.error("Usa il formato GG/MM/AAAA")

# --- SEZIONE: VERIFICA DISPONIBILITÀ ---
elif menu == "Verifica Disponibilità":
    st.header("🔍 Controllo Case Libere (Real-Time)")
    ci = st.date_input("Check-in", date.today())
    co = st.date_input("Check-out", date.today() + timedelta(days=1))

    if ci >= co:
        st.error("Date non valide.")
    else:
        case_libere = g.elenco_case_disponibili(ci, co)
        if not case_libere:
            st.warning("Tutto esaurito nelle date selezionate.")
        else:
            st.table(pd.DataFrame([{"Struttura / Casa": c, "Stato": "🟢 Libera sia localmente che su Booking"} for c in case_libere]))

# --- SEZIONE: ELENCO CASE ---
elif menu == "Elenco Case":
    st.header("🏠 Elenco delle strutture e Link Sincronizzazione")
    st.info("Configura i tuoi link iCal presi dall'Extranet di Booking.com nel codice sorgente (riga 52) per automatizzare il blocco.")
    st.table(pd.DataFrame([{"Casa": k, "URL iCal Configurato": v} for k, v in g.URL_ICAL_BOOKING.items()]))
