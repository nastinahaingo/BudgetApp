import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. CONFIGURATION DE LA PAGE & DESIGN LUXE ---
st.set_page_config(
    page_title="Onyx Budget Privé", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    /* Fond sombre profond */
    .stApp { background-color: #050505; color: #E0E0E0; }
    
    /* Titres en Or */
    h1, h2, h3 { color: #d4af37 !important; font-family: 'Playfair Display', serif; }
    
    /* Boutons stylisés */
    .stButton>button { 
        width: 100%; 
        border-radius: 5px; 
        border: 1px solid #d4af37; 
        background-color: #111; 
        color: #d4af37; 
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #d4af37; color: black; }
    
    /* Cartes pour les dépenses */
    .card { 
        background-color: #111; 
        padding: 15px; 
        border-radius: 10px; 
        border-left: 5px solid #d4af37; 
        margin-bottom: 10px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.5);
    }
    
    /* Input fields */
    input, select, textarea { border-radius: 5px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTION DE LA BASE DE DONNÉES (CSV) ---
DB_FILE = "budget_expert.csv"
COLONNES = ["Date", "Description", "Catégorie", "Sous-Catégorie", "Mode de Paiement", "Type", "Importance", "Montant"]

def load_data():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE)
        except:
            return pd.DataFrame(columns=COLONNES)
    return pd.DataFrame(columns=COLONNES)

# Initialisation de la session
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 3. LOGIQUE DE CALCULS ---
df = st.session_state.df
total_revenus = 0.0
total_depenses = 0.0

if not df.empty:
    # On s'assure que le montant est numérique
    df["Montant"] = pd.to_numeric(df["Montant"], errors='coerce').fillna(0)
    total_revenus = df[df['Type'] == "Revenu"]["Montant"].sum()
    total_depenses = df[df['Type'] != "Revenu"]["Montant"].sum()

reste_a_vivre = total_revenus - total_depenses

# --- 4. INTERFACE PRINCIPALE ---
st.title("⚜️ Onyx Budget")
st.write(f"**Solde disponible :** `{reste_a_vivre:,.2f} €`")

# --- FORMULAIRE DE SAISIE ---
with st.expander("📝 Nouvelle Transaction Détaillée", expanded=False):
    with st.form("main_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_saisie = st.date_input("Date", datetime.now())
            type_mvt = st.selectbox("Type", ["Dépense Variable", "Dépense Fixe", "Revenu"])
        with col2:
            montant = st.number_input("Montant (€)", min_value=0.0, step=0.01, format="%.2f")
            paiement = st.selectbox("Paiement", ["Carte Bancaire", "Virement", "Espèces", "Prélèvement"])

        desc = st.text_input("Description (ex: Plein Essence Total)")
        
        col3, col4 = st.columns(2)
        with col3:
            cat = st.selectbox("Catégorie", ["Transport", "Alimentation", "Habitation", "Loisirs", "Santé", "Revenus", "Autre"])
        with col4:
            importance = st.select_slider("Importance", options=["Superflu", "Utile", "Indispensable"])

        if st.form_submit_button("Enregistrer la transaction"):
            # Création de la nouvelle ligne
            new_entry = pd.DataFrame([{
                "Date": date_saisie.strftime("%Y-%m-%d"),
                "Description": desc,
                "Catégorie": cat,
                "Sous-Catégorie": "Général",
                "Mode de Paiement": paiement,
                "Type": type_mvt,
                "Importance": importance,
                "Montant": montant
            }])
            
            # Mise à jour
            st.session_state.df = pd.concat([st.session_state.df, new_entry], ignore_index=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.success("Transaction ajoutée !")
            st.rerun()

st.divider()

# --- 5. HISTORIQUE AVEC BOUTON SUPPRIMER ---
st.subheader("📜 Derniers mouvements")

if not st.session_state.df.empty:
    # Affichage inversé (plus récent en haut)
    for index, row in st.session_state.df.iloc[::-1].iterrows():
        color_montant = "#FFF" if row['Type'] == 'Revenu' else "#ff4b4b"
        prefixe = "+" if row['Type'] == 'Revenu' else "-"
        
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between;">
                <span style="color:#d4af37; font-size: 0.8em;">{row['Date']} • {row['Catégorie']}</span>
                <span style="color:{color_montant}; font-weight: bold;">{prefixe}{row['Montant']:.2f} €</span>
            </div>
            <b style="font-size: 1.1em;">{row['Description']}</b><br>
            <span style="font-size: 0.85em; opacity: 0.8;">💳 {row['Mode de Paiement']} | ✨ {row['Importance']}</span>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Retirer cette dépense", key=f"del_{index}"):
            st.session_state.df = st.session_state.df.drop(index).reset_index(drop=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.rerun()
else:
    st.info("Aucune donnée enregistrée pour le moment.")
