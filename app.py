import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Configurazione pagina
st.set_page_config(page_title="Gestionale B&B", layout="wide")
st.title("🏨 Gestionale B&B Potenziato")

# 1. INIZIALIZZAZIONE STATO (Database temporaneo in memoria)
if "camere" not in st.session_state:
    st.session_state.camere = {
        "101": "Singola",
        "102": "Doppia",
        "103": "Tripla",
        "201": "Doppia",
        "202": "Tripla"
    }

if "prenotazioni" not in st.session_state:
    # Alcuni dati di esempio iniziali per vedere subito la griglia popolata
    oggi = datetime.now().date()
    st.session_state.prenotazioni = [
        {
            "cliente": "Mario Rossi",
            "camera": "102",
            "check_in": oggi,
            "check_out": oggi + timedelta(days=3)
        },
        {
            "cliente": "Anna Bianchi",
            "camera": "201",
            "check_in": oggi + timedelta(days=2),
            "check_out": oggi + timedelta(days=5)
        }
    ]

# 2. FUNZIONI DI CONTROLLO
def controlla_overbooking(camera, check_in, check_out):
    """Restituisce True se c'è un conflitto di date per la camera selezionata"""
    for p in st.session_state.prenotazioni:
        if p["camera"] == camera:
            # Formula di sovrapposizione intervalli temporali
            if check_in < p["check_out"] and check_out > p["check_in"]:
                return p # Ritorna la prenotazione conflittuale
    return None

# Creazione delle schede nell'interfaccia
tab1, tab2, tab3 = st.tabs(["📊 Tabellone Disponibilità", "➕ Nuova Prenotazione", "⚙️ Gestione Camere"])

# ==========================================
# TAB 1: TABELLONE VISIVO DISPONIBILITÀ (15 Giorni)
# ==========================================
with tab1:
    st.header("🗓️ Griglia delle Occupazioni")
    st.write("Visualizzazione dei prossimi 15 giorni. In **Verde (Libero)**, in **Rosso (Occupato)** con il nome del cliente.")
    
    # Genera i prossimi 15 giorni a partire da oggi
    data_inizio = datetime.now().date()
    giorni = [data_inizio + timedelta(days=i) for i in range(15)]
    colonne_date = [d.strftime("%d/%m") for d in giorni]
    
    # Costruiamo la matrice per il DataFrame
    matrice_dati = []
    elenco_camere = sorted(list(st.session_state.camere.keys()))
    
    for cam in elenco_camere:
        riga = {"Camera": f"{cam} ({st.session_state.camere[cam]})"}
        for d in giorni:
            conflitto = False
            nome_ospite = "🟢 Libero"
            for p in st.session_state.prenotazioni:
                if p["camera"] == cam and p["check_in"] <= d < p["check_out"]:
                    conflitto = True
                    nome_ospite = f"🔴 {p['cliente']}"
                    break
            riga[d.strftime("%d/%m")] = nome_ospite
        matrice_dati.append(riga)
    
    df_griglia = pd.DataFrame(matrice_dati)
    
    # Funzione per colorare le celle del DataFrame Streamlit
    def colora_celle(val):
        if "🔴" in str(val):
            return "background-color: #ffcccc; color: #cc0000; font-weight: bold;"
        if "🟢" in str(val):
            return "background-color: #e2f0d9; color: #385723;"
        return ""
    
    df_stilizzato = df_griglia.style.map(colora_celle, subset=colonne_date)
    st.dataframe(df_stilizzato, use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: INSERIMENTO NUOVA PRENOTAZIONE (Con Blocco)
# ==========================================
with tab2:
    st.header("📝 Inserisci i dati dell'ospite")
    
    with st.form("form_prenotazione", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            cliente = st.text_input("Nome e Cognome Cliente:")
            # Crea la lista delle camere formattata per il menu a tendina
            opzioni_camere = [f"{k} - {v}" for k, v in st.session_state.camere.items()]
            camera_scelta_completa = st.selectbox("Seleziona Camera:", opzioni_camere)
            camera_id = camera_scelta_completa.split(" - ")[0] if camera_scelta_completa else None
            
        with col2:
            check_in = st.date_input("Data di Check-In:", datetime.now().date())
            check_out = st.date_input("Data di Check-Out:", datetime.now().date() + timedelta(days=1))
            
        submit = st.form_submit_with_button("Salva Prenotazione")
        
        if submit:
            if not cliente:
                st.error("⚠️ Inserisci il nome del cliente!")
            elif check_in >= check_out:
                st.error("⚠️ La data di check-out deve essere successiva a quella di check-in!")
            elif camera_id is None:
                st.error("⚠️ Nessuna camera selezionata!")
            else:
                # Controllo Overbooking attivo
                conflitto = controlla_overbooking(camera_id, check_in, check_out)
                
                if conflitto:
                    st.error(f"❌ IMPOSSIBILE SALVARE: La camera {camera_id} è già occupata in queste date da **{conflitto['cliente']}** (dal {conflitto['check_in'].strftime('%d/%m')} al {conflitto['check_out'].strftime('%d/%m')})!")
                else:
                    # Se tutto è ok, salva nel database temporaneo
                    nuova_p = {
                        "cliente": cliente,
                        "camera": camera_id,
                        "check_in": check_in,
                        "check_out": check_out
                    }
                    st.session_state.prenotazioni.append(nuova_p)
                    st.success(f"🎉 Prenotazione salvata con successo per {cliente} in Camera {camera_id}!")
                    st.rerun()

    # Tabella riepilogativa testuale sotto il form
    st.subheader("📋 Elenco Totale Prenotazioni")
    if st.session_state.prenotazioni:
        dati_tabella = []
        for i, p in enumerate(st.session_state.prenotazioni):
            dati_tabella.append({
                "ID": i + 1,
                "Cliente": p["cliente"],
                "Camera": f"{p['camera']} ({st.session_state.camere.get(p['camera'], 'N/D')})",
                "Check-In": p["check_in"].strftime("%d/%m/%Y"),
                "Check-Out": p["check_out"].strftime("%d/%m/%Y")
            })
        st.table(dati_tabella)
    else:
        st.info("Nessuna prenotazione attiva nel sistema.")

# ==========================================
# TAB 3: GESTIONE CONFIGURAZIONE CAMERE
# ==========================================
with tab3:
    st.header("🛠️ Configurazione Stanze della Struttura")
    
    col_lista, col_aggiungi = st.columns(2)
    
    with col_lista:
        st.subheader("Stanze Esistenti")
        df_camere = pd.DataFrame([{"Numero Camera": k, "Tipologia": v} for k, v in st.session_state.camere.items()])
        st.dataframe(df_camere, hide_index=True, use_container_width=True)
        
    with col_aggiungi:
        st.subheader("Aggiungi Nuova Stanza")
        nuovo_numero = st.text_input("Numero o Nome Stanza (es. 104 o 'Suite'):")
        nuova_tipologia = st.selectbox("Tipologia Stanza:", ["Singola", "Doppia", "Tripla", "Quadrupla", "Suite"])
        btn_aggiungi = st.button("Aggiungi Stanza")
        
        if btn_aggiungi:
            if not nuovo_numero:
                st.error("Inserisci un numero/nome valido!")
            elif nuovo_numero in st.session_state.camere:
                st.error("Questa stanza esiste già nel sistema!")
            else:
                st.session_state.camere[nuovo_numero] = nuova_tipologia
                st.success(f"Stanza {nuovo_numero} ({nuova_tipologia}) aggiunta!")
                st.rerun()
