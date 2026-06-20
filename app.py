import streamlit as st
import json
import os
from datetime import datetime, timedelta
import pandas as pd

# Configurazione della pagina Streamlit (layout largo per visualizzare bene la griglia)
st.set_page_config(
    page_title="Gestionale B&B Pro",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# File di database per le prenotazioni
DB_FILE = "dati.json"

# Funzione per caricare i dati dal file JSON
def carica_dati():
    if not os.path.exists(DB_FILE):
        return {"camere": ["Singola", "Doppia", "Tripla"], "prenotazioni": []}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            dati = json.load(f)
            if "prenotazioni" not in dati:
                dati["prenotazioni"] = []
            if "camere" not in dati:
                dati["camere"] = ["Singola", "Doppia", "Tripla"]
            return dati
    except Exception:
        return {"camere": ["Singola", "Doppia", "Tripla"], "prenotazioni": []}

# Funzione per salvare i dati sul file JSON
def salva_dati(dati):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dati, f, indent=4, ensure_ascii=False)

# Inizializza lo stato dell'applicazione
if "dati" not in st.session_state:
    st.session_state.dati = carica_dati()

# --- LOGICA DI CONTROLLO DEI CONFLITTI (Overbooking) ---
def verifica_conflitto(camera, check_in, check_out):
    """
    Ritorna la prenotazione in conflitto se esiste una sovrapposizione di date
    per la stessa camera, altrimenti ritorna None.
    """
    for p in st.session_state.dati["prenotazioni"]:
        if p["camera"] == camera:
            # Convertiamo le stringhe del database in date reali
            p_in = datetime.strptime(p["check_in"], "%Y-%m-%d").date()
            p_out = datetime.strptime(p["check_out"], "%Y-%m-%d").date()
            
            # Due periodi [A, B] e [C, D] si sovrappongono se: A < D e B > C
            if (check_in < p_out) and (check_out > p_in):
                return p
    return None

# --- STRUTTURA DELL'INTERFACCIA UTENTE ---
st.title("🏨 B&B Manager Pro")
st.markdown("Gestione e controllo disponibilità in tempo reale con prevenzione dell'overbooking.")

# Sidebar laterale per inserire nuove prenotazioni
st.sidebar.header("➕ Nuova Prenotazione")
with st.sidebar.form("form_prenotazione", clear_on_submit=True):
    cliente = st.text_input("Nome Cliente", placeholder="es. Mario Rossi")
    camera = st.sidebar.selectbox("Assegna Camera", st.session_state.dati["camere"])
    
    # Range di date predefinito (Oggi e domani)
    oggi = datetime.today().date()
    domani = oggi + timedelta(days=1)
    
    check_in = st.sidebar.date_input("Data di Check-in", value=oggi, min_value=oggi)
    check_out = st.sidebar.date_input("Data di Check-out", value=domani, min_value=domani)
    note = st.sidebar.text_area("Note / Telefono", placeholder="Opzionale (es. Telefono)")
    
    salva = st.form_submit_button("Conferma e Salva")

    if salva:
        if not cliente.strip():
            st.error("Inserisci il nome del cliente!")
        elif check_in >= check_out:
            st.error("La data di check-out deve essere successiva a quella di check-in!")
        else:
            # Controllo automatico dei conflitti prima del salvataggio
            conflitto = verifica_conflitto(camera, check_in, check_out)
            if conflitto:
                st.error(
                    f"⚠️ **CONFLITTO DI DATE!** La camera **{camera}** è già occupata "
                    f"da **{conflitto['cliente']}** dal {conflitto['check_in']} al {conflitto['check_out']}."
                )
            else:
                # Se non ci sono conflitti, salviamo la prenotazione
                nuova_prenotazione = {
                    "id": str(int(datetime.now().timestamp() * 1000)),  # ID unico basato sul tempo
                    "cliente": cliente.strip(),
                    "camera": camera,
                    "check_in": check_in.strftime("%Y-%m-%d"),
                    "check_out": check_out.strftime("%Y-%m-%d"),
                    "note": note.strip()
                }
                st.session_state.dati["prenotazioni"].append(nuova_prenotazione)
                salva_dati(st.session_state.dati)
                st.sidebar.success(f"✅ Prenotazione di {cliente} salvata con successo!")
                st.rerun()

# --- PANNELLO PRINCIPALE (TAB) ---
tab_calendario, tab_elenco = st.tabs(["🗓️ Griglia Disponibilità", "📋 Elenco Prenotazioni"])

# TAB 1: Griglia Disponibilità (Il Calendario Visivo)
with tab_calendario:
    st.subheader("Disponibilità delle camere per i prossimi 15 giorni")
    
    # Selettore per scegliere da quale data far partire la griglia
    data_inizio = st.date_input("Visualizza a partire dal:", value=oggi)
    intervallo_giorni = 15
    giorni = [data_inizio + timedelta(days=i) for i in range(intervallo_giorni)]
    
    # Costruiamo la tabella delle disponibilità
    matrice_dispo = {}
    for cam in st.session_state.dati["camere"]:
        matrice_dispo[cam] = []
        for giorno in giorni:
            # Controlliamo se un ospite pernotta la notte del 'giorno' selezionato
            # (Incluso check-in, escluso check-out per quella notte)
            stato_camera = "🟢 Libera"
            for p in st.session_state.dati["prenotazioni"]:
                if p["camera"] == cam:
                    p_in = datetime.strptime(p["check_in"], "%Y-%m-%d").date()
                    p_out = datetime.strptime(p["check_out"], "%Y-%m-%d").date()
                    if p_in <= giorno < p_out:
                        stato_camera = f"🔴 {p['cliente']}"
                        break
            matrice_dispo[cam].append(stato_camera)
            
    # Creiamo il DataFrame di Pandas
    colonne_date = [g.strftime("%d/%m (%a)") for g in giorni]
    df_visualizzazione = pd.DataFrame(matrice_dispo, index=colonne_date).T
    
    # Mostriamo la tabella interattiva
    st.dataframe(df_visualizzazione, use_container_width=True, height=220)
    st.info("💡 **Legenda:** 🟢 Libera (Disponibile) | 🔴 Nome Cliente (La camera è occupata da quell'ospite per quella notte)")

# TAB 2: Elenco e Gestione Prenotazioni
with tab_elenco:
    st.subheader("Tutte le prenotazioni salvate")
    prenotazioni = st.session_state.dati["prenotazioni"]
    
    if not prenotazioni:
        st.info("Nessuna prenotazione presente nel sistema.")
    else:
        # Ordiniamo le prenotazioni per data di arrivo (le più vicine prima)
        prenotazioni_ordinate = sorted(prenotazioni, key=lambda x: x["check_in"])
        
        # Generiamo la tabella riassuntiva
        tabella_riassunto = []
        for p in prenotazioni_ordinate:
            tabella_riassunto.append({
                "Cliente": p["cliente"],
                "Camera": p["camera"],
                "Check-in (Arrivo)": p["check_in"],
                "Check-out (Partenza)": p["check_out"],
                "Note / Contatti": p["note"]
            })
            
        st.table(tabella_riassunto)
        
        # Sezione per l'eliminazione rapida
        st.markdown("---")
        st.subheader("🗑️ Cancella una prenotazione")
        
        col_select, col_btn = st.columns([3, 1])
        with col_select:
            prenotazione_scelta = st.selectbox(
                "Seleziona la prenotazione da rimuovere:",
                options=prenotazioni_ordinate,
                format_func=lambda x: f"{x['cliente']} - Camera {x['camera']} (dal {x['check_in']} al {x['check_out']})"
            )
        with col_btn:
            st.write("") # Spaziatori per allineare il pulsante
            st.write("")
            if st.button("Elimina Prenotazione", type="primary"):
                st.session_state.dati["prenotazioni"] = [p for p in prenotazioni if p["id"] != prenotazione_scelta["id"]]
                salva_dati(st.session_state.dati)
                st.success(f"La prenotazione di {prenotazione_scelta['cliente']} è stata eliminata.")
                st.rerun()
`
