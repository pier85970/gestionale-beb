import streamlit as st
import json
import csv
from datetime import datetime, date, timedelta
import pandas as pd

# Configurazione della pagina Streamlit (deve essere la prima istruzione)
st.set_page_config(page_title="Gestionale B&B", page_icon="📒", layout="wide")

# ----------------------
# Modelli dati
# ----------------------
class Ospite:
    def __init__(self, nome: str, cognome: str, telefono: str = "", email: str = ""):
        self.nome = nome
        self.cognome = cognome
        self.telefono = telefono
        self.email = email

    def display(self) -> str:
        extra = []
        if self.telefono: extra.append(self.telefono)
        if self.email: extra.append(self.email)
        extra_str = f" - {' / '.join(extra)}" if extra else ""
        return f"{self.nome} {self.cognome}{extra_str}"

class Stanza:
    def __init__(self, nome: str, posti: int):
        self.nome = nome
        self.posti = posti

class Prenotazione:
    def __init__(self, ospite: Ospite, stanza: Stanza, check_in: date, check_out: date):
        self.ospite = ospite
        self.stanza = stanza
        self.check_in = check_in
        self.check_out = check_out

# ----------------------
# Logica Gestionale
# ----------------------
class GestionaleBnb:
    def __init__(self, file_dati: str = "dati.json"):
        self.file_dati = file_dati
        self.ospiti = []
        self.stanze = []
        self.prenotazioni = []
        self.mappa_posti_occupati = {}
        self.POSTI_MASSIMI_PER_CASA = 4
        self._carica()

    def rigenera_mappa_occupazione(self):
        self.mappa_posti_occupati = {}
        for p in self.prenotazioni:
            casa_nome = p.stanza.nome.split(" - ")[0]
            giorno = p.check_in
            while giorno < p.check_out:
                if giorno not in self.mappa_posti_occupati:
                    self.mappa_posti_occupati[giorno] = {}
                if casa_nome not in self.mappa_posti_occupati[giorno]:
                    self.mappa_posti_occupati[giorno][casa_nome] = 0
                self.mappa_posti_occupati[giorno][casa_nome] += p.stanza.posti
                giorno += timedelta(days=1)

    def stanza_disponibile(self, stanza: Stanza, check_in: date, check_out: date, ignora_idx = None) -> bool:
        casa_nome = stanza.nome.split(" - ")[0]
        
        if ignora_idx is not None:
            mappa_temp = {}
            for i, p in enumerate(self.prenotazioni):
                if i == ignora_idx: continue
                p_casa = p.stanza.nome.split(" - ")[0]
                if p_casa != casa_nome: continue
                giorno = p.check_in
                while giorno < p.check_out:
                    mappa_temp[giorno] = mappa_temp.get(giorno, 0) + p.stanza.posti
                    giorno += timedelta(days=1)
            
            giorno = check_in
            while giorno < check_out:
                if (self.POSTI_MASSIMI_PER_CASA - mappa_temp.get(giorno, 0)) < stanza.posti:
                    return False
                giorno += timedelta(days=1)
        else:
            giorno = check_in
            while giorno < check_out:
                posti_gia_occupati = self.mappa_posti_occupati.get(giorno, {}).get(casa_nome, 0)
                if (self.POSTI_MASSIMI_PER_CASA - posti_gia_occupati) < stanza.posti:
                    return False
                giorno += timedelta(days=1)
        return True

    def stanze_disponibili(self, check_in: date, check_out: date, ignora_idx = None):
        return [s for s in self.stanze if self.stanza_disponibile(s, check_in, check_out, ignora_idx)]

    def _carica(self):
        try:
            with open(self.file_dati, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.ospiti = []
            for o in data.get("ospiti", []):
                tel = o.get("telefono", o.get("telephone", ""))
                self.ospiti.append(Ospite(o.get("nome", ""), o.get("cognome", ""), tel, o.get("email", "")))
            self.stanze = [Stanza(s["nome"], s["posti"]) for s in data.get("stanze", [])]
            self.prenotazioni = []
            for p in data.get("prenotazioni", []):
                try:
                    o = self.ospiti[p["ospite"]]
                    s = self.stanze[p["stanza"]]
                    ci = datetime.strptime(p["check_in"], "%Y-%m-%d").date()
                    co = datetime.strptime(p["check_out"], "%Y-%m-%d").date()
                    self.prenotazioni.append(Prenotazione(o, s, ci, co))
                except: continue
        except FileNotFoundError:
            case = ["Casa Mariateressa", "Casa Antonetta", "Casa Peppino"]
            tipologie = [("Singola", 1), ("Doppia", 2), ("Tripla", 3), ("Quadrupla", 4)]
            self.stanze = [Stanza(f"{c} - {t}", posti) for c in case for t, posti in tipologie]
            self._salva()
        self.rigenera_mappa_occupazione()

    def _salva(self):
        data = {
            "ospiti": [{"nome": o.nome, "cognome": o.cognome, "telefono": o.telefono, "email": o.email} for o in self.ospiti],
            "stanze": [{"nome": s.nome, "posti": s.posti} for s in self.stanze],
            "prenotazioni": [
                {
                    "ospite": self.ospiti.index(p.ospite),
                    "stanza": self.stanze.index(p.stanza),
                    "check_in": p.check_in.strftime("%Y-%m-%d"),
                    "check_out": p.check_out.strftime("%Y-%m-%d")
                } for p in self.prenotazioni
            ]
        }
        with open(self.file_dati, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        self.rigenera_mappa_occupazione()

# Inizializzazione del gestionale nello stato di Streamlit
if "g" not in st.session_state:
    st.session_state.g = GestionaleBnb()
g = st.session_state.g

# ----------------------
# Interfaccia Grafica Web
# ----------------------
st.title("📒 Gestionale B&B — Versione Web Mobile-Friendly")

menu = st.sidebar.radio("Navigazione Menu", ["Prenotazioni", "Anagrafica Ospiti", "Verifica Disponibilità", "Elenco Stanze"])

# --- SEZIONE: PRENOTAZIONI ---
if menu == "Prenotazioni":
    st.header("📆 Registro Prenotazioni")
    
    # Filtro Anno
    anni = sorted(list({p.check_in.year for p in g.prenotazioni} | {date.today().year}), reverse=True)
    anno_sel = st.selectbox("Filtra per anno", anni)
    
    # Tabella Prenotazioni
    pren_filtrate = [
        (i, p) for i, p in enumerate(g.prenotazioni) 
        if p.check_in.year == anno_sel or p.check_out.year == anno_sel
    ]
    
    if pren_filtrate:
        tabella_dati = []
        for i, p in pren_filtrate:
            tabella_dati.append({
                "ID Interno": i,
                "Ospite": f"{p.ospite.nome} {p.ospite.cognome}",
                "Stanza/Casa assegnata": p.stanza.nome,
                "Check-in": p.check_in.strftime("%d/%m/%Y"),
                "Check-out": p.check_out.strftime("%d/%m/%Y")
            })
        df = pd.DataFrame(tabella_dati)
        st.dataframe(df.set_index("ID Interno"), use_container_width=True)
    else:
        st.info(f"Nessuna prenotazione trovata per il {anno_sel}.")
        
    st.divider()
    
    # Azioni: Nuova, Modifica, Elimina
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.expander("➕ Inserisci Nuova Prenotazione"):
            if not g.ospiti:
                st.warning("Crea prima almeno un ospite nell'Anagrafica!")
            else:
                ospiti_nomi = [o.display() for o in g.ospiti]
                osp_scelto_idx = st.selectbox("Seleziona Ospite", range(len(ospiti_nomi)), format_func=lambda x: ospiti_nomi[x], key="new_p_osp")
                
                c_in = st.date_input("Data di Check-in", date.today(), key="new_p_in")
                c_out = st.date_input("Data di Check-out", date.today() + timedelta(days=1), key="new_p_out")
                
                if c_in >= c_out:
                    st.error("Il check-out deve essere successivo al check-in!")
                else:
                    stanze_libere = g.stanze_disponibili(c_in, c_out)
                    if not stanze_libere:
                        st.error("Nessuna stanza o posto letto disponibile per queste date.")
                    else:
                        stanze_nomi = [s.nome for s in stanze_libere]
                        stanza_scelta_nome = st.selectbox("Seleziona Stanza/Casa", stanze_nomi, key="new_p_st")
                        
                        if st.button("Salva Prenotazione", type="primary"):
                            stanza_obj = next(s for s in g.stanze if s.nome == stanza_scelta_nome)
                            g.prenotazioni.append(Prenotazione(g.ospiti[osp_scelto_idx], stanza_obj, c_in, c_out))
                            g._salva()
                            st.success("Prenotazione salvata con successo!")
                            st.rerun()

    with col2:
        with st.expander("✏️ Modifica Prenotazione"):
            if not g.prenotazioni:
                st.info("Nessuna prenotazione da modificare.")
            else:
                opzioni_pren = [f"ID {i} - {p.ospite.nome} ({p.stanza.nome})" for i, p in enumerate(g.prenotazioni)]
                pren_idx = st.selectbox("Scegli quale modificare", range(len(g.prenotazioni)), format_func=lambda x: opzioni_pren[x], key="mod_p_idx")
                
                p_da_mod = g.prenotazioni[pren_idx]
                ospiti_nomi = [o.display() for o in g.ospiti]
                curr_osp_idx = g.ospiti.index(p_da_mod.ospite)
                
                osp_scelto_idx = st.selectbox("Cambia Ospite", range(len(ospiti_nomi)), index=curr_osp_idx, format_func=lambda x: ospiti_nomi[x], key="mod_p_osp")
                c_in = st.date_input("Cambia Check-in", p_da_mod.check_in, key="mod_p_in")
                c_out = st.date_input("Cambia Check-out", p_da_mod.check_out, key="mod_p_out")
                
                if c_in >= c_out:
                    st.error("Il check-out deve essere successivo al check-in!")
                else:
                    stanze_libere = g.stanze_disponibili(c_in, c_out, ignora_idx=pren_idx)
                    # Forziamo l'inclusione della sua stanza attuale se non compare
                    stanze_nomi = list({s.nome for s in stanze_libere} | {p_da_mod.stanza.nome})
                    try: curr_st_idx = stanze_nomi.index(p_da_mod.stanza.nome)
                    except: curr_st_idx = 0
                    
                    stanza_scelta_nome = st.selectbox("Cambia Stanza/Casa", stanze_nomi, index=curr_st_idx, key="mod_p_st")
                    
                    if st.button("Aggiorna Prenotazione"):
                        stanza_obj = next(s for s in g.stanze if s.nome == stanza_scelta_nome)
                        p_da_mod.ospite = g.ospiti[osp_scelto_idx]
                        p_da_mod.stanza = stanza_obj
                        p_da_mod.check_in = c_in
                        p_da_mod.check_out = c_out
                        g._salva()
                        st.success("Prenotazione modificata!")
                        st.rerun()

    with col3:
        with st.expander("🗑️ Elimina Prenotazione"):
            if not g.prenotazioni:
                st.info("Nessuna prenotazione da eliminare.")
            else:
                opzioni_pren = [f"ID {i} - {p.ospite.nome} ({p.stanza.nome})" for i, p in enumerate(g.prenotazioni)]
                del_idx = st.selectbox("Scegli quale eliminare", range(len(g.prenotazioni)), format_func=lambda x: opzioni_pren[x], key="del_p_idx")
                
                if st.button("Elimina Definitivamente", type="secondary"):
                    g.prenotazioni.pop(del_idx)
                    g._salva()
                    st.success("Prenotazione eliminata!")
                    st.rerun()

    # Esportazione CSV
    st.divider()
    if g.prenotazioni:
        csv_buffer = []
        for p in g.prenotazioni:
            csv_buffer.append([f"{p.ospite.nome} {p.ospite.cognome}", p.ospite.telefono, p.ospite.email, p.stanza.nome, p.stanza.posti, p.check_in.strftime("%d/%m/%Y"), p.check_out.strftime("%d/%m/%Y")])
        
        df_csv = pd.DataFrame(csv_buffer, columns=["Ospite", "Telefono", "Email", "Stanza", "Posti", "Check-in", "Check-out"])
        csv_data = df_csv.to_csv(index=False, sep=";").encode('utf-8-sig')
        st.download_button(label="⬇️ Scarica Elenco in CSV", data=csv_data, file_name="prenotazioni_beb.csv", mime="text/csv")

# --- SEZIONE: ANAGRAFICA OSPITI ---
elif menu == "Anagrafica Ospiti":
    st.header("👥 Anagrafica Ospiti")
    
    if g.ospiti:
        df_ospiti = pd.DataFrame([{"ID": i, "Nome": o.nome, "Cognome": o.cognome, "Telefono": o.telefono, "Email": o.email} for i, o in enumerate(g.ospiti)])
        st.dataframe(df_ospiti.set_index("ID"), use_container_width=True)
    else:
        st.info("Nessun ospite registrato.")
        
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.expander("➕ Nuovo Ospite"):
            n = st.text_input("Nome", key="new_o_n").strip()
            c = st.text_input("Cognome", key="new_o_c").strip()
            t = st.text_input("Telefono", key="new_o_t").strip()
            e = st.text_input("Email", key="new_o_e").strip()
            if st.button("Aggiungi Ospite"):
                if not n or not c:
                    st.error("Nome e Cognome sono obbligatori!")
                else:
                    g.ospiti.append(Ospite(n, c, t, e))
                    g._salva()
                    st.success("Ospite registrato!")
                    st.rerun()
                    
    with col2:
        with st.expander("✏️ Modifica Ospite"):
            if g.ospiti:
                o_idx = st.selectbox("Seleziona da modificare", range(len(g.ospiti)), format_func=lambda x: f"{g.ospiti[x].nome} {g.ospiti[x].cognome}")
                o_da_mod = g.ospiti[o_idx]
                n = st.text_input("Modifica Nome", value=o_da_mod.nome).strip()
                c = st.text_input("Modifica Cognome", value=o_da_mod.cognome).strip()
                t = st.text_input("Modifica Telefono", value=o_da_mod.telefono).strip()
                e = st.text_input("Modifica Email", value=o_da_mod.email).strip()
                if st.button("Salva Modifiche Ospite"):
                    if not n or not c: st.error("Campi obbligatori vuoti!")
                    else:
                        o_da_mod.nome, o_da_mod.cognome, o_da_mod.telefono, o_da_mod.email = n, c, t, e
                        g._salva()
                        st.success("Dati aggiornati!")
                        st.rerun()

    with col3:
        with st.expander("🗑️ Elimina Ospite"):
            if g.ospiti:
                o_idx = st.selectbox("Seleziona da eliminare", range(len(g.ospiti)), format_func=lambda x: f"{g.ospiti[x].nome} {g.ospiti[x].cognome}", key="del_o_idx")
                if st.button("Elimina Ospite"):
                    ha_p = any(p.ospite is g.ospiti[o_idx] for p in g.prenotazioni)
                    if ha_p:
                        st.error("Impossibile eliminare: l'ospite ha delle prenotazioni attive nel registro.")
                    else:
                        g.ospiti.pop(o_idx)
                        g._salva()
                        st.success("Ospite rimosso!")
                        st.rerun()

# --- SEZIONE: VERIFICA DISPONIBILITÀ ---
elif menu == "Verifica Disponibilità":
    st.header("🔍 Controllo Posti Letto e Camere Libere")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        ci = st.date_input("Inizio Soggiorno (Check-in)", date.today(), key="v_in")
    with col2:
        co = st.date_input("Fine Soggiorno (Check-out)", date.today() + timedelta(days=1), key="v_out")
    with col3:
        posti_unici = sorted(list({s.posti for s in g.stanze}))
        min_p = st.selectbox("Filtra per Posti Minimi", ["Qualsiasi"] + [str(x) for x in posti_unici])

    if ci >= co:
        st.error("La data di check-out deve essere successiva alla data di check-in.")
    else:
        stanze_dispo = g.stanze_disponibili(ci, co)
        if min_p != "Qualsiasi":
            stanze_dispo = [s for s in stanze_dispo if s.posti >= int(min_p)]
            
        if not stanze_dispo:
            st.warning("Nessuna soluzione disponibile per le date e i parametri indicati.")
        else:
            risultati = []
            for s in stanze_dispo:
                casa_nome = s.nome.split(" - ")[0]
                max_occupati = 0
                giorno = ci
                while giorno < co:
                    max_occupati = max(max_occupati, g.mappa_posti_occupati.get(giorno, {}).get(casa_nome, 0))
                    giorno += timedelta(days=1)
                posti_liberi = g.POSTI_MASSIMI_PER_CASA - max_occupati
                
                risultati.append({
                    "Tipologia Soluzione Ordinabile": s.nome,
                    "Letti Liberi Totali della Casa in quelle date": f"{posti_liberi} / {g.POSTI_MASSIMI_PER_CASA}"
                })
            st.table(pd.DataFrame(risultati))

# --- SEZIONE: ELENCO STANZE ---
elif menu == "Elenco Stanze":
    st.header("🏠 Configurazione Strutture (3 Case × 4 Tipologie)")
    df_st = pd.DataFrame([{"Nome Configurazione": s.nome, "Letti Equivalenti": s.posti} for s in g.stanze])
    st.table(df_st)