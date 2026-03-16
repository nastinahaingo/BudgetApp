import streamlit as st
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime
import os
import time

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
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. GESTION DES FICHIERS CSV (ADMIN GITHUB)
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
        if not os.path.exists(BUDGET_DB): return pd.DataFrame(columns=COLONNES)
        df = pd.read_csv(BUDGET_DB)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], errors='coerce')
            df["montant"] = pd.to_numeric(df["montant"], errors='coerce').fillna(0)
            df = df.dropna(subset=['date'])
        return df
    except:
        return pd.DataFrame(columns=COLONNES)

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
        u = st.text_input("Utilisateur", key="u_login")
        p = st.text_input("Mot de passe", type="password", key="p_login")
        if st.button("Se connecter"):
            df_u = get_users()
            h_p = hashlib.sha256(str.encode(p)).hexdigest()
            if not df_u[(df_u["username"] == u) & (df_u["password"] == h_p)].empty:
                st.session_state.auth = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Identifiants incorrects.")
            
    with t2:
        nu = st.text_input("Nouveau nom", key="u_reg")
        np = st.text_input("Nouveau mot de passe", type="password", key="p_reg")
        if st.button("Valider l'inscription"):
            df_u = get_users()
            if nu in df_u["username"].values:
                st.error("Nom deja pris.")
            elif nu and np:
                h_p = hashlib.sha256(str.encode(np)).hexdigest()
                new_u = pd.DataFrame([[nu, h_p]], columns=["username", "password"])
                pd.concat([df_u, new_u]).to_csv(USER_DB, index=False)
                st.success("Compte cree ! Connectez-vous.")
    st.stop()

# ==========================================
# 4. DASHBOARD & ANALYSE
# ==========================================
df = get_budget()

st.sidebar.write(f"Utilisateur: **{st.session_state.user}**")
if st.sidebar.button("Deconnexion"):
    st.session_state.auth = False
    st.rerun()

st.title("H&L Budget Pro")

if not df.empty:
    col1, col2 = st.columns(2)
    with col1:
        df_dep = df[df['type'] != "Revenu"]
        if not df_dep.empty:
            fig_pie = px.pie(df_dep, values='montant', names='categorie', hole=0.4, 
                             color_discrete_sequence=px.colors.sequential.Greys)
            fig_pie.update_layout(showlegend=False, height=200, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        df_trend = df.set_index("date").resample("ME")["montant"].sum().reset_index()
        fig_line = px.line(df_trend, x="date", y="montant", color_discrete_sequence=['#1A1A1A'])
        fig_line.update_layout(height=200, margin=dict(t=10, b=10, l=10, r=10), xaxis_title="", yaxis_title="")
        st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# ==========================================
# 5. SAISIE DE TRANSACTION
# ==========================================
with st.expander("Nouvelle Operation", expanded=False):
    with st.form("form_add", clear_on_submit=True):
        desc = st.text_input("Description")
        c1, c2 = st.columns(2)
        with c1:
            mt = st.number_input("Montant", min_value=0.0, step=0.01)
            cat = st.selectbox("Categorie", ["Transport", "Alimentation", "Loisirs", "Habitation", "Sante", "Revenu", "Autre"])
        with c2:
            dt = st.date_input("Date", datetime.now())
            tp = st.selectbox("Type", ["Variable", "Fixe", "Revenu"])
        
        if st.form_submit_button("Enregistrer"):
            # Charger les données fraîches
            current_df = get_budget()
            
            # Création de la nouvelle ligne avec ID unique temporel
            new_row = pd.DataFrame([{
                "id": int(time.time() * 1000), # ID unique précis à la milliseconde
                "date": dt.strftime('%Y-%m-%d'),
                "description": desc,
                "categorie": cat,
                "type": tp,
                "montant": mt,
                "paiement": "Carte",
                "auteur": st.session_state.user
            }])
            
            # Concaténation et sauvegarde
            updated_df = pd.concat([current_df, new_row], ignore_index=True)
            updated_df.to_csv(BUDGET_DB, index=False)
            st.success("Enregistre avec succes !")
            time.sleep(1)
            st.rerun()

# ==========================================
# 6. HISTORIQUE & SUPPRESSION
# ==========================================
st.subheader("Historique")
if not df.empty:
    # On trie pour afficher le plus récent en premier
    df_display = df.sort_values("date", ascending=False)
    for i, row in df_display.iterrows():
        with st.container():
            st.markdown(f"""
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.85em; color: #666;">{row['date'].strftime('%d/%m/%Y')} | {row['categorie']}</span>
                    <b style="font-size: 1.1em;">{row['montant']:.2f} EUR</b>
                </div>
                <div style="font-weight: 500; margin-top: 5px;">{row['description']}</div>
                <div style="margin-top: 10px;">
                    <span class="user-tag">Auteur: {row['auteur']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Bouton de suppression lié à l'ID unique
            if st.button("Supprimer l'entree", key=f"del_{row['id']}"):
                fresh_df = get_budget()
                fresh_df = fresh_df[fresh_df["id"] != row["id"]]
                fresh_df.to_csv(BUDGET_DB, index=False)
                st.rerun()
else:
    st.info("Aucune transaction enregistree.")
