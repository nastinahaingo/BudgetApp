import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATION & STYLE ---
st.set_page_config(page_title="LuxeBudget Mobile", layout="centered") # Centré pour mobile

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #E0E0E0; }
    .stButton>button { width: 100%; border-radius: 20px; border: 1px solid #d4af37; background-color: transparent; color: #d4af37; }
    .delete-btn { color: #ff4b4b; cursor: pointer; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTION DU FICHIER DE DONNÉES ---
DB_FILE = "budget_data.csv"

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Date", "Description", "Catégorie", "Type", "Montant"])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- LOGIQUE DE SUPPRESSION ---
def delete_row(index):
    st.session_state.df = st.session_state.df.drop(index).reset_index(drop=True)
    st.session_state.df.to_csv(DB_FILE, index=False)
    st.rerun()

# --- INTERFACE MOBILE ---
st.title("⚜️ Mon Budget")

# Formulaire d'ajout (replié par défaut pour gagner de la place)
with st.expander("➕ Ajouter une dépense/revenu", expanded=False):
    with st.form("add_form", clear_on_submit=True):
        date = st.date_input("Date", datetime.now())
        desc = st.text_input("Quoi ? (ex: Plein Essence)")
        cat = st.selectbox("Catégorie", ["Essence", "Courses", "Loyer", "Loisirs", "Salaire"])
        nature = "Revenu" if cat == "Salaire" else "Charge Variable" if cat in ["Essence", "Courses", "Loisirs"] else "Charge Fixe"
        montant = st.number_input("Montant (€)", min_value=0.0)
        
        if st.form_submit_button("Enregistrer"):
            new_entry = pd.DataFrame([[date, desc, cat, nature, montant]], columns=st.session_state.df.columns)
            st.session_state.df = pd.concat([st.session_state.df, new_entry], ignore_index=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.success("Ajouté !")
            st.rerun()

st.divider()

# --- LISTE DES DÉPENSES AVEC OPTION "RETIRER" ---
st.subheader("📋 Historique & Retrait")

if not st.session_state.df.empty:
    for index, row in st.session_state.df.iloc[::-1].iterrows(): # Afficher du plus récent au plus ancien
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write(f"**{row['Description']}** \n*{row['Date']}*")
        with col2:
            st.write(f"{row['Montant']} €")
        with col3:
            if st.button("Supprimer", key=f"del_{index}"):
                delete_row(index)
        st.write("---")
else:
    st.info("Aucune dépense enregistrée.")
