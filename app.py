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
# 4. RÉCUPÉRATION & FILTRES
# ==========================================
conn = sqlite3.connect('onyx_pro.db')
df = pd.read_sql_query("SELECT * FROM transactions", conn)
conn.close()

if not df.empty:
    df["date"] = pd.to_datetime(df["date"])
    
    st.title("📊 Tableau de Bord")
    
    # --- LES FILTRES ---
    with st.expander("🔍 Filtres d'analyse", expanded=False):
        f_cat = st.multiselect("Catégories", options=df["categorie"].unique(), default=df["categorie"].unique())
        f_vue = st.selectbox("Regrouper par", ["Jour", "Semaine", "Mois"])
    
    df_filt = df[df["categorie"].isin(f_cat)].copy()

    # --- LES JAUGES (GAUGES) ---
    rev = df_filt[df_filt['type'] == "Revenu"]['montant'].sum()
    dep = df_filt[df_filt['type'] != "Revenu"]['montant'].sum()
    
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = dep,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Dépenses cumulées (€)"},
        gauge = {'axis': {'range': [0, max(rev, dep+100)]},
                 'bar': {'color': "#1A1A1A"},
                 'steps': [{'range': [0, rev], 'color': "#E8F0FE"}]}))
    fig_gauge.update_layout(height=250, margin=dict(t=50, b=0))
    st.plotly_chart(fig_gauge, use_container_width=True)

    # --- LE GRAPH FILTRABLE ---
    freq = "D" if f_vue == "Jour" else "W" if f_vue == "Semaine" else "ME"
    df_trend = df_filt.set_index("date").resample(freq)["montant"].sum().reset_index()
    fig_line = px.area(df_trend, x="date", y="montant", color_discrete_sequence=['#1A1A1A'])
    fig_line.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# ==========================================
# 5. SAISIE & HISTORIQUE
# ==========================================
with st.expander("➕ Nouvelle Transaction"):
    with st.form("add", clear_on_submit=True):
        d1 = st.text_input("Description")
        c1, c2 = st.columns(2)
        with c1:
            m1 = st.number_input("Montant", min_value=0.0)
            cat1 = st.selectbox("Catégorie", ["Transport", "Alimentation", "Loisirs", "Habitation", "Revenu"])
        with c2:
            dt1 = st.date_input("Date", datetime.now())
            tp1 = st.selectbox("Type", ["Variable", "Fixe", "Revenu"])
        if st.form_submit_button("Enregistrer"):
            conn = sqlite3.connect('onyx_pro.db')
            c = conn.cursor()
            c.execute("INSERT INTO transactions (date, description, categorie, type, montant, paiement, auteur) VALUES (?,?,?,?,?,?,?)",
                      (dt1.strftime('%Y-%m-%d'), d1, cat1, tp1, m1, "Carte", st.session_state.user))
            conn.commit()
            conn.close()
            st.rerun()

st.subheader("📜 Historique")
if not df.empty:
    for _, row in df.sort_values("date", ascending=False).iterrows():
        st.markdown(f"""<div class="card">
            <b>{row['montant']:.2f} €</b> - {row['description']}<br>
            <small>{row['date'].strftime('%d/%m')} | {row['categorie']} | 👤 {row['auteur']}</small>
        </div>""", unsafe_allow_html=True)
        if st.button("Retirer", key=f"d_{row['id']}"):
            conn = sqlite3.connect('onyx_pro.db')
            conn.cursor().execute("DELETE FROM transactions WHERE id=?", (int(row['id']),))
            conn.commit()
            conn.close()
            st.rerun()
