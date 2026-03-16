import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import plotly.express as px

# ==========================================
# 1. INITIALISATION DE LA BASE DE DONNÉES (SQLITE)
# ==========================================
def init_db():
    conn = sqlite3.connect('onyx_data.db')
    c = conn.cursor()
    # Table des utilisateurs
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT)''')
    # Table des transactions
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, description TEXT, categorie TEXT, 
                  type TEXT, montant REAL, paiement TEXT, auteur TEXT)''')
    conn.commit()
    conn.close()

def add_user(username, password):
    conn = sqlite3.connect('onyx_data.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(str.encode(password)).hexdigest()
    try:
        c.execute('INSERT INTO users(username, password) VALUES (?,?)', (username, hashed_pw))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect('onyx_data.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(str.encode(password)).hexdigest()
    c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hashed_pw))
    data = c.fetchone()
    conn.close()
    return data

init_db()

# ==========================================
# 2. DESIGN & STYLE (MOBILE LIGHT)
# ==========================================
st.set_page_config(page_title="Onyx Budget", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #1A1A1A; }
    .card { 
        background-color: #F9F9F9; padding: 15px; border-radius: 12px; 
        border: 1px solid #EEEEEE; margin-bottom: 10px;
    }
    .user-tag { background-color: #E8F0FE; color: #1967D2; padding: 3px 10px; border-radius: 15px; font-size: 0.75em; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. ÉCRAN D'ACCÈS (LOGIN / CRÉATION)
# ==========================================
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.user = ""

if not st.session_state.auth:
    tab1, tab2 = st.tabs(["Connexion", "Créer un compte"])
    
    with tab1:
        u1 = st.text_input("Nom d'utilisateur", key="l1")
        p1 = st.text_input("Mot de passe", type="password", key="l2")
        if st.button("Se connecter"):
            if login_user(u1, p1):
                st.session_state.auth = True
                st.session_state.user = u1
                st.rerun()
            else:
                st.error("Échec de la connexion")
                
    with tab2:
        u2 = st.text_input("Choisir un nom", key="r1")
        p2 = st.text_input("Choisir un mot de passe", type="password", key="r2")
        if st.button("Créer mon compte"):
            if u2 and p2:
                if add_user(u2, p2):
                    st.success("Compte créé ! Vous pouvez vous connecter.")
                else:
                    st.error("Ce nom d'utilisateur existe déjà.")
    st.stop()

# ==========================================
# 4. CŒUR DE L'APPLICATION (APRES LOGIN)
# ==========================================
st.sidebar.write(f"👤 {st.session_state.user}")
if st.sidebar.button("Déconnexion"):
    st.session_state.auth = False
    st.rerun()

st.title("📱 Onyx Budget")

# --- FONCTION POUR LES DONNÉES ---
def get_data():
    conn = sqlite3.connect('onyx_data.db')
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df

df = get_data()

# --- FORMULAIRE D'AJOUT ---
with st.expander("➕ Ajouter une transaction", expanded=False):
    with st.form("add_form", clear_on_submit=True):
        desc = st.text_input("Description")
        col1, col2 = st.columns(2)
        with col1:
            mt = st.number_input("Montant (€)", min_value=0.0)
            cat = st.selectbox("Catégorie", ["Transport", "Alimentation", "Loisirs", "Habitation", "Santé", "Revenu"])
        with col2:
            dt = st.date_input("Date", datetime.now())
            tp = st.selectbox("Type", ["Variable", "Fixe", "Revenu"])
        
        paiement = st.selectbox("Paiement", ["Carte Bancaire", "Espèces", "Virement"])
        
        if st.form_submit_button("Enregistrer"):
            conn = sqlite3.connect('onyx_data.db')
            c = conn.cursor()
            c.execute('''INSERT INTO transactions (date, description, categorie, type, montant, paiement, auteur) 
                         VALUES (?,?,?,?,?,?,?)''', 
                      (dt.strftime('%Y-%m-%d'), desc, cat, tp, mt, paiement, st.session_state.user))
            conn.commit()
            conn.close()
            st.success("Enregistré !")
            st.rerun()

# --- HISTORIQUE ---
st.subheader("📜 Historique")
if not df.empty:
    for index, row in df.sort_values("date", ascending=False).iterrows():
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between;">
                <span style="font-size: 0.8em; color: #666;">{row['date'].strftime('%d/%m/%Y')} | {row['categorie']}</span>
                <b style="color: {'#2ECC71' if row['type'] == 'Revenu' else '#1A1A1A'};">{row['montant']:.2f} €</b>
            </div>
            <div style="font-weight: 500;">{row['description']}</div>
            <div style="margin-top: 5px;"><span class="user-tag">👤 {row['auteur']}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Supprimer", key=f"del_{row['id']}"):
            conn = sqlite3.connect('onyx_data.db')
            c = conn.cursor()
            c.execute("DELETE FROM transactions WHERE id = ?", (int(row['id']),))
            conn.commit()
            conn.close()
            st.rerun()
