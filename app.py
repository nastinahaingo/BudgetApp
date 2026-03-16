import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# 1. BASE DE DONNÉES & SÉCURITÉ
# ==========================================
def init_db():
    conn = sqlite3.connect('onyx_pro.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, description TEXT, 
                  categorie TEXT, type TEXT, montant REAL, paiement TEXT, auteur TEXT)''')
    conn.commit()
    conn.close()

def add_user(username, password):
    conn = sqlite3.connect('onyx_pro.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(str.encode(password)).hexdigest()
    try:
        c.execute('INSERT INTO users(username, password) VALUES (?,?)', (username, hashed_pw))
        conn.commit()
        return True
    except: return False
    finally: conn.close()

def login_user(username, password):
    conn = sqlite3.connect('onyx_pro.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(str.encode(password)).hexdigest()
    c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hashed_pw))
    data = c.fetchone()
    conn.close()
    return data

init_db()

# ==========================================
# 2. DESIGN LIGHT MODE
# ==========================================
st.set_page_config(page_title="Onyx Budget Pro", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #1A1A1A; }
    .card { background-color: #F9F9F9; padding: 15px; border-radius: 12px; border: 1px solid #EEEEEE; margin-bottom: 10px; }
    .stButton>button { border-radius: 10px; background-color: #1A1A1A; color: white; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. AUTHENTIFICATION
# ==========================================
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.user = ""

if not st.session_state.auth:
    tab1, tab2 = st.tabs(["Connexion", "Créer un compte"])
    with tab1:
        u = st.text_input("Utilisateur")
        p = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            if login_user(u, p):
                st.session_state.auth = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Erreur d'accès")
    with tab2:
        nu = st.text_input("Nouvel utilisateur")
        np = st.text_input("Nouveau mot de passe", type="password")
        if st.button("Créer le compte"):
            if add_user(nu, np): st.success("Compte créé !")
            else: st.error("Nom déjà pris")
    st.stop()

# ==========================================
# 4. ANALYSE DYNAMIQUE (FILTRES & JAUGE)
# ==========================================
conn = sqlite3.connect('onyx_pro.db')
df = pd.read_sql_query("SELECT * FROM transactions", conn)
conn.close()

if not df.empty:
    df["date"] = pd.to_datetime(df["date"])
    
    # --- ZONE DE FILTRES ---
    st.markdown("### 🔍 Affinage de l'analyse")
    c_f1, c_f2 = st.columns(2)
    with c_f1:
        # Filtre par catégorie (ex: Essence, Courses...)
        liste_cat = df["categorie"].unique().tolist()
        sel_cat = st.multiselect("Choisir Catégorie(s)", options=liste_cat, default=liste_cat)
    with c_f2:
        # Filtre par Type de temps
        f_vue = st.selectbox("Vue temporelle", ["Jour", "Semaine", "Mois", "Année"])
    
    # Filtrage du DataFrame
    df_filt = df[df["categorie"].isin(sel_cat)].copy()

    # --- CALCULS POUR LA JAUGE ---
    # Revenus totaux pour l'échelle de la jauge
    total_rev = df[df['type'] == "Revenu"]['montant'].sum()
    # Dépenses filtrées pour la valeur de la jauge
    total_dep_filt = df_filt[df_filt['type'] != "Revenu"]['montant'].sum()

    # --- AFFICHAGE DE LA JAUGE ---
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = total_dep_filt,
        domain = {'x': [0, 1], 'y': [0, 1]},
        delta = {'reference': total_rev, 'position': "top", 'relative': True, 'increasing': {'color': "#ff4b4b"}},
        title = {'text': "Poids des dépenses / Revenus", 'font': {'size': 18}},
        gauge = {
            'axis': {'range': [0, max(total_rev, total_dep_filt) * 1.1], 'tickwidth': 1},
            'bar': {'color': "#1A1A1A"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#EEEEEE",
            'steps': [
                {'range': [0, total_rev], 'color': '#E8F0FE'}, # Zone "Dans le budget"
                {'range': [total_rev, max(total_rev, total_dep_filt)*1.1], 'color': '#FFEBEE'} # Zone "Dépassement"
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': total_rev
            }
        }
    ))
    fig_gauge.update_layout(height=300, margin=dict(t=50, b=0, l=20, r=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

    # --- GRAPHique D'ÉVOLUTION FILTRABLE ---
    st.markdown(f"### 📈 Évolution : {', '.join(sel_cat[:2])}...")
    
    # Mapping des fréquences de temps
    freq_map = {"Jour": "D", "Semaine": "W", "Mois": "ME", "Année": "YE"}
    
    # Préparation des données pour le graph
    df_trend = df_filt.set_index("date").resample(freq_map[f_vue])["montant"].sum().reset_index()
    
    fig_line = px.area(df_trend, x="date", y="montant", 
                       color_discrete_sequence=['#1A1A1A'])
    
    fig_line.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#EEE", title="Montant (€)"),
        margin=dict(l=0, r=0, t=10, b=0), 
        height=250
    )
    st.plotly_chart(fig_line, use_container_width=True)

    # --- RÉCAPITULATIF CHIFFRÉ ---
    st.write(f"💰 **Total sélectionné :** {total_dep_filt:,.2f} €")
