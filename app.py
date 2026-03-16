"""
H&L Budget — Version Finale avec boutons alignés sur la carte
Stack : Streamlit Cloud + GitHub CSV
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import secrets, base64, json, requests
from datetime import datetime, date
from io import StringIO

# ─────────────────────────────────────────────────────
# 1. CONFIG & STYLE (OPTIMISÉ POUR L'ALIGNEMENT)
# ─────────────────────────────────────────────────────
st.set_page_config(page_title="H&L Budget", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;800&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background: #F5F4F0 !important; }

/* Conteneur de la carte */
.card-tx {
    background:#fff; border-radius:18px;
    padding: 0.9rem 1.1rem; margin-bottom: 0.5rem;
    box-shadow: 0 2px 14px rgba(0,0,0,.07);
    display: flex; align-items: center; position: relative;
    border: 1px solid transparent;
}

.tx-icon { 
    width:40px; height:40px; border-radius:12px; 
    display:flex; align-items:center; justify-content:center; 
    font-size:20px; flex-shrink:0; margin-right: 12px;
}

.tx-info { flex-grow: 1; min-width: 0; }
.tx-info strong { display: block; font-size: 13px; font-weight:700; color: #1A1A1A; margin-bottom: 2px; }
.tx-info span { font-size: 11px; color: #bbb; display: block; line-height: 1.2; }

.tx-amt { 
    font-size: 14px; font-weight: 800; 
    margin-right: 95px; /* Espace crucial pour laisser place aux boutons */
    white-space: nowrap;
}

/* Style des boutons d'action (Crayon et Poubelle) */
div.stButton > button {
    border-radius: 10px !important;
    padding: 0px !important;
    height: 36px !important;
    width: 36px !important;
    background-color: white !important;
    color: #1A1A1A !important;
    border: 1px solid #EAEAEA !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    transition: all 0.2s ease;
}
div.stButton > button:hover { border-color: #1A1A1A !important; background: #f9f9f9 !important; }

/* LE SECRET DE L'ALIGNEMENT : Remonte le bloc de boutons sur la carte */
[data-testid="stHorizontalBlock"]:has(button[key^="ed_"]) {
    margin-top: -53px !important; 
    margin-bottom: 22px !important;
    position: relative;
    z-index: 10;
}

.badge-user {
    background: #1A1A1A; color: white; padding: 2px 10px;
    border-radius: 12px; font-size: 10px; font-weight: 800;
    margin-top: 6px; display: inline-block; text-transform: uppercase;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
# 2. FONCTIONS GITHUB & DATA
# ─────────────────────────────────────────────────────
BUDGET_FILE = "budget_data.csv"
COLS_BUDGET = ["id","user_email","date","description","categorie","type","montant","auteur"]

def _headers():
    return {"Authorization": f"token {st.secrets['GITHUB_TOKEN']}", "Accept": "application/vnd.github.v3+json"}

def _url():
    return f"https://api.github.com/repos/{st.secrets['GITHUB_REPO']}/contents/{BUDGET_FILE}"

def gh_read():
    r = requests.get(_url(), headers=_headers())
    if r.status_code == 200:
        d = r.json()
        return base64.b64decode(d["content"]).decode("utf-8"), d["sha"]
    return "", ""

def gh_write(df, sha):
    content = df.to_csv(index=False)
    payload = {"message": "update", "content": base64.b64encode(content.encode()).decode(), "sha": sha}
    requests.put(_url(), headers=_headers(), json=payload)

@st.cache_data(ttl=5)
def load_data():
    content, sha = gh_read()
    if content:
        df = pd.read_csv(StringIO(content))
        df["date"] = pd.to_datetime(df["date"])
        return df, sha
    return pd.DataFrame(columns=COLS_BUDGET), ""

# ─────────────────────────────────────────────────────
# 3. INTERFACE HISTORIQUE
# ─────────────────────────────────────────────────────
def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = True # Pour le test
        st.session_state.user_email = "test@hl.com"

    df, sha = load_data()
    
    st.title("H&L Budget")
    
    # --- Formulaire d'ajout rapide (Optionnel) ---
    with st.expander("➕ Ajouter une opération"):
        with st.form("add"):
            d = st.text_input("Description")
            m = st.number_input("Montant", min_value=0.0)
            if st.form_submit_button("Enregistrer"):
                new = pd.DataFrame([{"id": secrets.token_hex(4), "date": date.today(), "description": d, 
                                     "categorie": "📦 Autre", "type": "Variable", "montant": m, 
                                     "auteur": "ADMIN", "user_email": st.session_state.user_email}])
                gh_write(pd.concat([df, new]), sha)
                st.cache_data.clear()
                st.rerun()

    st.markdown(f"**{len(df)} TRANSACTION(S)**")

    if not df.empty:
        df = df.sort_values("date", ascending=False)
        for _, row in df.iterrows():
            tx_id = str(row["id"])
            is_rev = row["type"] == "Revenu"
            color = "#2D6A0F" if is_rev else "#D94040"
            sign = "+" if is_rev else "-"
            bg = "#F0FFF4" if is_rev else "#F8F8F8"
            icon = "💰" if is_rev else "🛒"

            # 1. Rendu de la carte HTML
            st.markdown(f"""
            <div class="card-tx">
                <div class="tx-icon" style="background:{bg}">{icon}</div>
                <div class="tx-info">
                    <strong>{row['description']}</strong>
                    <span>{row['date'].strftime('%d/%m/%Y')} · {row['categorie']}</span>
                    <span class="badge-user">{row['auteur']}</span>
                </div>
                <div class="tx-amt" style="color:{color}">{sign}{row['montant']:,.2f} €</div>
            </div>
            """, unsafe_allow_html=True)

            # 2. Boutons flottants alignés
            # Utilisation de colonnes Streamlit avec décalage CSS
            c_space, c_ed, c_del = st.columns([10, 1.1, 1.1])
            with c_space: st.empty()
            with c_ed:
                if st.button("✏️", key=f"ed_{tx_id}"):
                    st.toast(f"Mode édition pour : {row['description']}")
            with c_del:
                if st.button("🗑️", key=f"del_{tx_id}"):
                    new_df = df[df["id"].astype(str) != tx_id]
                    gh_write(new_df, sha)
                    st.cache_data.clear()
                    st.rerun()

if __name__ == "__main__":
    main()
