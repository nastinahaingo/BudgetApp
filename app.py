import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
from datetime import datetime
import os

# ==========================================
# 1. CONFIGURATION ET STYLE (NOIR & BLANC)
# ==========================================
st.set_page_config(page_title="H&L Budget", layout="centered")

st.markdown("""
    <style>
    /* Fond blanc et texte noir */
    .stApp { background-color: #FFFFFF; color: #1A1A1A; }
    h1, h2, h3 { color: #1A1A1A !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 600; }
    
    /* Boutons noirs */
    .stButton>button { 
        width: 100%; border-radius: 10px; border: 1px solid #1A1A1A; 
        background-color: #1A1A1A; color: white; padding: 10px; font-weight: bold;
    }
    .stButton>button:hover { background-color: #333333; color: white; border: 1px solid #333333; }
    
    /* Cartes d'historique */
    .card { 
        background-color: #F9F9F9; padding: 15px; border-radius: 12px; 
        margin-bottom: 12px; border: 1px solid #EEEEEE;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Tags utilisateurs */
    .user-tag { 
        background-color: #E0E0E0; color: #1A1A1A; padding: 3px 10px; 
        border-radius: 15px; font-size: 0.75em; font-weight: bold; 
    }
    
    /* Menus déroulants */
    .stExpander { border: 1px solid #EEE !important; border-radius: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. GESTION DES TABLES (SQLITE)
# ==========================================
DB_NAME = "hl_budget_final.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Table 1 : Authentification
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT)''')
    # Table 2 : Budget (Transactions)
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, description TEXT, categorie TEXT, 
                  type TEXT, montant REAL, paiement TEXT, auteur TEXT)''')
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
# 3. SYSTÈME DE CONNEXION
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
        nu = st.text_input("Choisir un nom", key="reg_user")
        np = st.text_input("Choisir un mot de passe", type="password", key="reg_pass")
        if st.button("Valider l'inscription"):
            if nu and np:
                if add_user(nu, np): st.success("Compte cree avec succes.")
                else: st.error("Ce nom est deja utilise.")
    st.stop()

# ==========================================
# 4. RÉCUPÉRATION DES DONNÉES
# ==========================================
conn = sqlite3.connect(DB_NAME)
df = pd.read_sql_query("SELECT * FROM transactions", conn)
conn.close()

# Barre latérale pour déconnexion
st.sidebar.write(f"Connecte en tant que : **{st.session_state.user}**")
if st.sidebar.button("Deconnexion"):
    st.session_state.auth = False
    st.rerun()

st.title("H&L Budget Pro")

# ==========================================
# 5. ANALYSE (CAMEMBERT & EVOLUTION)
# ==========================================
if not df.empty:
    df["date"] = pd.to_datetime(df["date"])
    
    with st.expander("Filtres d'analyse", expanded=False):
        f_cat = st.multiselect("Categories", options=df["categorie"].unique(), default=df["categorie"].unique())
        f_vue = st.selectbox("Vue par", ["Jour", "Semaine", "Mois", "Annee"])
    
    df_filt = df[df["categorie"].isin(f_cat)].copy()

    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Camembert de répartition (Seulement les dépenses)
        df_dep = df_filt[df_filt['type'] != "Revenu"]
        if not df_dep.empty:
            fig_pie = px.pie(df_dep, values='montant', names='categorie', 
                             title="Repartition", hole=0.4,
                             color_discrete_sequence=px.colors.sequential.Greys_r)
            fig_pie.update_layout(showlegend=False, height=220, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
        else: st.write("Aucune depense.")

    with col_g2:
        # Courbe d'évolution
        freq_map = {"Jour": "D", "Semaine": "W", "Mois": "ME", "Annee": "YE"}
        df_trend = df_filt.set_index("date").resample(freq_map[f_vue])["montant"].sum().reset_index()
        fig_line = px.line(df_trend, x="date", y="montant", title="Evolution",
                           color_discrete_sequence=['#1A1A1A'])
        fig_line.update_layout(height=220, margin=dict(t=30, b=0, l=0, r=0), xaxis_title="", yaxis_title="")
        st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# ==========================================
# 6. SAISIE DE TRANSACTION
# ==========================================
with st.expander("Nouvelle Operation", expanded=False):
    with st.form("main_form", clear_on_submit=True):
        desc = st.text_input("Description (ex: Essence, Loyer)")
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
            c.execute('''INSERT INTO transactions 
                         (date, description, categorie, type, montant, paiement, auteur) 
                         VALUES (?,?,?,?,?,?,?)''',
                      (dt.strftime('%Y-%m-%d'), desc, cat, tp, mt, mp, st.session_state.user))
            conn.commit()
            conn.close()
            st.success("Enregistre !")
            st.rerun()

# ==========================================
# 7. HISTORIQUE & SUPPRESSION
# ==========================================
st.subheader("Historique des mouvements")
if not df.empty:
    # Affichage du plus récent au plus ancien
    for index, row in df.sort_values("date", ascending=False).iterrows():
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.8em; color: #666;">{row['date'].strftime('%d/%m/%Y')} | {row['categorie']}</span>
                <b style="font-size: 1.1em;">{row['montant']:.2f} EUR</b>
            </div>
            <div style="font-weight: 500; margin-top: 5px;">{row['description']}</div>
            <div style="margin-top: 10px;">
                <span class="user-tag">Auteur: {row['auteur']}</span>
                <span style="font-size: 0.75em; color: #999; margin-left: 10px;">{row['paiement']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Retirer", key=f"del_{row['id']}"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("DELETE FROM transactions WHERE id = ?", (int(row['id']),))
            conn.commit()
            conn.close()
            st.rerun()
else:
    st.info("Aucune operation dans la base.")
