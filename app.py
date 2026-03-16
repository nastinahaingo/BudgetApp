import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. CONFIGURATION & STYLE LUXE ---
st.set_page_config(page_title="Onyx Budget Privé", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #E0E0E0; }
    h1, h2, h3 { color: #d4af37 !important; }
    .stButton>button { 
        width: 100%; border-radius: 5px; border: 1px solid #d4af37; 
        background-color: #111; color: #d4af37; font-weight: bold;
    }
    .card { 
        background-color: #111; padding: 15px; border-radius: 10px; 
        border-left: 5px solid #d4af37; margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTION DES DONNÉES AVEC SÉCURITÉ ---
DB_FILE = "budget_expert.csv"
# Liste complète des colonnes requises
COLONNES = ["Date", "Description", "Catégorie", "Sous-Catégorie", "Mode de Paiement", "Type", "Importance", "Montant"]

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df_existing = pd.read_csv(DB_FILE)
            # FORCE l'ajout des colonnes si elles manquent (évite le KeyError)
            for col in COLONNES:
                if col not in df_existing.columns:
                    df_existing[col] = "Non spécifié"
            return df_existing[COLONNES] # On garde l'ordre propre
        except:
            return pd.DataFrame(columns=COLONNES)
    return pd.DataFrame(columns=COLONNES)

# Initialisation
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 3. CALCULS ---
df = st.session_state.df
if not df.empty:
    df["Montant"] = pd.to_numeric(df["Montant"], errors='coerce').fillna(0)
    rev = df[df['Type'] == "Revenu"]["Montant"].sum()
    dep = df[df['Type'] != "Revenu"]["Montant"].sum()
    solde = rev - dep
else:
    rev, dep, solde = 0.0, 0.0, 0.0

# --- 4. INTERFACE ---
st.title("⚜️ Onyx Budget")
st.subheader(f"Solde : {solde:,.2f} €")

# FORMULAIRE
with st.expander("📝 Nouvelle Transaction Détaillée", expanded=False):
    with st.form("form_v3", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_s = st.date_input("Date", datetime.now())
            type_m = st.selectbox("Nature", ["Dépense Variable", "Dépense Fixe", "Revenu"])
            cat = st.selectbox("Catégorie", ["Transport", "Alimentation", "Loisirs", "Habitation", "Santé", "Revenus", "Autre"])
        with col2:
            mt = st.number_input("Montant (€)", min_value=0.0, format="%.2f")
            mp = st.selectbox("Paiement", ["Carte Bancaire", "Virement", "Espèces", "Prélèvement"])
            imp = st.select_slider("Importance", options=["Superflu", "Utile", "Indispensable"])
        
        desc = st.text_input("Description")

        if st.form_submit_button("💰 Enregistrer"):
            new_row = pd.DataFrame([[date_s.strftime("%Y-%m-%d"), desc, cat, "Général", mp, type_m, imp, mt]], columns=COLONNES)
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.rerun()

st.divider()

# HISTORIQUE
st.subheader("📜 Historique")
if not st.session_state.df.empty:
    for index, row in st.session_state.df.iloc[::-1].iterrows():
        color = "#FFF" if row['Type'] == "Revenu" else "#ff4b4b"
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between;">
                <span style="color:#d4af37; font-size: 0.8em;">{row['Date']} | {row['Catégorie']}</span>
                <b style="color:{color};">{row['Montant']:.2f} €</b>
            </div>
            <b>{row['Description']}</b><br>
            <span style="font-size: 0.8em; opacity: 0.7;">💳 {row['Mode de Paiement']} | ✨ {row['Importance']}</span>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Retirer", key=f"del_{index}"):
            st.session_state.df = st.session_state.df.drop(index).reset_index(drop=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.rerun()
