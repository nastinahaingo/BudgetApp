import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. CONFIGURATION & DESIGN ---
st.set_page_config(page_title="Onyx Budget Privé", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #E0E0E0; }
    h1, h2, h3 { color: #d4af37 !important; font-family: 'Playfair Display', serif; }
    .stButton>button { 
        width: 100%; border-radius: 5px; border: 1px solid #d4af37; 
        background-color: #111; color: #d4af37; font-weight: bold;
    }
    .card { 
        background-color: #111; padding: 15px; border-radius: 10px; 
        border-left: 5px solid #d4af37; margin-bottom: 15px;
    }
    .stExpander { border: 1px solid #333 !important; background-color: #0a0a0a !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTION ROBUSTE DES DONNÉES ---
DB_FILE = "budget_expert.csv"
COLONNES = ["Date", "Description", "Catégorie", "Sous-Catégorie", "Mode de Paiement", "Type", "Importance", "Montant"]

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df_existing = pd.read_csv(DB_FILE)
            # Sécurité : Ajoute les colonnes manquantes si le fichier est ancien
            for col in COLONNES:
                if col not in df_existing.columns:
                    df_existing[col] = "Non spécifié"
            return df_existing
        except:
            return pd.DataFrame(columns=COLONNES)
    return pd.DataFrame(columns=COLONNES)

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 3. CALCULS DU BUDGET ---
df = st.session_state.df
# Conversion propre des montants
if not df.empty:
    df["Montant"] = pd.to_numeric(df["Montant"], errors='coerce').fillna(0)

revenus = df[df['Type'] == "Revenu"]["Montant"].sum()
depenses = df[df['Type'] != "Revenu"]["Montant"].sum()
solde = revenus - depenses

# --- 4. INTERFACE ---
st.title("⚜️ Onyx Budget")

# Indicateurs rapides
c1, c2 = st.columns(2)
with c1:
    st.metric("Revenus", f"{revenus:,.2f} €")
with c2:
    st.metric("Dépenses", f"-{depenses:,.2f} €")
st.subheader(f"Reste à vivre : {solde:,.2f} €")

st.divider()

# --- FORMULAIRE DE SAISIE ---
with st.expander("📝 Nouvelle Transaction Détaillée", expanded=False):
    with st.form("form_luxe", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            date_s = st.date_input("Date", datetime.now())
            type_m = st.selectbox("Nature", ["Dépense Variable", "Dépense Fixe", "Revenu"])
        with col_b:
            mt = st.number_input("Montant (€)", min_value=0.0, format="%.2f")
            mp = st.selectbox("Paiement", ["Carte Bancaire", "Virement", "Espèces", "Prélèvement"])
        
        desc = st.text_input("Description (ex: Plein Essence Total)")
        
        col_c, col_d = st.columns(2)
        with col_c:
            cat = st.selectbox("Catégorie", ["Transport", "Alimentation", "Habitation", "Loisirs", "Santé", "Revenus", "Autre"])
        with col_d:
            imp = st.select_slider("Importance", options=["Superflu", "Utile", "Indispensable"])

        if st.form_submit_button("💰 Enregistrer"):
            new_entry = pd.DataFrame([{
                "Date": date_s.strftime("%Y-%m-%d"),
                "Description": desc,
                "Catégorie": cat,
                "Sous-Catégorie": "Général",
                "Mode de Paiement": mp,
                "Type": type_m,
                "Importance": imp,
                "Montant": mt
            }])
            st.session_state.df = pd.concat([st.session_state.df, new_entry], ignore_index=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.success("Enregistré avec succès")
            st.rerun()

# --- 5. HISTORIQUE AVEC SUPPRESSION ---
st.subheader("📜 Historique")

if not st.session_state.df.empty:
    # On affiche l'historique du plus récent au plus ancien
    for index, row in st.session_state.df.iloc[::-1].iterrows():
        prefix = "+" if row['Type'] == "Revenu" else "-"
        color = "#FFF" if row['Type'] == "Revenu" else "#ff4b4b"
        
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color:#d4af37; font-size: 0.8em;">{row['Date']} | {row['Catégorie']}</span>
                <b style="color:{color}; font-size: 1.2em;">{prefix}{row['Montant']:.2f} €</b>
            </div>
            <div style="margin-top: 5px;">
                <b>{row['Description']}</b><br>
                <span style="font-size: 0.8em; opacity: 0.7;">💳 {row['Mode de Paiement']} • ✨ {row['Importance']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🗑️ Retirer cette ligne", key=f"btn_{index}"):
            st.session_state.df = st.session_state.df.drop(index).reset_index(drop=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.rerun()
else:
    st.info("Aucune transaction enregistrée.")
