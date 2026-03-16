import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATION STYLE ---
st.set_page_config(page_title="Onyx Budget Privé", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #E0E0E0; }
    .stHeader { border-bottom: 2px solid #d4af37; }
    .stButton>button { border-radius: 5px; border: 1px solid #d4af37; background-color: #111; color: #d4af37; font-weight: bold; }
    .card { background-color: #111; padding: 15px; border-radius: 10px; border-left: 5px solid #d4af37; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DONNÉES ---
DB_FILE = "budget_expert.csv"

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Date", "Description", "Catégorie", "Sous-Catégorie", "Mode de Paiement", "Type", "Importance", "Montant"])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- FORMULAIRE DÉTAILLÉ ---
st.title("⚜️ Onyx Budget")
st.subheader("Saisie détaillée des flux")

with st.expander("📝 Nouvelle Entrée Détaillée", expanded=True):
    with st.form("main_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", datetime.now())
            type_mvt = st.selectbox("Type", ["Dépense Variable", "Dépense Fixe", "Revenu"])
        with col2:
            montant = st.number_input("Montant (€)", min_value=0.0, step=0.01, format="%.2f")
            paiement = st.selectbox("Moyen de paiement", ["Carte Bancaire", "Virement", "Espèces", "Prélèvement"])

        desc = st.text_input("Description (ex: Plein station Total, Courses Bio...)")
        
        col3, col4 = st.columns(2)
        with col3:
            cat = st.selectbox("Catégorie", ["Transport", "Alimentation", "Habitation", "Loisirs", "Santé", "Revenus", "Autre"])
        with col4:
            importance = st.select_slider("Importance", options=["Superflu", "Plutôt utile", "Indispensable"])

        if st.form_submit_button("Enregistrer avec précision"):
            new_row = pd.DataFrame([[date, desc, cat, "Général", paiement, type_mvt, importance, montant]], 
                                   columns=st.session_state.df.columns)
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.success("Transaction enregistrée.")
            st.rerun()

st.divider()

# --- AFFICHAGE & SUPPRESSION ---
st.subheader("📜 Derniers mouvements")

if not st.session_state.df.empty:
    # On affiche les 10 dernières transactions
    for index, row in st.session_state.df.iloc[::-1].iterrows():
        with st.container():
            st.markdown(f"""
            <div class="card">
                <span style="color:#d4af37; font-size: 0.8em;">{row['Date']} • {row['Catégorie']}</span><br>
                <b style="font-size: 1.1em;">{row['Description']}</b><br>
                <span style="font-size: 0.9em;">💳 {row['Mode de Paiement']} | ✨ {row['Importance']}</span>
                <h4 style="margin: 5px 0; color: {'#FFF' if row['Type'] == 'Revenu' else '#ff4b4b'};">
                    {'+' if row['Type'] == 'Revenu' else '-'}{row['Montant']:.2f} €
                </h4>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Retirer", key=f"del_{index}"):
                st.session_state.df = st.session_state.df.drop(index).reset_index(drop=True)
                st.session_state.df.to_csv(DB_FILE, index=False)
                st.rerun()
else:
    st.info("Aucune transaction.")
