import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# -----------------------------
# Configuration page
# -----------------------------

st.set_page_config(
    page_title="Dashboard Dépenses",
    page_icon="💰",
    layout="wide"
)

# Style fond blanc texte noir
st.markdown("""
<style>
body {
    background-color: white;
    color: black;
}
</style>
""", unsafe_allow_html=True)

st.title("💰 Dashboard de suivi des dépenses")

# -----------------------------
# Données exemple
# -----------------------------

data = {
    "Mois": [
        "Janvier","Février","Mars",
        "Avril","Mai","Juin",
        "Juillet","Août","Septembre",
        "Octobre","Novembre","Décembre"
    ],
    "Depenses": [
        1200,900,1500,
        1100,1700,1300,
        1600,1400,1500,
        1800,1700,1900
    ],
    "Categorie":[
        "Loyer","Courses","Transport",
        "Loisirs","Courses","Transport",
        "Vacances","Courses","Transport",
        "Loisirs","Courses","Cadeaux"
    ]
}

df = pd.DataFrame(data)

budget_annuel = 20000
total_depenses = df["Depenses"].sum()

# -----------------------------
# Layout colonnes
# -----------------------------

col1, col2 = st.columns(2)

# -----------------------------
# Jauge Budget
# -----------------------------

with col1:

    st.subheader("Budget utilisé")

    fig_jauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=total_depenses,
        title={'text': "Dépenses totales"},
        gauge={
            'axis': {'range': [None, budget_annuel]},
            'bar': {'color': "black"},
            'bgcolor': "white",
            'steps': [
                {'range': [0, budget_annuel*0.5], 'color': "#e8f5e9"},
                {'range': [budget_annuel*0.5, budget_annuel*0.8], 'color': "#fff3cd"},
                {'range': [budget_annuel*0.8, budget_annuel], 'color': "#f8d7da"}
            ]
        }
    ))

    fig_jauge.update_layout(
        paper_bgcolor="white",
        font=dict(color="black")
    )

    st.plotly_chart(fig_jauge, use_container_width=True)

# -----------------------------
# Répartition dépenses
# -----------------------------

with col2:

    st.subheader("Répartition des dépenses")

    df_cat = df.groupby("Categorie")["Depenses"].sum().reset_index()

    fig_pie = px.pie(
        df_cat,
        values="Depenses",
        names="Categorie",
        hole=0.4
    )

    fig_pie.update_layout(
        paper_bgcolor="white",
        font=dict(color="black")
    )

    st.plotly_chart(fig_pie, use_container_width=True)

# -----------------------------
# Evolution mensuelle
# -----------------------------

st.subheader("Evolution mensuelle des dépenses")

fig_line = px.line(
    df,
    x="Mois",
    y="Depenses",
    markers=True
)

fig_line.update_layout(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(color="black"),
    xaxis_title="Mois",
    yaxis_title="Montant (€)"
)

st.plotly_chart(fig_line, use_container_width=True)

# -----------------------------
# Tableau des données
# -----------------------------

st.subheader("Données")

st.dataframe(df)
