import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURATION & DESIGN SAUGE (MINIMALISTE) ---
st.set_page_config(page_title="Sauge Budget", layout="centered")

st.markdown("""
    <style>
    /* Fond Vert Sauge Doux */
    .stApp { background-color: #8fa382; color: #fdfdfd; }
    
    /* Titres Typo Sobre */
    h1, h2, h3 { color: #fdfdfd !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 300; }
    
    /* Boutons et Inputs Mats */
    .stButton>button { 
        width: 100%; border-radius: 12px; border: none; 
        background-color: #7a8c6f; color: white; padding: 10px;
    }
    .stButton>button:hover { background-color: #6a7a61; color: white; }
    
    /* Cartes Dépenses */
    .card { 
        background-color: rgba(255, 255, 255, 0.15); 
        padding: 15px; border-radius: 15px; 
        margin-bottom: 15px; backdrop-filter: blur(5px);
    }
    
    /* Styliser les indicateurs de budget */
    div[data-testid="stMetricValue"] { color: white !important; font-size: 1.5rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTION DES DONNÉES ---
DB_FILE = "budget_expert.csv"
COLONNES = ["Date", "Description", "Catégorie", "Sous-Catégorie", "Mode de Paiement", "Type", "Importance", "Montant"]

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df_existing = pd.read_csv(DB_FILE)
            for col in COLONNES:
                if col not in df_existing.columns:
                    df_existing[col] = "Non spécifié"
            return df_existing[COLONNES]
        except:
            return pd.DataFrame(columns=COLONNES)
    return pd.DataFrame(columns=COLONNES)

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 3. ANALYSE ET GRAPHES ---
df = st.session_state.df
if not df.empty:
    df["Montant"] = pd.to_numeric(df["Montant"], errors='coerce').fillna(0)
    df["Date"] = pd.to_datetime(df["Date"])
    
    # KPIs
    rev = df[df['Type'] == "Revenu"]["Montant"].sum()
    dep = df[df['Type'] != "Revenu"]["Montant"].sum()
    solde = rev - dep
else:
    rev, dep, solde = 0.0, 0.0, 0.0

# --- 4. INTERFACE ---
st.title("🌿 Sauge Budget")
st.subheader(f"Solde actuel : {solde:,.2f} €")

# --- GRAPHIQUES (LES MANQUANTS) ---
if not df.empty:
    st.divider()
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Répartition des dépenses
        df_dep = df[df['Type'] != "Revenu"]
        if not df_dep.empty:
            fig_pie = px.pie(df_dep, values='Montant', names='Catégorie', 
                             hole=0.6, color_discrete_sequence=px.colors.sequential.Greens_r)
            fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=150, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_g2:
        # Évolution temporelle
        df_trend = df.groupby('Date')['Montant'].sum().reset_index()
        fig_line = px.line(df_trend, x='Date', y='Montant', color_discrete_sequence=['white'])
        fig_line.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=150, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_visible=False, yaxis_visible=False)
        st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# SAISIE
with st.expander("➕ Nouvelle Transaction", expanded=False):
    with st.form("form_sauge", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_s = st.date_input("Date", datetime.now())
            type_m = st.selectbox("Type", ["Dépense Variable", "Dépense Fixe", "Revenu"])
            cat = st.selectbox("Catégorie", ["Transport", "Alimentation", "Loisirs", "Habitation", "Santé", "Revenus", "Autre"])
        with col2:
            mt = st.number_input("Montant (€)", min_value=0.0)
            mp = st.selectbox("Paiement", ["Carte Bancaire", "Virement", "Espèces", "Prélèvement"])
            imp = st.select_slider("Importance", options=["Superflu", "Utile", "Indispensable"])
        
        desc = st.text_input("Description")

        if st.form_submit_button("Ajouter"):
            new_row = pd.DataFrame([[date_s.strftime("%Y-%m-%d"), desc, cat, "Général", mp, type_m, imp, mt]], columns=COLONNES)
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.rerun()

# HISTORIQUE
st.subheader("📋 Historique")
if not st.session_state.df.empty:
    for index, row in st.session_state.df.iloc[::-1].iterrows():
        # Transformation de la date pour l'affichage
        d_str = row['Date'].strftime("%d %b") if isinstance(row['Date'], datetime) else row['Date']
        
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between;">
                <span style="font-size: 0.8em; opacity: 0.8;">{d_str} | {row['Catégorie']}</span>
                <b>{row['Montant']:.2f} €</b>
            </div>
            <div style="font-size: 1.1em; margin-top: 5px;">{row['Description']}</div>
            <div style="font-size: 0.75em; opacity: 0.7; margin-top: 5px;">{row['Mode de Paiement']} • {row['Importance']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Supprimer", key=f"del_{index}"):
            st.session_state.df = st.session_state.df.drop(index).reset_index(drop=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.rerun()
