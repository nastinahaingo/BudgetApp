import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# ==========================================
# 1. CONFIGURATION ET STYLE (MOBILE LIGHT)
# ==========================================
st.set_page_config(page_title="H&L", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #1A1A1A; }
    h1, h2, h3 { color: #1A1A1A !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 600; }
    .stButton>button { 
        width: 100%; border-radius: 12px; border: 1px solid #1A1A1A; 
        background-color: #1A1A1A; color: white; padding: 10px; font-weight: bold;
    }
    .card { 
        background-color: #F9F9F9; padding: 15px; border-radius: 15px; 
        margin-bottom: 12px; border: 1px solid #EEEEEE;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }
    .user-tag { background-color: #E8F0FE; color: #1967D2; padding: 3px 10px; border-radius: 15px; font-size: 0.75em; font-weight: bold; }
    .stExpander { border: 1px solid #EEE !important; border-radius: 15px !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. GESTION DE LA BASE DE DONNÉES (SQLITE)
# ==========================================
DB_NAME = "H&l_budget_v3.db"

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
# 3. SYSTÈME D'AUTHENTIFICATION
# ==========================================
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.user = ""

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🔐 Accès Onyx</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Connexion", "Créer un compte"])
    
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
        if st.button("Valider la création"):
            if nu and np:
                if add_user(nu, np): st.success("Compte créé ! Connectez-vous.")
                else: st.error("Nom d'utilisateur déjà pris.")
    st.stop()

# ==========================================
# 4. RÉCUPÉRATION DES DONNÉES
# ==========================================
conn = sqlite3.connect(DB_NAME)
df = pd.read_sql_query("SELECT * FROM transactions", conn)
conn.close()

st.sidebar.write(f"👤 Connecté : **{st.session_state.user}**")
if st.sidebar.button("Déconnexion"):
    st.session_state.auth = False
    st.rerun()

st.title("📱 Onyx Budget Pro")

# ==========================================
# 5. ANALYSE DYNAMIQUE (JAUGES & GRAPHS)
# ==========================================
if not df.empty:
    df["date"] = pd.to_datetime(df["date"])
    
    # --- FILTRES ---
    with st.expander("🔍 Filtres & Période", expanded=False):
        f_cat = st.multiselect("Catégories", options=df["categorie"].unique(), default=df["categorie"].unique())
        f_vue = st.selectbox("Regrouper par", ["Jour", "Semaine", "Mois", "Année"])
    
    df_filt = df[df["categorie"].isin(f_cat)].copy()

    # --- JAUGE DE PERFORMANCE ---
    total_rev = df[df['type'] == "Revenu"]['montant'].sum()
    total_dep_filt = df_filt[df_filt['type'] != "Revenu"]['montant'].sum()

    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = total_dep_filt,
        domain = {'x': [0, 1], 'y': [0, 1]},
        delta = {'reference': total_rev, 'position': "top", 'relative': True},
        title = {'text': "Dépenses / Revenus Totaux", 'font': {'size': 16}},
        gauge = {
            'axis': {'range': [0, max(total_rev, total_dep_filt) * 1.2]},
            'bar': {'color': "#1A1A1A"},
            'steps': [
                {'range': [0, total_rev], 'color': "#E8F0FE"},
                {'range': [total_rev, max(total_rev, total_dep_filt)*1.2], 'color': "#FFEBEE"}
            ],
            'threshold': {'line': {'color': "red", 'width': 4}, 'value': total_rev}
        }
    ))
    fig_gauge.update_layout(height=280, margin=dict(t=50, b=0, l=10, r=10))
    st.plotly_chart(fig_gauge, use_container_width=True)

    # --- GRAPHique D'ÉVOLUTION ---
    freq_map = {"Jour": "D", "Semaine": "W", "Mois": "ME", "Année": "YE"}
    df_trend = df_filt.set_index("date").resample(freq_map[f_vue])["montant"].sum().reset_index()
    
    fig_line = px.area(df_trend, x="date", y="montant", color_discrete_sequence=['#1A1A1A'])
    fig_line.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# ==========================================
# 6. SAISIE DE TRANSACTION
# ==========================================
with st.expander("➕ Nouvelle Opération", expanded=False):
    with st.form("main_form", clear_on_submit=True):
        desc = st.text_input("Description")
        c1, c2 = st.columns(2)
        with c1:
            mt = st.number_input("Montant (€)", min_value=0.0, format="%.2f")
            cat = st.selectbox("Catégorie", ["Transport", "Alimentation", "Loisirs", "Habitation", "Santé", "Revenu", "Autre"])
        with c2:
            dt = st.date_input("Date", datetime.now())
            tp = st.selectbox("Type", ["Variable", "Fixe", "Revenu"])
        
        mp = st.selectbox("Paiement", ["Carte Bancaire", "Espèces", "Virement"])
        
        if st.form_submit_button("Enregistrer"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO transactions (date, description, categorie, type, montant, paiement, auteur) VALUES (?,?,?,?,?,?,?)",
                      (dt.strftime('%Y-%m-%d'), desc, cat, tp, mt, mp, st.session_state.user))
            conn.commit()
            conn.close()
            st.success("Opération enregistrée !")
            st.rerun()

# ==========================================
# 7. HISTORIQUE ET SUPPRESSION
# ==========================================
st.subheader("📜 Historique")
if not df.empty:
    for index, row in df.sort_values("date", ascending=False).iterrows():
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.8em; color: #666;">{row['date'].strftime('%d/%m/%Y')} | {row['categorie']}</span>
                <b style="color: {'#2ECC71' if row['type'] == 'Revenu' else '#1A1A1A'}; font-size: 1.1em;">
                    {row['montant']:.2f} €
                </b>
            </div>
            <div style="font-weight: 500; margin-top: 5px;">{row['description']}</div>
            <div style="margin-top: 8px;">
                <span class="user-tag">👤 {row['auteur']}</span>
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
    st.info("Aucune donnée enregistrée.")
