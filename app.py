import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
from datetime import datetime
import os

# ==========================================
# 1. CONFIGURATION ET STYLE (MINIMALISTE)
# ==========================================
st.set_page_config(page_title="H&L Budget", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #1A1A1A; }
    h1, h2, h3 { color: #1A1A1A !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 600; }
    .stButton>button { 
        width: 100%; border-radius: 10px; border: 1px solid #1A1A1A; 
        background-color: #1A1A1A; color: white; padding: 10px; font-weight: bold;
    }
    .card { 
        background-color: #F9F9F9; padding: 15px; border-radius: 12px; 
        margin-bottom: 12px; border: 1px solid #EEEEEE;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }
    .user-tag { background-color: #E0E0E0; color: #1A1A1A; padding: 3px 10px; border-radius: 15px; font-size: 0.75em; font-weight: bold; }
    .stExpander { border: 1px solid #EEE !important; border-radius: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. GESTION DE LA BASE DE DONNÉES
# ==========================================
DB_NAME = "hl_budget_v4.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, description TEXT, 
                  categorie TEXT, type TEXT, montant REAL, paiement TEXT, auteur TEXT)''')
    conn.commit()
    conn.close()

def add_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    hashed_pw = hashlib.sha256(str.encode(password)).hexdigest()
    try:
        c.execute('INSERT INTO users(username, password) VALUES (?,?)', (username, hashed_pw))
        conn.commit()
        return True
    except: return False
    finally: conn.close()

def login_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    hashed_pw = hashlib.sha256(str.encode(password)).hexdigest()
    c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hashed_pw))
    data = c.fetchone()
    conn.close()
    return data

init_db()

# ==========================================
# 3. AUTHENTIFICATION
# ==========================================
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.user = ""

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>Acces H&L Budget</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Connexion", "Creer un compte"])
    
    with tab1:
        u = st.text_input("Utilisateur", key="login_user")
        p = st.text_input("Mot de passe", type="password", key="login_pass")
        if st.button("Se connecter"):
            if login_user(u, p):
                st.session_state.auth = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Identifiants incorrects.")
            
    with tab2:
        nu = st.text_input("Nom d'utilisateur", key="reg_user")
        np = st.text_input("Mot de passe", type="password", key="reg_pass")
        if st.button("Valider la creation"):
            if nu and np:
                if add_user(nu, np): st.success("Compte cree. Connectez-vous.")
                else: st.error("Nom deja pris.")
    st.stop()

# ==========================================
# 4. RÉCUPÉRATION ET FILTRES
# ==========================================
conn = sqlite3.connect(DB_NAME)
df = pd.read_sql_query("SELECT * FROM transactions", conn)
conn.close()

st.sidebar.write(f"Utilisateur: {st.session_state.user}")
if st.sidebar.button("Deconnexion"):
    st.session_state.auth = False
    st.rerun()

st.title("H&L Budget Pro")

if not df.empty:
    df["date"] = pd.to_datetime(df["date"])
    
    # --- FILTRES ---
    with st.expander("Filtres et Periode", expanded=False):
        f_cat = st.multiselect("Categories", options=df["categorie"].unique(), default=df["categorie"].unique())
        f_vue = st.selectbox("Regrouper par", ["Jour", "Semaine", "Mois", "Annee"])
    
    df_filt = df[df["categorie"].isin(f_cat)].copy()

    # ==========================================
    # 5. ANALYSE (CAMEMBERT ET ÉVOLUTION)
    # ==========================================
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Camembert de repartition des depenses
        df_depenses = df_filt[df_filt['type'] != "Revenu"]
        if not df_depenses.empty:
            fig_pie = px.pie(df_depenses, values='montant', names='categorie', 
                             title="Repartition",
                             color_discrete_sequence=px.colors.qualitative.Grey)
            fig_pie.update_layout(showlegend=False, height=250, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.write("Pas de depenses.")

    with col_g2:
        # Evolution temporelle
        freq_map = {"Jour": "D", "Semaine": "W", "Mois": "ME", "Annee": "YE"}
        df_trend = df_filt.set_index("date").resample(freq_map[f_vue])["montant"].sum().reset_index()
        fig_line = px.line(df_trend, x="date", y="montant", title="Evolution",
                           color_discrete_sequence=['#1A1A1A'])
        fig_line.update_layout(height=250, margin=dict(t=30, b=0, l=0, r=0), xaxis_title="", yaxis_title="")
        st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# ==========================================
# 6. SAISIE DE TRANSACTION
# ==========================================
with st.expander("Nouvelle Operation", expanded=False):
    with st.form("main_form", clear_on_submit=True):
        desc = st.text_input("Description")
        c1, c2 = st.columns(2)
        with c1:
            mt = st.number_input("Montant (EUR)", min_value=0.0, format="%.2f")
            cat = st.selectbox("Categorie", ["Transport", "Alimentation", "Loisirs", "Habitation", "Sante", "Revenu", "Autre"])
        with c2:
            dt = st.date_input("Date", datetime.now())
            tp = st.selectbox("Type", ["Variable", "Fixe", "Revenu"])
        
        mp = st.selectbox("Paiement", ["Carte Bancaire", "Especes", "Virement"])
        
        if st.form_submit_button("Enregistrer"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO transactions (date, description, categorie, type, montant, paiement, auteur) VALUES (?,?,?,?,?,?,?)",
                      (dt.strftime('%Y-%m-%d'), desc, cat, tp, mt, mp, st.session_state.user))
            conn.commit()
            conn.close()
            st.rerun()

# ==========================================
# 7. HISTORIQUE
# ==========================================
st.subheader("Historique")
if not df.empty:
    for index, row in df.sort_values("date", ascending=False).iterrows():
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.8em; color: #666;">{row['date'].strftime('%d/%m/%Y')} | {row['categorie']}</span>
                <b style="font-size: 1.1em;">{row['montant']:.2f} EUR</b>
            </div>
            <div style="font-weight: 500; margin-top: 5px;">{row['description']}</div>
            <div style="margin-top: 8px;">
                <span class="user-tag">Utilisateur: {row['auteur']}</span>
                <span style="font-size: 0.75em; color: #999; margin-left: 10px;">{row['paiement']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Supprimer", key=f"del_{row['id']}"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("DELETE FROM transactions WHERE id = ?", (int(row['id']),))
            conn.commit()
            conn.close()
            st.rerun()
else:
    st.info("Aucune donnee enregistree.")
