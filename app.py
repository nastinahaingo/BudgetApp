import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURATION & DESIGN LIGHT (MOBILE) ---
st.set_page_config(page_title="Sauge Budget Light", layout="centered")

st.markdown("""
    <style>
    /* Fond Blanc et Texte Noir */
    .stApp { background-color: #FFFFFF; color: #1A1A1A; }
    
    /* Titres Typo Propre */
    h1, h2, h3 { color: #1A1A1A !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 600; }
    
    /* Boutons Minimalistes */
    .stButton>button { 
        width: 100%; border-radius: 10px; border: 1px solid #1A1A1A; 
        background-color: #1A1A1A; color: white; padding: 10px;
    }
    .stButton>button:hover { background-color: #333333; color: white; }
    
    /* Cartes Dépenses (Ombre légère pour relief) */
    .card { 
        background-color: #F9F9F9; 
        padding: 15px; border-radius: 12px; 
        margin-bottom: 12px; border: 1px solid #EEEEEE;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Filtres et Expander */
    .stExpander { border: 1px solid #EEEEEE !important; border-radius: 12px !important; }
    div[data-testid="stMetricValue"] { color: #1A1A1A !important; }
    
    /* Couleur des textes d'input */
    label { color: #1A1A1A !important; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTION DES DONNÉES ---
DB_FILE = "budget_expert.csv"
COLONNES = ["Date", "Description", "Catégorie", "Sous-Catégorie", "Mode de Paiement", "Type", "Importance", "Montant"]

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            df["Date"] = pd.to_datetime(df["Date"])
            for col in COLONNES:
                if col not in df.columns:
                    df[col] = "Non spécifié"
            return df[COLONNES]
        except:
            return pd.DataFrame(columns=COLONNES)
    return pd.DataFrame(columns=COLONNES)

if 'df' not in st.session_state:
    st.session_state.df = load_data()

df_raw = st.session_state.df

# --- 3. INTERFACE PRINCIPALE ---
st.title("📱 Mon Budget")

if not df_raw.empty:
    # FILTRES
    c_f1, c_f2 = st.columns(2)
    with c_f1:
        f_cat = st.multiselect("Filtrer par catégorie", options=df_raw["Catégorie"].unique(), default=df_raw["Catégorie"].unique())
    with c_f2:
        f_vue = st.selectbox("Vue par", ["Jour", "Mois", "Année"])

    # Application filtres
    df_filtered = df_raw[df_raw["Catégorie"].isin(f_cat)].copy()

    # --- 4. GRAPHIQUE D'ÉVOLUTION ---
    if not df_filtered.empty:
        freq = "D" if f_vue == "Jour" else "ME" if f_vue == "Mois" else "YE"
        df_trend = df_filtered.set_index("Date").resample(freq)["Montant"].sum().reset_index()
        
        fig = px.line(df_trend, x="Date", y="Montant", 
                      color_discrete_sequence=['#1A1A1A'], 
                      markers=True)
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, color="#1A1A1A"),
            yaxis=dict(showgrid=True, gridcolor="#EEEEEE", color="#1A1A1A"),
            margin=dict(l=0, r=0, t=10, b=0), height=200
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 5. SAISIE ---
with st.expander("➕ Ajouter une dépense ou revenu", expanded=False):
    with st.form("light_form", clear_on_submit=True):
        date_s = st.date_input("Date", datetime.now())
        desc = st.text_input("Description (ex: Essence, Loyer...)")
        
        col1, col2 = st.columns(2)
        with col1:
            mt = st.number_input("Montant (€)", min_value=0.0)
            cat = st.selectbox("Catégorie", ["Transport", "Alimentation", "Habitation", "Loisirs", "Santé", "Revenu", "Autre"])
        with col2:
            type_m = st.selectbox("Type", ["Dépense Variable", "Dépense Fixe", "Revenu"])
            imp = st.selectbox("Importance", ["Superflu", "Utile", "Indispensable"])
        
        mp = st.selectbox("Paiement", ["Carte Bancaire", "Virement", "Espèces"])

        if st.form_submit_button("Enregistrer"):
            new_row = pd.DataFrame([{
                "Date": pd.to_datetime(date_s), "Description": desc, "Catégorie": cat,
                "Sous-Catégorie": "Général", "Mode de Paiement": mp, "Type": type_m,
                "Importance": imp, "Montant": mt
            }])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.success("Ajouté !")
            st.rerun()

# --- 6. HISTORIQUE ---
st.subheader("📜 Historique")

if not st.session_state.df.empty:
    df_disp = st.session_state.df.sort_values(by="Date", ascending=False)
    for index, row in df_disp.iterrows():
        # Carte blanche style iOS/Android
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between;">
                <span style="font-size: 0.8em; color: #666;">{row['Date'].strftime('%d/%m/%Y')} | {row['Catégorie']}</span>
                <b style="color: {'#2ECC71' if row['Type'] == 'Revenu' else '#1A1A1A'};">
                    {'+' if row['Type'] == 'Revenu' else '-'}{row['Montant']:.2f} €
                </b>
            </div>
            <div style="font-weight: 500; margin-top: 5px;">{row['Description']}</div>
            <div style="font-size: 0.75em; color: #999; margin-top: 2px;">{row['Mode de Paiement']} • {row['Importance']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Retirer", key=f"del_{index}"):
            st.session_state.df = st.session_state.df.drop(index).reset_index(drop=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.rerun()
else:
    st.info("Aucune donnée enregistrée.")
