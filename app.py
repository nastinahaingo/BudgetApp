import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime
import hashlib

# --- 1. CONFIGURATION & SÉCURITÉ ---
st.set_page_config(page_title="Mon Budget Privé", layout="centered")

# Fonction pour hacher le mot de passe (sécurité)
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

# --- 2. SYSTÈME DE LOGIN ---
# NOTE : Dans une vraie app pro, on utiliserait une DB pour les users.
# Ici, pour la simplicité, nous définissons les accès valides :
USER_CREDENTIALS = {
    "Papa": make_hashes("Secret123"), 
    "Maman": make_hashes("Maison2026")
}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

def login_screen():
    st.markdown("<h1 style='text-align: center;'>🔐 Connexion</h1>", unsafe_allow_html=True)
    with st.container():
        user = st.text_input("Utilisateur")
        password = st.text_input("Mot de passe", type='password')
        if st.button("Se connecter"):
            if user in USER_CREDENTIALS and check_hashes(password, USER_CREDENTIALS[user]):
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Utilisateur ou mot de passe incorrect")

if not st.session_state.logged_in:
    login_screen()
    st.stop() # Arrête l'exécution ici si pas connecté

# --- 3. DESIGN (FOND BLANC) ---
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #1A1A1A; }
    h1, h2, h3 { color: #1A1A1A !important; font-family: 'Helvetica Neue', sans-serif; }
    .card { 
        background-color: #F9F9F9; padding: 15px; border-radius: 12px; 
        margin-bottom: 12px; border: 1px solid #EEEEEE;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
    }
    .user-tag { background-color: #E8F0FE; color: #1967D2; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. GESTION DES DONNÉES ---
DB_FILE = "budget_expert.csv"
COLONNES = ["Date", "Description", "Catégorie", "Type", "Montant", "Mode de Paiement", "Importance", "Auteur"]

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            df["Date"] = pd.to_datetime(df["Date"])
            for col in COLONNES:
                if col not in df.columns:
                    df[col] = "Inconnu"
            return df[COLONNES]
        except:
            return pd.DataFrame(columns=COLONNES)
    return pd.DataFrame(columns=COLONNES)

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 5. INTERFACE ET GRAPHIQUES ---
st.sidebar.write(f"👤 Connecté : **{st.session_state.user}**")
if st.sidebar.button("Déconnexion"):
    st.session_state.logged_in = False
    st.rerun()

st.title("📱 Onyx Budget")

# Graphique d'évolution rapide
if not st.session_state.df.empty:
    df_trend = st.session_state.df.set_index("Date").resample("ME")["Montant"].sum().reset_index()
    fig = px.line(df_trend, x="Date", y="Montant", color_discrete_sequence=['#1A1A1A'])
    fig.update_layout(height=180, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 6. SAISIE ---
with st.expander("➕ Nouvelle Transaction", expanded=False):
    with st.form("secure_form", clear_on_submit=True):
        desc = st.text_input("Description")
        col1, col2 = st.columns(2)
        with col1:
            mt = st.number_input("Montant (€)", min_value=0.0)
            cat = st.selectbox("Catégorie", ["Transport", "Alimentation", "Loisirs", "Habitation", "Santé", "Revenu", "Autre"])
            auteur = st.selectbox("Qui fait la dépense ?", ["Papa", "Maman", "Commun"])
        with col2:
            date_s = st.date_input("Date", datetime.now())
            type_m = st.selectbox("Type", ["Dépense Variable", "Dépense Fixe", "Revenu"])
            mp = st.selectbox("Paiement", ["Carte Bancaire", "Virement", "Espèces"])
        
        if st.form_submit_button("Enregistrer"):
            new_row = pd.DataFrame([{
                "Date": pd.to_datetime(date_s), "Description": desc, "Catégorie": cat,
                "Type": type_m, "Montant": mt, "Mode de Paiement": mp, 
                "Importance": "Utile", "Auteur": auteur
            }])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.success("Enregistré !")
            st.rerun()

# --- 7. HISTORIQUE ---
st.subheader("📜 Historique")

if not st.session_state.df.empty:
    df_disp = st.session_state.df.sort_values(by="Date", ascending=False)
    for index, row in df_disp.iterrows():
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between;">
                <span style="font-size: 0.8em; color: #666;">{row['Date'].strftime('%d/%m/%Y')} | {row['Catégorie']}</span>
                <b style="color: {'#2ECC71' if row['Type'] == 'Revenu' else '#1A1A1A'};">
                    {row['Montant']:.2f} €
                </b>
            </div>
            <div style="font-weight: 500; margin-top: 5px;">{row['Description']}</div>
            <div style="margin-top: 8px;">
                <span class="user-tag">👤 {row['Auteur']}</span>
                <span style="font-size: 0.75em; color: #999; margin-left: 10px;">{row['Mode de Paiement']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Retirer", key=f"del_{index}"):
            st.session_state.df = st.session_state.df.drop(index).reset_index(drop=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.rerun()
