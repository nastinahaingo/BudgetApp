import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- CONFIGURATION STYLE LUXE ---
st.set_page_config(page_title="LuxeBudget Privé", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #E0E0E0; }
    .stMetric { border: 1px solid #C5A059; border-radius: 5px; padding: 15px; background-color: #111; }
    div[data-testid="stExpander"] { border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTION DES DONNÉES (CSV LOCAL) ---
DB_FILE = "budget_data.csv"

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE, parse_dates=['Date'])
    return pd.DataFrame(columns=["Date", "Description", "Catégorie", "Type", "Montant"])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- INTERFACE ---
st.title("⚜️ Gestion de Budget Familial")
st.subheader("Pilotage des charges fixes et variables")

# Barre latérale : Saisie de données
with st.sidebar:
    st.header("Nouvelle Entrée")
    with st.form("form_entry"):
        date = st.date_input("Date", datetime.now())
        desc = st.text_input("Description")
        cat_type = st.selectbox("Nature", ["Charge Fixe", "Charge Variable", "Revenu"])
        cat_name = st.selectbox("Catégorie", ["Loyer/Crédit", "Essence", "Courses", "Électricité/Eau", "Loisirs", "Salaire", "Autre"])
        montant = st.number_input("Montant (€)", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Ajouter au registre"):
            new_data = pd.DataFrame([[date, desc, cat_name, cat_type, montant]], 
                                    columns=["Date", "Description", "Catégorie", "Type", "Montant"])
            st.session_state.df = pd.concat([st.session_state.df, new_data], ignore_index=True)
            save_data(st.session_state.df)
            st.success("Enregistré")

# --- ANALYSE DES CHIFFRES ---
df = st.session_state.df
if not df.empty:
    # Calculs
    rev = df[df['Type'] == "Revenu"]['Montant'].sum()
    fixes = df[df['Type'] == "Charge Fixe"]['Montant'].sum()
    vars = df[df['Type'] == "Charge Variable"]['Montant'].sum()
    reste = rev - fixes - vars

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenus", f"{rev:,.2f} €")
    c2.metric("Charges Fixes", f"-{fixes:,.2f} €")
    c3.metric("Charges Variables", f"-{vars:,.2f} €")
    c4.metric("Reste à vivre", f"{reste:,.2f} €", delta=f"{(reste/rev*100):.1f}%" if rev > 0 else None)

    st.divider()

    # --- ÉVOLUTION DES CHARGES ---
    st.header("📈 Évolution des Flux")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.write("**Dépenses Variables par Catégorie**")
        df_var = df[df['Type'] == "Charge Variable"]
        if not df_var.empty:
            fig_pie = px.pie(df_var, values='Montant', names='Catégorie', hole=0.5, 
                             color_discrete_sequence=px.colors.sequential.Goldenrod)
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart2:
        st.write("**Tendance Essence & Fluides**")
        df_trend = df[df['Catégorie'].isin(["Essence", "Courses"])].sort_values("Date")
        if not df_trend.empty:
            fig_line = px.line(df_trend, x="Date", y="Montant", color="Catégorie",
                               line_shape="spline", color_discrete_map={"Essence": "#D4AF37", "Courses": "#E0E0E0"})
            st.plotly_chart(fig_line, use_container_width=True)

    # --- TABLEAU DE BORD ---
    with st.expander("Voir tout l'historique des transactions"):
        st.dataframe(df.sort_values("Date", ascending=False), use_container_width=True)
else:
    st.info("Bienvenue. Veuillez saisir votre première transaction dans la barre latérale.")