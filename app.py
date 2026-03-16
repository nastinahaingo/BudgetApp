import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURATION & DESIGN SAUGE ---
st.set_page_config(page_title="Sauge Budget Pro", layout="centered")

st.markdown("""
    <style>
    /* Thème Sauge & Nature */
    .stApp { background-color: #8fa382; color: #fdfdfd; }
    h1, h2, h3 { color: #fdfdfd !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 300; }
    
    /* Boutons et Inputs */
    .stButton>button { 
        width: 100%; border-radius: 12px; border: none; 
        background-color: #7a8c6f; color: white; padding: 10px; font-weight: bold;
    }
    .stButton>button:hover { background-color: #6a7a61; }
    
    /* Cartes et boîtes de filtres */
    .card { 
        background-color: rgba(255, 255, 255, 0.15); 
        padding: 15px; border-radius: 15px; 
        margin-bottom: 12px; backdrop-filter: blur(8px);
    }
    .filter-box { 
        background-color: rgba(0, 0, 0, 0.1); 
        padding: 15px; border-radius: 15px; margin-bottom: 20px; 
    }
    
    /* Personnalisation des selects et inputs */
    .stSelectbox, .stTextInput, .stNumberInput { background-color: rgba(255,255,255,0.1); border-radius: 10px; }
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
            # Sécurité colonnes
            for col in COLONNES:
                if col not in df.columns:
                    df[col] = "Non spécifié"
            return df[COLONNES]
        except:
            return pd.DataFrame(columns=COLONNES)
    return pd.DataFrame(columns=COLONNES)

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 3. FILTRES ET ANALYSE ---
st.title("🌿 Sauge Budget")

df_raw = st.session_state.df

if not df_raw.empty:
    # Zone de filtres
    st.markdown('<div class="filter-box">', unsafe_allow_html=True)
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        natures = df_raw["Type"].unique().tolist()
        f_type = st.multiselect("Nature", options=natures, default=natures)
    with f_col2:
        cats = df_raw["Catégorie"].unique().tolist()
        f_cat = st.multiselect("Catégorie", options=cats, default=cats)
    with f_col3:
        f_periode = st.selectbox("Vue par", ["Jour", "Semaine", "Mois", "Année"])
    st.markdown('</div>', unsafe_allow_html=True)

    # Application filtres
    mask = df_raw["Type"].isin(f_type) & df_raw["Catégorie"].isin(f_cat)
    df_filtered = df_raw[mask].copy()

    # --- 4. GRAPHIQUE DYNAMIQUE ---
    if not df_filtered.empty:
        # Groupement temporel
        freq_map = {"Jour": "D", "Semaine": "W", "Mois": "ME", "Année": "YE"}
        df_trend = df_filtered.set_index("Date").resample(freq_map[f_periode])["Montant"].sum().reset_index()
        
        fig = px.area(df_trend, x="Date", y="Montant", 
                      color_discrete_sequence=['#fdfdfd'], 
                      title=f"Tendance : {f_periode}")
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, color="white", title=""),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)", color="white", title="Montant (€)"),
            margin=dict(l=0, r=0, t=30, b=0), height=250
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Petit calcul du total filtré
        st.write(f"**Total sur la sélection :** {df_filtered['Montant'].sum():,.2f} €")
    else:
        st.info("Ajustez les filtres pour voir le graphique.")

st.divider()

# --- 5. SAISIE DE TRANSACTION ---
with st.expander("➕ Nouvelle Transaction Détaillée", expanded=False):
    with st.form("form_global", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            d_input = st.date_input("Date", datetime.now())
            t_input = st.selectbox("Type", ["Dépense Variable", "Dépense Fixe", "Revenu"])
            c_input = st.selectbox("Catégorie", ["Transport", "Alimentation", "Habitation", "Loisirs", "Santé", "Revenus", "Autre"])
        with c2:
            m_input = st.number_input("Montant (€)", min_value=0.0, format="%.2f")
            p_input = st.selectbox("Paiement", ["Carte Bancaire", "Virement", "Espèces", "Prélèvement"])
            i_input = st.select_slider("Importance", options=["Superflu", "Utile", "Indispensable"])
        
        desc_input = st.text_input("Description")

        if st.form_submit_button("💰 Enregistrer l'opération"):
            new_row = pd.DataFrame([{
                "Date": pd.to_datetime(d_input),
                "Description": desc_input,
                "Catégorie": c_input,
                "Sous-Catégorie": "Général",
                "Mode de Paiement": p_input,
                "Type": t_input,
                "Importance": i_input,
                "Montant": m_input
            }])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.success("Opération enregistrée")
            st.rerun()

# --- 6. HISTORIQUE ---
st.subheader("📜 Historique")

if not st.session_state.df.empty:
    # Tri par date décroissante pour l'affichage
    df_display = st.session_state.df.sort_values(by="Date", ascending=False)
    
    for index, row in df_display.iterrows():
        # Formatage de la date pour la carte
        d_fmt = row['Date'].strftime("%d %b %Y") if isinstance(row['Date'], datetime) else str(row['Date'])
        
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.8em; opacity: 0.8;">{d_fmt} | {row['Catégorie']}</span>
                <b style="font-size: 1.1em;">{row['Montant']:.2f} €</b>
            </div>
            <div style="margin-top: 5px; font-weight: bold;">{row['Description']}</div>
            <div style="font-size: 0.75em; opacity: 0.7; margin-top: 3px;">
                💳 {row['Mode de Paiement']} • ✨ {row['Importance']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Supprimer", key=f"del_{index}"):
            st.session_state.df = st.session_state.df.drop(index).reset_index(drop=True)
            st.session_state.df.to_csv(DB_FILE, index=False)
            st.rerun()
else:
    st.info("Commencez par ajouter une transaction.")
