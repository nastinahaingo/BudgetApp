import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime

# --- 1. DESIGN SAUGE ---
st.set_page_config(page_title="Sauge Budget Pro", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #8fa382; color: #fdfdfd; }
    h1, h2, h3 { color: #fdfdfd !important; font-family: 'Helvetica Neue', sans-serif; }
    .stButton>button { border-radius: 12px; background-color: #7a8c6f; color: white; border: none; }
    .card { background-color: rgba(255, 255, 255, 0.15); padding: 15px; border-radius: 15px; margin-bottom: 15px; }
    .filter-box { background-color: rgba(0,0,0,0.1); padding: 20px; border-radius: 15px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CHARGEMENT DONNÉES ---
DB_FILE = "budget_expert.csv"
COLONNES = ["Date", "Description", "Catégorie", "Sous-Catégorie", "Mode de Paiement", "Type", "Importance", "Montant"]

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    return pd.DataFrame(columns=COLONNES)

if 'df' not in st.session_state:
    st.session_state.df = load_data()

df_raw = st.session_state.df

# --- 3. SYSTÈME DE FILTRES ---
st.title("🌿 Analyse Sauge")

if not df_raw.empty:
    with st.container():
        st.markdown('<div class="filter-box">', unsafe_allow_html=True)
        colf1, colf2, colf3 = st.columns(3)
        
        with colf1:
            f_type = st.multiselect("Nature", options=df_raw["Type"].unique(), default=df_raw["Type"].unique())
        with colf2:
            f_cat = st.multiselect("Catégorie", options=df_raw["Catégorie"].unique(), default=df_raw["Catégorie"].unique())
        with colf3:
            f_periode = st.selectbox("Vue par", ["Jour", "Semaine", "Mois", "Année"])
        
        # Application des filtres
        df_filtered = df_raw[df_raw["Type"].isin(f_type) & df_raw["Catégorie"].isin(f_cat)]
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 4. GRAPHIQUE DYNAMIQUE ---
    st.subheader(f"Évolution des flux ({f_periode})")
    
    if not df_filtered.empty:
        # Groupement par période
        freq_map = {"Jour": "D", "Semaine": "W", "Mois": "ME", "Année": "YE"}
        df_trend = df_filtered.set_index("Date").resample(freq_map[f_periode])["Montant"].sum().reset_index()
        
        fig = px.area(df_trend, x="Date", y="Montant", 
                      color_discrete_sequence=['#fdfdfd'])
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, color="white"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)", color="white"),
            margin=dict(l=0, r=0, t=10, b=0),
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée pour cette sélection.")

st.divider()

# --- 5. SAISIE & HISTORIQUE (RESTE DU CODE) ---
# [Ici vous gardez le formulaire et l'historique du code précédent]
with st.expander("➕ Ajouter une opération"):
    # ... (Copiez le formulaire de l'étape précédente ici)
    pass

st.subheader("📋 Derniers mouvements")
# ... (Copiez la boucle d'affichage des cartes ici)
