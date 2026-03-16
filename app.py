"""
H&L Budget — Application de suivi des dépenses du foyer
Optimisé avec boutons Modifier/Supprimer intégrés sur la carte.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import secrets, base64, json
from datetime import datetime, date
from io import StringIO
import requests

# ─────────────────────────────────────────────────────
# 1. CONFIG & STYLE
# ─────────────────────────────────────────────────────
st.set_page_config(page_title="H&L Budget", page_icon="💰",
                   layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;800&display=swap');
html, body, [class*="css"] {
    font-family: 'DM Sans', -apple-system, sans-serif;
    background: #F5F4F0 !important;
}
.main .block-container { padding: 0 1rem 5rem; max-width: 480px; }
.hl-header {
    background: #1A1A1A; color: #fff;
    margin: -1rem -1rem 1.25rem;
    padding: 1.5rem 1.25rem 2.75rem;
    border-radius: 0 0 28px 28px;
}
.hl-header small { font-size:11px; opacity:.5; text-transform:uppercase; letter-spacing:.1em; }
.hl-header h2   { font-size:22px; font-weight:800; margin-top:3px; }
.hl-header p    { font-size:13px; opacity:.6; margin-top:3px; }

/* Design de la Carte Transaction */
.card-tx {
    background:#fff; border-radius:18px;
    padding:0.75rem 1rem; margin-bottom:0.5rem;
    box-shadow:0 2px 14px rgba(0,0,0,.07);
    display:flex; align-items:center; gap:12px;
    position: relative;
    border: 1px solid transparent;
}
.tx-icon { 
    width:38px; height:38px; border-radius:11px; 
    display:flex; align-items:center; justify-content:center; 
    font-size:18px; flex-shrink:0; 
}
.tx-desc { flex:1; min-width:0; padding-right: 80px; } /* Espace pour les boutons */
.tx-desc strong { font-size:13px; font-weight:600; color:#1A1A1A; display:block;
                  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.tx-desc span { font-size:11px; color:#bbb; display:block; }
.tx-amt { font-size:14px; font-weight:800; white-space:nowrap; margin-right: 85px; }
.tx-amt.red   { color:#D94040; }
.tx-amt.green { color:#2D6A0F; }

/* Conteneur des Boutons d'action */
.tx-actions-container {
    position: absolute;
    right: 12px;
    display: flex;
    gap: 6px;
    pointer-events: auto;
}

/* Style des boutons Streamlit pour ressembler à la capture */
div.stButton > button.btn-action {
    background-color: #ffffff !important;
    color: #1A1A1A !important;
    border: 1px solid #E8E8E8 !important;
    padding: 4px 8px !important;
    height: 36px !important;
    width: 36px !important;
    border-radius: 10px !important;
    font-size: 16px !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
}
div.stButton > button.btn-action:hover {
    border-color: #1A1A1A !important;
    background-color: #f9f9f9 !important;
}

.auth-logo { text-align:center; padding:2.5rem 0 1.5rem; }
.auth-logo h1 { font-size:36px; font-weight:800; color:#1A1A1A; letter-spacing:-2px; }
.auth-logo p  { font-size:14px; color:#aaa; margin-top:6px; }

/* Bouton principal Enregistrer */
.stButton > button.btn-main {
    width:100%; border-radius:14px !important;
    background:#1A1A1A !important; color:#fff !important;
    border:none !important; padding:13px !important;
    font-size:15px !important; font-weight:700 !important;
}

div[data-baseweb="tab-list"] { background:transparent !important; gap:4px; }
div[data-baseweb="tab"] { border-radius:20px !important; padding:6px 16px !important;
                           font-size:13px !important; font-weight:600 !important; }
div[aria-selected="true"] { background:#1A1A1A !important; color:#fff !important; }
.badge {
    display:inline-block; font-size:10px; font-weight:700; padding:2px 8px;
    border-radius:20px; background:#E8E8E8; color:#666;
    text-transform:uppercase; letter-spacing:.04em;
}
.badge.mine { background:#1A1A1A; color:#fff; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# 2. CONSTANTES & GITHUB (SQUELETTE REQUIS)
# ─────────────────────────────────────────────────────
BUDGET_FILE = "budget_data.csv"
USERS_FILE  = "users.csv"
CATS_FILE   = "categories.json"
COLS_BUDGET = ["id","user_email","date","description","categorie","type","montant","auteur"]
COLS_USERS  = ["email","password"]

DEFAULT_CATEGORIES = {
    "🏠 Logement": ("#F0F0EE", "#1A1A1A"), "🛒 Alimentation": ("#FFF0F0", "#D94040"),
    "🚗 Transport": ("#EEF4FF", "#2563EB"), "🎬 Loisirs": ("#F0FFF4", "#2D6A0F"),
    "🏥 Santé": ("#FFFBEE", "#A16207"), "💰 Salaire": ("#F0FFF4", "#2D6A0F"), "📦 Autre": ("#F8F8F8", "#888"),
}
TYPES = ["Variable", "Fixe", "Revenu"]

def _headers(): return {"Authorization": f"token {st.secrets['GITHUB_TOKEN']}", "Accept": "application/vnd.github.v3+json"}
def _url(f): return f"https://api.github.com/repos/{st.secrets['GITHUB_REPO']}/contents/{f}"

def gh_read(filename):
    r = requests.get(_url(filename), headers=_headers(), timeout=10)
    if r.status_code == 200:
        d = r.json()
        return base64.b64decode(d["content"]).decode("utf-8"), d["sha"]
    return "", ""

def gh_write(filename, content, sha, msg):
    payload = {"message": msg, "content": base64.b64encode(content.encode()).decode()}
    if sha: payload["sha"] = sha
    r = requests.put(_url(filename), headers=_headers(), json=payload, timeout=10)
    return (True, "") if r.status_code in (200, 201) else (False, r.text)

# ─────────────────────────────────────────────────────
# 3. LOGIQUE DONNÉES
# ─────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def read_budget_cached():
    content, sha = gh_read(BUDGET_FILE)
    if content.strip():
        df = pd.read_csv(StringIO(content))
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["montant"] = pd.to_numeric(df["montant"], errors="coerce").fillna(0)
        return df.dropna(subset=["date"]), sha
    return pd.DataFrame(columns=COLS_BUDGET), ""

def write_budget(df, sha):
    read_budget_cached.clear()
    df_s = df.copy()
    if "date" in df_s.columns:
        df_s["date"] = df_s["date"].apply(lambda x: x.strftime("%Y-%m-%d") if hasattr(x, "strftime") else x)
    return gh_write(BUDGET_FILE, df_s.reindex(columns=COLS_BUDGET).to_csv(index=False), sha, "update budget")

def get_cat_style(cat): return DEFAULT_CATEGORIES.get(cat.split(" › ")[0], ("#F8F8F8","#888"))
def get_cat_icon(cat): return (cat.split(" › ")[1] if " › " in cat else cat).split(" ")[0]

# ─────────────────────────────────────────────────────
# 4. SESSION & AUTH (SIMPLIFIÉ)
# ─────────────────────────────────────────────────────
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "editing_id" not in st.session_state: st.session_state.editing_id = None

# ─────────────────────────────────────────────────────
# 5. PAGE DASHBOARD & HISTORIQUE
# ─────────────────────────────────────────────────────
def page_dashboard():
    email = st.session_state.user_email
    st.markdown('<div class="hl-header"><h2>H&L Budget</h2><p>Pilotage du foyer</p></div>', unsafe_allow_html=True)

    tab_home, tab_add, tab_history = st.tabs(["📊 Dashboard", "➕ Ajouter", "📋 Historique"])

    df, sha = read_budget_cached()

    with tab_add:
        st.subheader("Nouvelle dépense")
        with st.form("add_form", clear_on_submit=True):
            desc = st.text_input("Description")
            mt = st.number_input("Montant", min_value=0.01)
            cat = st.selectbox("Catégorie", list(DEFAULT_CATEGORIES.keys()))
            tp = st.selectbox("Type", TYPES)
            dt = st.date_input("Date", date.today())
            if st.form_submit_button("Enregistrer", cls="btn-main"):
                new_row = pd.DataFrame([{"id": secrets.token_hex(4), "user_email": email, "date": dt, 
                                         "description": desc, "categorie": cat, "type": tp, "montant": mt, "auteur": email.split("@")[0]}])
                write_budget(pd.concat([df, new_row]), sha)
                st.rerun()

    with tab_history:
        if df.empty:
            st.info("Aucune transaction.")
        else:
            df = df.sort_values("date", ascending=False)
            for _, row in df.iterrows():
                tx_id = str(row["id"])
                is_rev = row["type"] == "Revenu"
                bg, _ = get_cat_style(row["categorie"])
                icon = get_cat_icon(row["categorie"])
                amt_cls = "green" if is_rev else "red"
                sign = "+" if is_rev else "−"
                is_mine = row["user_email"] == email
                badge_cls = "mine" if is_mine else ""

                # --- CARTE HTML ---
                st.markdown(f"""
                <div class="card-tx">
                    <div class="tx-icon" style="background:{bg}">{icon}</div>
                    <div class="tx-desc">
                        <strong>{row['description']}</strong>
                        <span>{row['date'].strftime('%d/%m/%Y')} · {row['categorie']} <span class="badge {badge_cls}">{row['auteur']}</span></span>
                    </div>
                    <div class="tx-amt {amt_cls}">{sign}{row['montant']:,.2f} €</div>
                </div>
                """, unsafe_allow_html=True)

                # --- BOUTONS FLOTTANTS (STREAMLIT) ---
                # On utilise des colonnes pour positionner les boutons au-dessus de la carte
                c_spacer, c_edit, c_del = st.columns([8, 1.2, 1.2])
                with c_spacer: st.empty()
                with c_edit:
                    if st.button("✏️", key=f"ed_{tx_id}", help="Modifier", cls="btn-action"):
                        st.session_state.editing_id = tx_id if st.session_state.editing_id != tx_id else None
                        st.rerun()
                with c_del:
                    if st.button("🗑️", key=f"del_{tx_id}", help="Supprimer", cls="btn-action"):
                        df_new = df[df["id"].astype(str) != tx_id]
                        write_budget(df_new, sha)
                        st.rerun()
                
                # Petit décalage pour remonter les boutons sur la carte
                st.markdown('<style>div[data-testid="column"]:nth-child(2), div[data-testid="column"]:nth-child(3) { margin-top: -55px; z-index: 10; }</style>', unsafe_allow_html=True)

                # --- ZONE ÉDITION ---
                if st.session_state.editing_id == tx_id:
                    with st.expander("Modifier la transaction", expanded=True):
                        new_desc = st.text_input("Description", value=row["description"], key=f"in_desc_{tx_id}")
                        new_mt = st.number_input("Montant", value=float(row["montant"]), key=f"in_mt_{tx_id}")
                        if st.button("Sauvegarder", key=f"save_{tx_id}"):
                            df.loc[df["id"].astype(str) == tx_id, ["description", "montant"]] = [new_desc, new_mt]
                            write_budget(df, sha)
                            st.session_state.editing_id = None
                            st.rerun()

# ─────────────────────────────────────────────────────
# 6. ROUTAGE
# ─────────────────────────────────────────────────────
if not st.session_state.logged_in:
    # Page Login simplifiée pour le test
    email_test = st.text_input("Email")
    if st.button("Entrer"):
        st.session_state.logged_in = True
        st.session_state.user_email = email_test
        st.rerun()
else:
    page_dashboard()
