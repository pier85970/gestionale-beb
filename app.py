import streamlit as st
import json
from datetime import datetime, date, timedelta
import pandas as pd
import uuid

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Gestionale B&B", page_icon="📒", layout="wide")

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
        self.data_nascita = data_nascita  # Oggetto datetime.date

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
        self.ELENCO_CASE = ["Casa Mariateressa", "Casa Antonetta", "Casa Peppino"]
        self._carica()

    def casa_disponibile(self, nome_casa: str, check_in: date, check_out: date, ignora_idx = None) -> bool:
        for i, p in enumerate(self.prenotazioni):
            if i == ignora_idx: 
                continue
            p_casa = p.stanza.nome.split(" - ")[0]
            if p_casa == nome_casa:
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
                
                self.ospiti.append(Ospite(
                    o.get("nome", ""), 
                    o.get("cognome", ""), 
                    tel, 
                    o.get("email", ""), 
                    o.get("luogo_nascita", ""), 
                    dt_nas,
                    o.get("id")
                ))
            
            mappa_ospiti = {o.id: o for o in self.ospiti}
            mappa_stanze = {s.nome: s for s in self.stanze}

            self.prenotazioni = []
            for p in data.get("prenotazioni", []):
                try:
                    id_p_ospite = p["ospite"]
                    if isinstance(id_p_ospite, int) and id_p_ospite < len(self.ospiti):
                        o = self.ospiti[id_p_ospite]
                    else:
                        o = mappa_ospiti.get(str(id_p_ospite))

                    nome_stanza = p["stanza"] if isinstance(p["stanza"], str) else self.stanze[p["stanza"]].nome
                    if " - " in nome_stanza:
                        casa, tipo = nome_stanza.split(" - ", 1)
                        if tipo in conversione_nomi:
                            nome_stanza = f"{casa} - {conversione_nomi[tipo]}"
                    
                    s = mappa_stanze.get(nome_stanza)
                    ci = datetime.strptime(p["check_in"], "%Y-%m-%d").date()
                    co = datetime.strptime(p["check_out"], "%Y-%m-%d").date()
                    
                    if o and s:
                        self.prenotazioni.append(Prenotazione(o, s, ci, co))
                except: 
                    continue
                
            self._salva()
            
        except (FileNotFoundError, json.JSONDecodeError):
            self._salva()

    def _salva(self):
        data = {
            "ospiti": [
                {
                    "id": o.id, 
                    "nome": o.nome, 
                    "cognome": o.cognome, 
                    "telefono": o.telefono, 
                    "email": o.email,
                    "luogo_nascita": o.luogo_nascita,
                    "data_nascita": o.data_nascita.strftime("%Y-%m-%d") if o.data_nascita else ""
                } for o in self.ospiti
            ],
            "prenotazioni": [
                {
                    "ospite": p.ospite.id,  
                    "stanza": p.stanza.nome, 
                    "check_in": p.check_in.strftime("%Y-%m-%d"),
                    "check_out": p.check_out.strftime("%Y-%m-%d")
                } for p in self.prenotazioni
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
st.title("📒 Gestionale B&B — Prenotazione Case Intere")

menu = st.sidebar.radio("Navigazione Menu", ["Prenotazioni", "Anagrafica Ospiti", "Verifica Disponibilità", "Elenco Case"])

# --- SEZIONE: PRENOTAZIONI ---
if menu == "Prenotazioni":
    st.header("📆 Registro Prenotazioni")
    st.subheader("🗓️ Tabellone Occupazione Case (Prossimi 15 Giorni)")
    
    data_inizio = date.today()
    giorni_tabellone = [data_inizio + timedelta(days=i) for i in range(15)]
    colonne_date = [d.strftime("%d/%m") for d in giorni_tabellone]
    
    matrice_dati = []
    for casa in g.ELENCO_CASE:
        riga = {"Struttura / Casa": casa}
        for d in giorni_tabellone:
            stato = "🟢 Libera"
            for p in g.prenotazioni:
                p_casa = p.stanza.nome.split(" - ")[0]
                if p_casa == casa and p.check_in <= d < p.check_out:
                    num_persone = p.stanza.nome.split(" - ")[1]
                    stato = f"🔴 {p.ospite.nome} {p.ospite.cognome} ({num_persone})"
                    break
            riga[d.strftime("%d/%m")] = stato
        matrice_dati.append(riga)
        
    df_griglia = pd.DataFrame(matrice_dati)
    
    def colora_celle(val):
        if "🔴" in str(val):
            return "background-color: #ffcccc; color: #cc0000; font-weight: bold;"
        if "🟢" in str(val):
            return "background-color: #e2f0d9; color: #385723;"
        return ""
    
    df_stilizzato = df_griglia.style.map(colora_celle, subset=colonne_date)
    st.dataframe(df_stilizzato, use_container_width=True, hide_index=True)
    st.divider()
    
    # Filtro Anno
    anni = sorted(list({p.check_in.year for p in g.prenotazioni} | {date.today().year}), reverse=True)
    anno_sel = st.selectbox("Filtra elenco testuale per anno", anni)
    
    # Tabella Prenotazioni
    pren_filtrate = [
        (i, p) for i, p in enumerate(g.prenotazioni) 
        if p.check_in.year == anno_sel or p.check_out.year == anno_sel
    ]
    
    if pren_filtrate:
        tabella_dati = []
        for i, p in pren_filtrate:
            parti = p.stanza.nome.split(" - ")
            tabella_dati.append({
                "ID Interno": i,
                "Ospite": f"{p.ospite.nome} {p.ospite.cognome}",
                "Casa": parti[0],
                "Ospiti Effettivi": parti[1],
                "Check-in": p.check_in.strftime("%d/%m/%Y"),
                "Check-out": p.check_out.strftime("%d/%m/%Y")
            })
        df = pd.DataFrame(tabella_dati)
        st.dataframe(df.set_index("ID Interno"), use_container_width=True)
    else:
        st.info(f"Nessuna prenotazione trovata per il {anno_sel}.")
        
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.expander("➕ Nuova Prenotazione"):
            if not g.ospiti:
                st.warning("Crea prima un ospite in Anagrafica!")
            else:
                ospiti_nomi = [o.display() for o in g.ospiti]
                osp_scelto_idx = st.selectbox("Seleziona Ospite", range(len(ospiti_nomi)), format_func=lambda x: ospiti_nomi[x], key="new_p_osp")
                
                c_in = st.date_input("Data di Check-in", date.today(), key="new_p_in")
                c_out = st.date_input("Data di Check-out", date.today() + timedelta(days=1), key="new_p_out")
                
                if c_in >= c_out:
                    st.error("Il check-out deve essere successivo al check-in!")
                else:
                    case_libere = g.elenco_case_disponibili(c_in, c_out)
                    if not case_libere:
                        st.error("❌ Tutte le case sono occupate in queste date!")
                    else:
                        casa_scelta = st.selectbox("Seleziona la Casa", case_libere, key="new_p_casa")
                        persone = st.selectbox("Numero di persone", ["1 Persona", "2 Persone", "3 Persone", "4 Persone"], key="new_p_persone")
                        
                        if st.button("Salva Prenotazione", type="primary"):
                            stringa_stanza = f"{casa_scelta} - {persone}"
                            stanza_obj = next((s for s in g.stanze if s.nome == stringa_stanza), None)
                            if stanza_obj:
                                g.prenotazioni.append(Prenotazione(g.ospiti[osp_scelto_idx], stanza_obj, c_in, c_out))
                                g._salva()
                                st.success("Prenotazione registrata con successo!")
                                st.rerun()

    with col2:
        with st.expander("✏️ Modifica Prenotazione"):
            if not g.prenotazioni:
                st.info("Nessuna prenotazione presente.")
            else:
                opzioni_pren = [f"ID {i} - {p.ospite.nome} ({p.stanza.nome})" for i, p in enumerate(g.prenotazioni)]
                pren_idx = st.selectbox("Scegli la prenotazione", range(len(g.prenotazioni)), format_func=lambda x: opzioni_pren[x], key="mod_p_idx")
                
                p_da_mod = g.prenotazioni[pren_idx]
                casa_attuale, persone_attuali = p_da_mod.stanza.nome.split(" - ")
                
                ospiti_nomi = [o.display() for o in g.ospiti]
                curr_osp_idx = g.ospiti.index(p_da_mod.ospite) if p_da_mod.ospite in g.ospiti else 0
                osp_scelto_idx = st.selectbox("Cambia Ospite", range(len(ospiti_nomi)), index=curr_osp_idx, format_func=lambda x: ospiti_nomi[x], key="mod_p_osp")
                
                c_in = st.date_input("Cambia Check-in", p_da_mod.check_in, key="mod_p_in")
                c_out = st.date_input("Cambia Check-out", p_da_mod.check_out, key="mod_p_out")
                
                if c_in >= c_out:
                    st.error("Il check-out deve essere successivo al check-in!")
                else:
                    case_libere = g.elenco_case_disponibili(c_in, c_out, ignora_idx=pren_idx)
                    if casa_attuale not in case_libere:
                        case_libere.append(casa_attuale)
                    case_libere.sort()
                    
                    idx_casa_corr = case_libere.index(casa_attuale)
                    casa_scelta = st.selectbox("Cambia Casa", case_libere, index=idx_casa_corr, key="mod_p_casa")
                    
                    opzioni_persone = ["1 Persona", "2 Persone", "3 Persone", "4 Persone"]
                    idx_pers_corr = opzioni_persone.index(persone_attuali) if persone_attuali in opzioni_persone else 0
                    persone = st.selectbox("Cambia Numero Persone", opzioni_persone, index=idx_pers_corr, key="mod_p_persone")
                    
                    if st.button("Aggiorna Prenotazione"):
                        stringa_stanza = f"{casa_scelta} - {persone}"
                        stanza_obj = next((s for s in g.stanze if s.nome == stringa_stanza), p_da_mod.stanza)
                        p_da_mod.ospite = g.ospiti[osp_scelto_idx]
                        p_da_mod.stanza = stanza_obj
                        p_da_mod.check_in = c_in
                        p_da_mod.check_out = c_out
                        g._salva()
                        st.success("Prenotazione aggiornata!")
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
            casa_n, pers_n = p.stanza.nome.split(" - ")
            csv_buffer.append([
                f"{p.ospite.nome} {p.ospite.cognome}", 
                p.ospite.telefono, 
                p.ospite.email, 
                casa_n, 
                pers_n, 
                p.check_in.strftime("%d/%m/%Y"), 
                p.check_out.strftime("%d/%m/%Y")
            ])
        
        df_csv = pd.DataFrame(csv_buffer, columns=["Ospite", "Telefono", "Email", "Casa", "Ospiti Effettivi", "Check-in", "Check-out"])
        csv_data = df_csv.to_csv(index=False, sep=";").encode('utf-8-sig')
        st.download_button(label="⬇️ Scarica Elenco in CSV", data=csv_data, file_name="prenotazioni_beb.csv", mime="text/csv")

# --- SEZIONE: ANAGRAFICA OSPITI ---
elif menu == "Anagrafica Ospiti":
    st.header("👥 Anagrafica Ospiti")
    
    if g.ospiti:
        tabella_ospiti = []
        for o in g.ospiti:
            tabella_ospiti.append({
                "ID": o.id,
                "Nome": o.nome,
                "Cognome": o.cognome,
                "Luogo di Nascita": o.luogo_nascita,
                "Data di Nascita": o.data_nascita.strftime("%d/%m/%Y") if o.data_nascita else "", 
                "Telefono": o.telefono,
                "Email": o.email
            })
        df_ospiti = pd.DataFrame(tabella_ospiti)
        st.dataframe(df_ospiti.set_index("ID"), use_container_width=True)
    else:
        st.info("Nessun ospite registrato.")
        
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.expander("➕ Nuovo Ospite"):
            n = st.text_input("Nome*", key="new_o_n").strip()
            c = st.text_input("Cognome*", key="new_o_c").strip()
            l_nas = st.text_input("Luogo di Nascita", key="new_o_ln").strip()
            
            # INPUT TESTUALE: per digitare liberamente 03/10/1985
            d_nas_str = st.text_input("Data di Nascita (GG/MM/AAAA)*", placeholder="es. 03/10/1985", key="new_o_dn_str").strip()
            
            t = st.text_input("Telefono", key="new_o_t").strip()
            e = st.text_input("Email", key="new_o_e").strip()
            
            if st.button("Aggiungi Ospite"):
                if not n or not c or not d_nas_str:
                    st.error("Nome, Cognome e Data di Nascita sono obbligatori!")
                else:
                    try:
                        # Convalida il formato italiano inserito dall'utente
                        d_nas_convertita = datetime.strptime(d_nas_str, "%d/%m/%Y").date()
                        
                        g.ospiti.append(Ospite(n, c, t, e, l_nas, d_nas_convertita))
                        g._salva()
                        st.success("Ospite registrato con successo!")
                        st.rerun()
                    except ValueError:
                        st.error("❌ Formato data non valido! Usa la struttura GG/MM/AAAA (es. 03/10/1985).")
                    
    with col2:
        with st.expander("✏️ Modifica Ospite"):
            if g.ospiti:
                o_idx = st.selectbox("Seleziona da modificare", range(len(g.ospiti)), format_func=lambda x: f"{g.ospiti[x].nome} {g.ospiti[x].cognome}")
                o_da_mod = g.ospiti[o_idx]
                
                n = st.text_input("Modifica Nome", value=o_da_mod.nome).strip()
                c = st.text_input("Modifica Cognome", value=o_da_mod.cognome).strip()
                l_nas = st.text_input("Modifica Luogo di Nascita", value=o_da_mod.luogo_nascita).strip()
                
                # Pre-popola il campo di testo con la data dell'ospite in formato italiano
                data_default_str = o_da_mod.data_nascita.strftime("%d/%m/%Y") if o_da_mod.data_nascita else ""
                d_nas_str = st.text_input("Modifica Data di Nascita (GG/MM/AAAA)", value=data_default_str, key="mod_o_dn_str").strip()
                
                t = st.text_input("Modifica Telefono", value=o_da_mod.telefono).strip()
                e = st.text_input("Modifica Email", value=o_da_mod.email).strip()
                
                if st.button("Salva Modifiche Ospite"):
                    if not n or not c or not d_nas_str: 
                        st.error("I campi Nome, Cognome e Data di Nascita sono obbligatori!")
                    else:
                        try:
                            d_nas_convertita = datetime.strptime(d_nas_str, "%d/%m/%Y").date()
                            
                            o_da_mod.nome = n
                            o_da_mod.cognome = c
                            o_da_mod.luogo_nascita = l_nas
                            o_da_mod.data_nascita = d_nas_convertita
                            o_da_mod.telefono = t
                            o_da_mod.email = e
                            g._salva()
                            st.success("Dati ospite aggiornati!")
                            st.rerun()
                        except ValueError:
                            st.error("❌ Formato data non valido! Usa la struttura GG/MM/AAAA (es. 03/10/1985).")

    with col3:
        with st.expander("🗑️ Elimina Ospite"):
            if g.ospiti:
                o_idx = st.selectbox("Seleziona da eliminare", range(len(g.ospiti)), format_func=lambda x: f"{g.ospiti[x].nome} {g.ospiti[x].cognome}", key="del_o_idx")
                if st.button("Elimina Ospite"):
                    ha_p = any(p.ospite.id == g.ospiti[o_idx].id for p in g.prenotazioni)
                    if ha_p:
                        st.error("Impossibile eliminare: l'ospite ha delle prenotazioni attive nel registro.")
                    else:
                        g.ospiti.pop(o_idx)
                        g._salva()
                        st.success("Ospite rimosso!")
                        st.rerun()

# --- SEZIONE: VERIFICA DISPONIBILITÀ ---
elif menu == "Verifica Disponibilità":
    st.header("🔍 Controllo Case Libere")
    
    col1, col2 = st.columns(2)
    with col1:
        ci = st.date_input("Inizio Soggiorno (Check-in)", date.today(), key="v_in")
    with col2:
        co = st.date_input("Fine Soggiorno (Check-out)", date.today() + timedelta(days=1), key="v_out")

    if ci >= co:
        st.error("La data di check-out deve essere successiva alla data di check-in.")
    else:
        case_libere = g.elenco_case_disponibili(ci, co)
            
        if not case_libere:
            st.warning("Nessuna struttura disponibile per le date indicate.")
        else:
            risultati = [{"Struttura / Casa": c, "Stato": "🟢 Completamente Libera"} for c in case_libere]
            st.table(pd.DataFrame(risultati))

# --- SEZIONE: ELENCO CASE ---
elif menu == "Elenco Case":
    st.header("🏠 Elenco delle strutture gestite")
    df_case = pd.DataFrame([{"Nome Struttura": c} for c in g.ELENCO_CASE])
    st.table(df_case)
