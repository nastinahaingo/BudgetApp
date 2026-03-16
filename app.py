import streamlit as st
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime
import os

# ==========================================
# 1. CONFIGURATION ET STYLE
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
    }
    .user-tag { background-color: #E0E0E0; color: #1A1A1A; padding: 3px 10px; border-radius: 15px; font-size: 0.75em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. GESTION DES FICHIERS CSV (AVEC SECURITE)
# ==========================================
USER_DB = "users_admin.csv"
BUDGET_DB = "budget_admin.csv"
COLONNES = ["id", "date", "description", "categorie", "type", "montant", "paiement", "auteur"]

def init_files():
    if not os.path.exists(USER_DB):
        pd.DataFrame(columns=["username", "password"]).to_csv(USER_DB, index=False)
    if not os.path.exists(BUDGET_DB):
        pd.DataFrame(columns=COLONNES).to_csv(BUDGET_DB, index=False)

def get_users():
    try:
        return pd.read_csv(USER_DB)
    except:
        return pd.DataFrame(columns=["username", "password"])

def get_budget():
    try:
        df = pd.read_csv(BUDGET_DB)
        if not df.empty:
            # Sécurité : on supprime les lignes totalement vides et on convertit
            df = df.dropna(subset=['date'])
            df["date"] = pd.to_datetime(df["date"], errors='coerce')
            df = df.dropna(subset=['date']) # Supprime les dates invalides (NaT)
        return df
    except:
        return pd.DataFrame(columns=COLONNES)

def save_user(username, password):
    df = get_users()
    if username in df["username"].values:
        return False
    hashed_pw = hashlib.sha256(str.encode(password)).hexdigest()
    new_user = pd.DataFrame([[username, hashed_pw]], columns=["username", "password"])
    pd.concat([df, new_user]).to_csv(USER_DB, index=False)
    return True

init_files()

# ==========================================
# 3. AUTHENTIFICATION
# ==========================================
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.user = ""

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>Acces H&L Budget</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["Connexion", "Creer un compte"])
    
    with t1:
        u = st.text_input("Utilisateur")
        p = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            df_u = get_users()
            h_p = hashlib.sha256(str.encode(p)).hexdigest()
            if not df_u[(df_u["username"] == u) & (df_u["password"] == h_p)].empty:
                st.session_state.auth = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Erreur d'identifiants")
            
    with t2:
        nu = st.text_input("Nouveau nom")
        np = st.text_input("Nouveau mot de passe", type="password")
        if st.button("Valider l'inscription"):
            if save_user(nu, np): st.success("Compte cree !")
            else: st.error("Nom deja pris")
    st.stop()

# ==========================================
# 4. DASHBOARD & ANALYSE
# ==========================================
df = get_budget()

st.sidebar.write(f"Utilisateur: {st.session_state.user}")
if st.sidebar.button("Deconnexion"):
    st.session_state.auth = False
    st.rerun()

st.title("H&L Budget Pro")

if not df.empty:
    col1, col2 = st.columns(2)
    with col1:
        # Camembert
        df_dep = df[df['type'] != "Revenu"]
        if not df_dep.empty:
            fig_pie = px.pie(df_dep, values='montant', names='categorie', hole=0.4, 
                             title="Repartition", color_discrete_sequence=px.colors.sequential.Greys)
            fig_pie.update_layout(showlegend=False, height=220, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        # Evolution
        df_trend = df.set_index("date").resample("ME")["montant"].sum().reset_index()
        fig_line = px.line(df_trend, x="date", y="montant", title="Evolution", color_discrete_sequence=['#1A1A1A'])
        fig_line.update_layout(height=220, margin=dict(t=30, b=0, l=0, r=0), xaxis_title="", yaxis_title="")
        st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# ==========================================
# 5. FORMULAIRE & HISTORIQUE
# ==========================================
with st.expander("Nouvelle Operation"):
    with st.form("add_form", clear_on_submit=True):
        desc = st.text_input("Description")
        c1, c2 = st.columns(2)
        with c1:
            mt = st.number_input("Montant", min_value=0.0)
            cat = st.selectbox("Categorie", ["Transport", "Alimentation", "Loisirs", "Habitation", "Sante", "Revenu", "Autre"])
        with c2:
            dt = st.date_input("Date", datetime.now())
            tp = st.selectbox("Type", ["Variable", "Fixe", "Revenu"])
        
        if st.form_submit_button("Enregistrer"):
            new_data = pd.DataFrame([[len(df), dt.strftime('%Y-%m-%d'), desc, cat, tp, mt, "Carte", st.session_state.user]], 
                                    columns=COLONNES)
            pd.concat([df, new_data]).to_csv(BUDGET_DB, index=False)
            st.rerun()

st.subheader("Historique")
if not df.empty:
    # On affiche les données triées par date
    df_sorted = df.sort_values("date", ascending=False)
    for i, row in df_sorted.iterrows():
        st.markdown(f"""<div class="card">
        <div style="display: flex; justify-content: space-between;">
            <span style="font-size: 0.8em; color: #666;">{row['date'].strftime('%d/%m/%Y')}</span>
            <b>{row['montant']:.2f} EUR</b>
        </div>
        <div style="font-weight: 500;">{row['description']}</div>
        <span class="user-tag">{row['auteur']} | {row['categorie']}</span>
        </div>""", unsafe_allow_html=True)
        
        if st.button("Supprimer", key=f"del_{i}"):
            df.drop(i).to_csv(BUDGET_DB, index=False)
            st.rerun()
else:
    st.info("Aucune transaction enregistree.")
