"""
H&L Budget — Application de suivi des dépenses du foyer
Stack : Streamlit Cloud · CSV stockés sur GitHub

SECRETS (Streamlit Cloud > Manage app > Settings > Secrets) :
  GITHUB_TOKEN = "ghp_..."
  GITHUB_REPO  = "votre_user/nom_du_repo"
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
.card {
    background:#fff; border-radius:18px;
    padding:1rem 1.1rem; margin-bottom:.65rem;
    box-shadow:0 2px 14px rgba(0,0,0,.07);
}
.metric-row { display:flex; gap:8px; margin-bottom:.75rem; }
.metric-box {
    flex:1; background:#fff; border-radius:14px;
    padding:.75rem .5rem; text-align:center;
    box-shadow:0 2px 14px rgba(0,0,0,.07);
}
.metric-label { font-size:10px; text-transform:uppercase; letter-spacing:.06em; color:#aaa; display:block; }
.metric-val   { font-size:17px; font-weight:800; color:#1A1A1A; display:block; margin-top:3px; }
.metric-val.green { color:#2D6A0F; }
.metric-val.red   { color:#D94040; }
.tx { display:flex; align-items:center; gap:12px; padding:.6rem 0; border-bottom:.5px solid #F2F2F2; }
.tx:last-child { border-bottom:none; }
.tx-icon { width:38px; height:38px; border-radius:11px; display:flex;
           align-items:center; justify-content:center; font-size:18px; flex-shrink:0; }
.tx-desc { flex:1; min-width:0; }
.tx-desc strong { font-size:13px; font-weight:600; color:#1A1A1A; display:block;
                  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.tx-desc span { font-size:11px; color:#bbb; display:block; }
.tx-amt { font-size:14px; font-weight:800; white-space:nowrap; }
.tx-amt.red   { color:#D94040; }
.tx-amt.green { color:#2D6A0F; }
.auth-logo { text-align:center; padding:2.5rem 0 1.5rem; }
.auth-logo h1 { font-size:36px; font-weight:800; color:#1A1A1A; letter-spacing:-2px; }
.auth-logo p  { font-size:14px; color:#aaa; margin-top:6px; }
.stButton > button {
    width:100%; border-radius:14px !important;
    background:#1A1A1A !important; color:#fff !important;
    border:none !important; padding:13px !important;
    font-size:15px !important; font-weight:700 !important;
}
.stButton > button:hover { opacity:.82; }
div[data-testid="stForm"] { background:transparent; border:none; padding:0; }
.stTextInput input, .stNumberInput input, .stSelectbox select, .stDateInput input {
    border-radius:12px !important; border:1.5px solid #E8E8E8 !important;
    font-size:15px !important; padding:12px 14px !important; background:#fff !important;
}
.stAlert { border-radius:12px !important; font-size:14px !important; }
.sec-label { font-size:11px; font-weight:700; text-transform:uppercase;
             letter-spacing:.08em; color:#bbb; margin:1.1rem 0 .5rem; }
div[data-baseweb="tab-list"] { background:transparent !important; gap:4px; }
div[data-baseweb="tab"] { border-radius:20px !important; padding:6px 16px !important;
                           font-size:13px !important; font-weight:600 !important; }
div[aria-selected="true"] { background:#1A1A1A !important; color:#fff !important; }
.badge {
    display:inline-block; font-size:10px; font-weight:700; padding:2px 8px;
    border-radius:20px; background:#E8E8E8; color:#666;
    text-transform:uppercase; letter-spacing:.04em; max-width:fit-content;
}
.badge.mine { background:#1A1A1A; color:#fff; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# 2. CONSTANTES
# ─────────────────────────────────────────────────────
BUDGET_FILE = "budget_data.csv"
USERS_FILE  = "users.csv"
CATS_FILE   = "categories.json"

COLS_BUDGET = ["id","user_email","date","description","categorie","type","montant","auteur"]
COLS_USERS  = ["email","password"]

DEFAULT_CATEGORIES = {
    "🏠 Logement":     ("#F0F0EE", "#1A1A1A"),
    "🛒 Alimentation": ("#FFF0F0", "#D94040"),
    "🚗 Transport":    ("#EEF4FF", "#2563EB"),
    "🎬 Loisirs":      ("#F0FFF4", "#2D6A0F"),
    "🏥 Santé":        ("#FFFBEE", "#A16207"),
    "💰 Salaire":      ("#F0FFF4", "#2D6A0F"),
    "📦 Autre":        ("#F8F8F8", "#888"),
}

DEFAULT_TRANSPORT_SOUS_CAT = [
    "🚗 Voiture", "⛽ Carburant", "🅿️ Stationnement",
    "🚇 Transports en commun", "✈️ Avion", "🚕 Taxi / VTC",
    "🚲 Vélo", "🛣️ Péage / Autoroute", "🔧 Entretien véhicule",
]

TYPES    = ["Variable", "Fixe", "Revenu"]
MONTH_FR = ["Janvier","Février","Mars","Avril","Mai","Juin",
            "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
PALETTE  = [
    ("#FFF0F8","#C026D3"),("#FFF7ED","#EA580C"),("#F0F9FF","#0284C7"),
    ("#FDF4FF","#9333EA"),("#ECFDF5","#059669"),("#FFF1F2","#E11D48"),
]


# ─────────────────────────────────────────────────────
# 3. GITHUB
# ─────────────────────────────────────────────────────
def _headers():
    return {"Authorization": f"token {st.secrets['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github.v3+json"}

def _url(f):
    return f"https://api.github.com/repos/{st.secrets['GITHUB_REPO']}/contents/{f}"

def gh_read(filename):
    r = requests.get(_url(filename), headers=_headers(), timeout=10)
    if r.status_code == 200:
        d = r.json()
        return base64.b64decode(d["content"]).decode("utf-8"), d["sha"]
    return "", ""

def gh_write(filename, content, sha, msg):
    current_sha = sha
    if not current_sha:
        _, current_sha = gh_read(filename)
    payload = {"message": msg,
               "content": base64.b64encode(content.encode()).decode()}
    if current_sha:
        payload["sha"] = current_sha
    r = requests.put(_url(filename), headers=_headers(), json=payload, timeout=10)
    if r.status_code in (200, 201):
        return True, ""
    try:    detail = r.json().get("message", r.text)
    except: detail = r.text
    return False, f"GitHub {r.status_code} : {detail}"


# ─────────────────────────────────────────────────────
# 4. CATÉGORIES PERSONNALISÉES
# ─────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def read_custom_cats_cached():
    content, _ = gh_read(CATS_FILE)
    if content.strip():
        try: return json.loads(content)
        except: pass
    return {"extra_categories": [], "extra_transport": []}

def save_custom_cats(data):
    read_custom_cats_cached.clear()
    _, sha = gh_read(CATS_FILE)
    return gh_write(CATS_FILE, json.dumps(data, ensure_ascii=False, indent=2), sha, "update categories")

def get_all_categories():
    cats = dict(DEFAULT_CATEGORIES)
    for i, label in enumerate(read_custom_cats_cached().get("extra_categories", [])):
        if label not in cats:
            cats[label] = PALETTE[i % len(PALETTE)]
    return cats

def get_all_transport_sous_cat():
    base  = list(DEFAULT_TRANSPORT_SOUS_CAT)
    extra = read_custom_cats_cached().get("extra_transport", [])
    return base + [x for x in extra if x not in base]

def get_cat_style(cat):
    base = cat.split(" › ")[0] if " › " in cat else cat
    return get_all_categories().get(base, ("#F8F8F8","#888"))

def get_cat_icon(cat):
    part = cat.split(" › ")[1] if " › " in cat else cat
    return part.split(" ")[0] if part else "📦"

def get_cat_base(cat):
    return cat.split(" › ")[0] if " › " in cat else cat

def get_cat_sous(cat):
    return cat.split(" › ")[1] if " › " in cat else None


# ─────────────────────────────────────────────────────
# 5. DONNÉES
# ─────────────────────────────────────────────────────
def read_users():
    content, sha = gh_read(USERS_FILE)
    if content.strip():
        df = pd.read_csv(StringIO(content))
        for c in COLS_USERS:
            if c not in df.columns: df[c] = ""
        return df, sha
    empty = pd.DataFrame(columns=COLS_USERS)
    ok, err = gh_write(USERS_FILE, empty.to_csv(index=False), "", "init users.csv")
    if not ok: st.error(f"Impossible de créer users.csv : {err}")
    return empty, ""

def write_users(df, sha):
    return gh_write(USERS_FILE, df.to_csv(index=False), sha, "update users")

@st.cache_data(ttl=10)
def read_budget_cached():
    content, sha = gh_read(BUDGET_FILE)
    if content.strip():
        df = pd.read_csv(StringIO(content))
        for c in COLS_BUDGET:
            if c not in df.columns: df[c] = ""
        df["date"]    = pd.to_datetime(df["date"], errors="coerce")
        df["montant"] = pd.to_numeric(df["montant"], errors="coerce").fillna(0)
        df = df.dropna(subset=["date"])
        return df, sha
    empty = pd.DataFrame(columns=COLS_BUDGET)
    gh_write(BUDGET_FILE, empty.to_csv(index=False), "", "init budget_data.csv")
    return empty, ""

def write_budget(df, sha):
    read_budget_cached.clear()
    df_s = df.copy()
    if "date" in df_s.columns:
        df_s["date"] = df_s["date"].apply(
            lambda x: x.strftime("%Y-%m-%d") if hasattr(x, "strftime") else x)
    return gh_write(BUDGET_FILE,
                    df_s.reindex(columns=COLS_BUDGET).to_csv(index=False),
                    sha, "update budget_data")


# ─────────────────────────────────────────────────────
# 6. AUTH
# ─────────────────────────────────────────────────────
def register(email, pwd, pwd2):
    email = email.strip().lower()
    if "@" not in email: return False, "Email invalide."
    if len(pwd) < 6:     return False, "Mot de passe trop court (6 car. min.)."
    if pwd != pwd2:      return False, "Les mots de passe ne correspondent pas."
    df, sha = read_users()
    if not df.empty and email in df["email"].astype(str).values:
        return False, "Un compte existe déjà avec cet email."
    updated = pd.concat([df, pd.DataFrame([[email, pwd]], columns=COLS_USERS)], ignore_index=True)
    ok, err = write_users(updated, sha)
    return (True, "Compte créé ! Connectez-vous.") if ok else (False, f"Erreur : {err}")

def login(email, pwd):
    email = email.strip().lower()
    df, _ = read_users()
    if df.empty: return False, "Identifiants incorrects."
    if df[(df["email"].astype(str)==email) & (df["password"].astype(str)==pwd)].empty:
        return False, "Identifiants incorrects."
    return True, "OK"


# ─────────────────────────────────────────────────────
# 7. FORMULAIRE CATÉGORIE (réutilisé pour ajout ET édition)
# ─────────────────────────────────────────────────────
def cat_selector(key_prefix="", default_cat=None, default_sous=None):
    """
    Affiche selectbox catégorie + sous-catégorie transport + champs 'Autre'.
    Retourne (cat_finale, sous_cat_finale_ou_None).
    """
    CATS   = get_all_categories()
    TRANS  = get_all_transport_sous_cat()
    opts   = list(CATS.keys())

    idx_cat = opts.index(default_cat) if default_cat and default_cat in opts else 0
    cat     = st.selectbox("Catégorie", opts, index=idx_cat, key=f"{key_prefix}_cat")

    sous_cat     = None
    nouvelle_cat = None

    if cat == "🚗 Transport":
        sc_opts = TRANS + ["➕ Ajouter une sous-catégorie..."]
        idx_sc  = TRANS.index(default_sous) if default_sous and default_sous in TRANS else 0
        sc_sel  = st.selectbox("Sous-catégorie", sc_opts, index=idx_sc, key=f"{key_prefix}_sc")
        if sc_sel == "➕ Ajouter une sous-catégorie...":
            sous_cat = st.text_input("Nouvelle sous-catégorie",
                                     placeholder="Ex: 🛵 Scooter", key=f"{key_prefix}_sc_new")
        else:
            sous_cat = sc_sel

    if cat == "📦 Autre":
        nouvelle_cat = st.text_input("Nom de la nouvelle catégorie",
                                     placeholder="Ex: 🐾 Animaux", key=f"{key_prefix}_newcat")
        st.caption("Sauvegardée pour tous les futurs ajouts.")

    return cat, sous_cat, nouvelle_cat


def resolve_cat(cat, sous_cat, nouvelle_cat):
    """
    Sauvegarde les nouvelles catégories/sous-catégories et retourne le label final.
    """
    cat_finale = cat

    if cat == "📦 Autre" and nouvelle_cat and nouvelle_cat.strip():
        label = nouvelle_cat.strip()
        data  = read_custom_cats_cached()
        if label not in data["extra_categories"]:
            data["extra_categories"].append(label)
            save_custom_cats(data)
        cat_finale = label

    elif cat == "🚗 Transport":
        if sous_cat and sous_cat.strip():
            sc = sous_cat.strip()
            if sc not in DEFAULT_TRANSPORT_SOUS_CAT:
                data = read_custom_cats_cached()
                if sc not in data.get("extra_transport", []):
                    data.setdefault("extra_transport", []).append(sc)
                    save_custom_cats(data)
            cat_finale = f"🚗 Transport › {sc}"

    return cat_finale


# ─────────────────────────────────────────────────────
# 8. SESSION
# ─────────────────────────────────────────────────────
for k, v in {"logged_in": False, "user_email": "", "auth_mode": "login",
             "editing_id": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────
# 9. PAGE AUTH
# ─────────────────────────────────────────────────────
def page_auth():
    st.markdown('<div class="auth-logo"><h1>H&L</h1><p>Votre budget familial</p></div>',
                unsafe_allow_html=True)
    mode = st.session_state.auth_mode

    if mode == "login":
        with st.form("fl"):
            email = st.text_input("Adresse email", placeholder="vous@example.com")
            pwd   = st.text_input("Mot de passe", type="password")
            sub   = st.form_submit_button("Se connecter")
        if sub:
            ok, msg = login(email, pwd)
            if ok:
                st.session_state.logged_in  = True
                st.session_state.user_email = email.strip().lower()
                st.rerun()
            else:
                st.error(msg)
        if st.button("Créer un compte"):
            st.session_state.auth_mode = "register"; st.rerun()

    elif mode == "register":
        st.markdown("### Créer un compte")
        with st.form("fr"):
            email = st.text_input("Adresse email")
            pwd1  = st.text_input("Mot de passe (6 car. min.)", type="password")
            pwd2  = st.text_input("Confirmer", type="password")
            sub   = st.form_submit_button("Créer mon compte")
        if sub:
            ok, msg = register(email, pwd1, pwd2)
            if ok:
                st.success(msg); st.session_state.auth_mode = "login"; st.rerun()
            else:
                st.error(msg)
        if st.button("← Retour"):
            st.session_state.auth_mode = "login"; st.rerun()


# ─────────────────────────────────────────────────────
# 10. PAGE DASHBOARD
# ─────────────────────────────────────────────────────
def page_dashboard():
    email     = st.session_state.user_email
    user_name = email.split("@")[0].capitalize()
    now       = datetime.now()

    st.markdown(f"""
    <div class="hl-header">
        <small>{MONTH_FR[now.month-1]} {now.year}</small>
        <h2>Bonjour {user_name} 👋</h2>
        <p>Budget partagé du foyer</p>
    </div>""", unsafe_allow_html=True)

    tab_home, tab_add, tab_history, tab_account = st.tabs(
        ["📊 Dashboard", "➕ Ajouter", "📋 Historique", "👤 Compte"])

    # Charge TOUTES les transactions (tous utilisateurs du foyer)
    df_all, _ = read_budget_cached()
    df = df_all.copy() if not df_all.empty else pd.DataFrame()
    if not df.empty:
        df = df.sort_values("date", ascending=False)

    # ══ DASHBOARD ════════════════════════════════════
    with tab_home:
        if df.empty:
            st.info("Aucune transaction. Commencez par en ajouter une !")
        else:
            df_m = df[(df["date"].dt.month == now.month) &
                      (df["date"].dt.year  == now.year)]
            rev  = df_m[df_m["type"] == "Revenu"]["montant"].sum()
            dep  = df_m[df_m["type"] != "Revenu"]["montant"].sum()
            sold = rev - dep
            sc   = "green" if sold >= 0 else "red"
            sg   = "+" if sold >= 0 else "−"

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="metric-box"><span class="metric-label">Revenus</span>'
                            f'<span class="metric-val green">+{rev:,.0f} €</span></div>',
                            unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="metric-box"><span class="metric-label">Dépenses</span>'
                            f'<span class="metric-val red">−{dep:,.0f} €</span></div>',
                            unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="metric-box"><span class="metric-label">Solde</span>'
                            f'<span class="metric-val {sc}">{sg}{abs(sold):,.0f} €</span></div>',
                            unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            df_dep = df_m[df_m["type"] != "Revenu"].copy()
            if not df_dep.empty:
                df_dep["cat_base"] = df_dep["categorie"].apply(get_cat_base)
                st.markdown('<div class="sec-label">Répartition des dépenses</div>',
                            unsafe_allow_html=True)
                totals  = df_dep.groupby("cat_base")["montant"].sum().reset_index()
                fig_pie = px.pie(totals, values="montant", names="cat_base", hole=0.45,
                                 color_discrete_sequence=["#1A1A1A","#D94040","#2563EB",
                                                          "#2D6A0F","#A16207","#888",
                                                          "#C026D3","#EA580C","#0284C7"])
                fig_pie.update_traces(textposition="inside", textinfo="percent+label",
                                      textfont_size=11)
                fig_pie.update_layout(showlegend=False, height=260,
                                      paper_bgcolor="rgba(0,0,0,0)",
                                      margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig_pie, use_container_width=True)

            st.markdown('<div class="sec-label">Évolution des dépenses (6 mois)</div>',
                        unsafe_allow_html=True)
            trend = (df[df["type"] != "Revenu"]
                     .set_index("date").resample("ME")["montant"]
                     .sum().reset_index().tail(6))
            fig_line = go.Figure(go.Scatter(
                x=trend["date"], y=trend["montant"], mode="lines+markers",
                line=dict(color="#1A1A1A", width=2.5),
                marker=dict(size=7, color="#1A1A1A"),
                fill="tozeroy", fillcolor="rgba(26,26,26,0.07)",
            ))
            fig_line.update_layout(
                height=190, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10,b=10,l=10,r=10),
                xaxis=dict(showgrid=False, tickformat="%b", zeroline=False),
                yaxis=dict(showgrid=True, gridcolor="#F0F0F0", zeroline=False),
            )
            st.plotly_chart(fig_line, use_container_width=True)

            st.markdown('<div class="sec-label">Dernières opérations</div>',
                        unsafe_allow_html=True)
            html = '<div class="card">'
            for _, row in df.head(5).iterrows():
                is_rev  = row["type"] == "Revenu"
                bg, _   = get_cat_style(row["categorie"])
                icon    = get_cat_icon(row["categorie"])
                amt_cls = "green" if is_rev else "red"
                sign    = "+" if is_rev else "−"
                is_mine = str(row.get("user_email","")) == email
                badge   = f'<span class="badge {"mine" if is_mine else ""}">{row["auteur"]}</span>'
                html   += f"""
                <div class="tx">
                  <div class="tx-icon" style="background:{bg}">{icon}</div>
                  <div class="tx-desc">
                    <strong>{row['description']}</strong>
                    <span>{row['date'].strftime('%d/%m')} · {row['categorie']} {badge}</span>
                  </div>
                  <span class="tx-amt {amt_cls}">{sign}{row['montant']:,.2f} €</span>
                </div>"""
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

    # ══ AJOUTER ══════════════════════════════════════
    with tab_add:
        editing_id = st.session_state.editing_id

        if editing_id:
            # ── MODE ÉDITION ──
            st.markdown("### ✏️ Modifier la transaction")
            row_edit = df[df["id"].astype(str) == editing_id]
            if row_edit.empty:
                st.warning("Transaction introuvable.")
                st.session_state.editing_id = None
                st.rerun()
            else:
                r = row_edit.iloc[0]
                default_base = get_cat_base(r["categorie"])
                default_sous = get_cat_sous(r["categorie"])

                with st.form("fedit", clear_on_submit=False):
                    desc = st.text_input("Description", value=r["description"])
                    mt   = st.number_input("Montant (€)", value=float(r["montant"]),
                                           min_value=0.01, step=0.01, format="%.2f")
                    cat, sous_cat, nouvelle_cat = cat_selector(
                        "edit", default_cat=default_base, default_sous=default_sous)
                    tp_idx = TYPES.index(r["type"]) if r["type"] in TYPES else 0
                    tp   = st.selectbox("Type", TYPES, index=tp_idx)
                    dt   = st.date_input("Date", value=r["date"].date()
                                         if hasattr(r["date"], "date") else date.today())
                    col1, col2 = st.columns(2)
                    with col1: save_edit = st.form_submit_button("💾 Enregistrer")
                    with col2: cancel    = st.form_submit_button("Annuler")

                if cancel:
                    st.session_state.editing_id = None; st.rerun()

                if save_edit:
                    cat_finale = resolve_cat(cat, sous_cat, nouvelle_cat)
                    full_df, sha = read_budget_cached()
                    _, fresh_sha = gh_read(BUDGET_FILE)
                    if fresh_sha: sha = fresh_sha
                    full_df.loc[full_df["id"].astype(str) == editing_id, "description"] = desc.strip()
                    full_df.loc[full_df["id"].astype(str) == editing_id, "montant"]     = mt
                    full_df.loc[full_df["id"].astype(str) == editing_id, "categorie"]   = cat_finale
                    full_df.loc[full_df["id"].astype(str) == editing_id, "type"]        = tp
                    full_df.loc[full_df["id"].astype(str) == editing_id, "date"]        = dt.strftime("%Y-%m-%d")
                    ok, err = write_budget(full_df, sha)
                    if ok:
                        st.success("✅ Transaction modifiée !")
                        st.session_state.editing_id = None
                        st.rerun()
                    else:
                        st.error(f"Erreur : {err}")
        else:
            # ── MODE AJOUT ──
            st.markdown("### Nouvelle opération")
            with st.form("fa", clear_on_submit=True):
                desc = st.text_input("Description", placeholder="Ex : Courses Leclerc")
                mt   = st.number_input("Montant (€)", min_value=0.01, step=0.01, format="%.2f")
                cat, sous_cat, nouvelle_cat = cat_selector("add")
                tp   = st.selectbox("Type", TYPES)
                dt   = st.date_input("Date", value=date.today())
                sub  = st.form_submit_button("Enregistrer ✓")

            if sub:
                if not desc.strip():
                    st.warning("Veuillez saisir une description.")
                else:
                    cat_finale   = resolve_cat(cat, sous_cat, nouvelle_cat)
                    full_df, sha = read_budget_cached()
                    _, fresh_sha = gh_read(BUDGET_FILE)
                    if fresh_sha: sha = fresh_sha
                    new_row = pd.DataFrame([{
                        "id":          secrets.token_hex(8),
                        "user_email":  email,
                        "date":        dt.strftime("%Y-%m-%d"),
                        "description": desc.strip(),
                        "categorie":   cat_finale,
                        "type":        tp,
                        "montant":     mt,
                        "auteur":      email.split("@")[0],
                    }])
                    ok, err = write_budget(pd.concat([full_df, new_row], ignore_index=True), sha)
                    if ok:
                        st.success("✅ Enregistré !")
                        st.rerun()
                    else:
                        st.error(f"Erreur : {err}")

    # ══ HISTORIQUE ═══════════════════════════════════
    with tab_history:
        if df.empty:
            st.info("Aucune transaction enregistrée.")
        else:
            # ── Filtres ──
            with st.expander("🔍 Filtres", expanded=False):
                # Filtre Auteur
                auteurs      = ["Tous"] + sorted(df["auteur"].dropna().unique().tolist())
                sel_auteur   = st.selectbox("Auteur", auteurs, key="f_auteur")

                # Filtre Type
                sel_type     = st.selectbox("Type", ["Tous"] + TYPES, key="f_type")

                # Filtre Catégorie de base
                cats_dispo   = sorted(set(get_cat_base(c) for c in df["categorie"].dropna().unique()))
                sel_cat      = st.selectbox("Catégorie", ["Toutes"] + cats_dispo, key="f_cat")

                # Filtre Sous-catégorie (uniquement si Transport sélectionné)
                sel_sous     = None
                if sel_cat == "🚗 Transport":
                    sous_dispo = sorted(set(
                        get_cat_sous(c) for c in df["categorie"].dropna()
                        if get_cat_base(c) == "🚗 Transport" and get_cat_sous(c)))
                    if sous_dispo:
                        sel_sous = st.selectbox("Sous-catégorie",
                                                ["Toutes"] + sous_dispo, key="f_sous")

            # ── Application des filtres ──
            df_f = df.copy()
            if sel_auteur != "Tous":
                df_f = df_f[df_f["auteur"] == sel_auteur]
            if sel_type != "Tous":
                df_f = df_f[df_f["type"] == sel_type]
            if sel_cat != "Toutes":
                df_f = df_f[df_f["categorie"].apply(get_cat_base) == sel_cat]
            if sel_sous and sel_sous != "Toutes":
                df_f = df_f[df_f["categorie"].apply(
                    lambda x: get_cat_sous(x) == sel_sous)]

            st.markdown(f'<div class="sec-label">{len(df_f)} transaction(s)</div>',
                        unsafe_allow_html=True)

            st.markdown("""
            <style>
            .btn-modifier > div > button, .btn-modifier > button {
                background: #F5F4F0 !important; color: #1A1A1A !important;
                border: none !important; border-radius: 10px !important;
                width: 36px !important; height: 36px !important;
                padding: 0 !important; font-size: 16px !important;
                min-height: 36px !important; line-height: 1 !important;
            }
            .btn-supprimer > div > button, .btn-supprimer > button {
                background: #FFF0F0 !important; color: #D94040 !important;
                border: none !important; border-radius: 10px !important;
                width: 36px !important; height: 36px !important;
                padding: 0 !important; font-size: 16px !important;
                min-height: 36px !important; line-height: 1 !important;
            }
            </style>
            """, unsafe_allow_html=True)

            for _, row in df_f.iterrows():
                is_rev  = row["type"] == "Revenu"
                bg, _   = get_cat_style(row["categorie"])
                icon    = get_cat_icon(row["categorie"])
                amt_cls = "green" if is_rev else "red"
                sign    = "+" if is_rev else "−"
                tx_id   = str(row["id"])
                is_mine = str(row.get("user_email","")) == email
                badge   = f'<span class="badge {"mine" if is_mine else ""}">{row["auteur"]}</span>'

                # Carte + 2 petits boutons icône sur la même ligne
                col_card, col_e, col_d = st.columns([10, 1, 1])
                with col_card:
                    st.markdown(f"""
                    <div class="card" style="margin-bottom:0">
                      <div class="tx" style="padding:.1rem 0">
                        <div class="tx-icon" style="background:{bg}">{icon}</div>
                        <div class="tx-desc">
                          <strong>{row['description']}</strong>
                          <span>{row['date'].strftime('%d/%m/%Y')} · {row['categorie']} · {row['type']}</span>
                          <span>{badge}</span>
                        </div>
                        <span class="tx-amt {amt_cls}">{sign}{row['montant']:,.2f} €</span>
                      </div>
                    </div>""", unsafe_allow_html=True)
                with col_e:
                    st.markdown('<div class="btn-modifier">', unsafe_allow_html=True)
                    if st.button("✏️", key=f"e_{tx_id}"):
                        st.session_state.editing_id = tx_id
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with col_d:
                    st.markdown('<div class="btn-supprimer">', unsafe_allow_html=True)
                    if st.button("🗑", key=f"d_{tx_id}"):
                        _, fresh_sha = gh_read(BUDGET_FILE)
                        full_df, _   = read_budget_cached()
                        full_df      = full_df[full_df["id"].astype(str) != tx_id]
                        ok, err      = write_budget(full_df, fresh_sha or _)
                        if ok: st.rerun()
                        else:  st.error(f"Erreur : {err}")
                    st.markdown('</div>', unsafe_allow_html=True)

    # ══ COMPTE ═══════════════════════════════════════
    with tab_account:
        st.markdown(f"""
        <div class="card" style="text-align:center;padding:1.75rem">
            <div style="font-size:42px;margin-bottom:.5rem">👤</div>
            <div style="font-weight:800;font-size:16px;color:#1A1A1A">{email}</div>
            <div style="font-size:12px;color:#aaa;margin-top:4px">Compte actif</div>
        </div>""", unsafe_allow_html=True)

        df_u, _ = read_users()
        if not df_u.empty:
            row_u = df_u[df_u["email"].astype(str) == email]
            if not row_u.empty:
                with st.expander("🔑 Voir mes identifiants"):
                    st.markdown(f"""
                    <div class="card">
                        <div style="margin-bottom:.75rem">
                            <span style="font-size:11px;color:#aaa;text-transform:uppercase;
                                  letter-spacing:.06em">Email</span>
                            <div style="font-weight:700;font-size:15px;margin-top:2px">{email}</div>
                        </div>
                        <div>
                            <span style="font-size:11px;color:#aaa;text-transform:uppercase;
                                  letter-spacing:.06em">Mot de passe</span>
                            <div style="font-weight:700;font-size:15px;margin-top:2px;
                                 font-family:monospace">{row_u.iloc[0]['password']}</div>
                        </div>
                    </div>""", unsafe_allow_html=True)

        with st.expander("🗂 Gérer mes catégories personnalisées"):
            custom = read_custom_cats_cached()
            st.markdown('<div class="sec-label">Catégories</div>', unsafe_allow_html=True)
            for i, c in enumerate(custom.get("extra_categories", [])):
                cc, cx = st.columns([5,1])
                with cc: st.markdown(f"<div style='padding:6px 0;font-size:14px'>{c}</div>",
                                     unsafe_allow_html=True)
                with cx:
                    if st.button("🗑", key=f"delcat_{i}"):
                        custom["extra_categories"].pop(i)
                        save_custom_cats(custom); st.rerun()
            if not custom.get("extra_categories"):
                st.caption("Aucune catégorie personnalisée.")

            st.markdown('<div class="sec-label">Sous-catégories Transport</div>',
                        unsafe_allow_html=True)
            for i, c in enumerate(custom.get("extra_transport", [])):
                cc, cx = st.columns([5,1])
                with cc: st.markdown(f"<div style='padding:6px 0;font-size:14px'>{c}</div>",
                                     unsafe_allow_html=True)
                with cx:
                    if st.button("🗑", key=f"deltrans_{i}"):
                        custom["extra_transport"].pop(i)
                        save_custom_cats(custom); st.rerun()
            if not custom.get("extra_transport"):
                st.caption("Aucune sous-catégorie personnalisée.")

        if not df.empty:
            st.markdown('<div class="sec-label">Statistiques globales du foyer</div>',
                        unsafe_allow_html=True)
            td = df[df["type"] != "Revenu"]["montant"].sum()
            tr = df[df["type"] == "Revenu"]["montant"].sum()
            nb = len(df)
            st.markdown(f"""
            <div class="metric-row">
              <div class="metric-box">
                <span class="metric-label">Dépenses</span>
                <span class="metric-val red">{td:,.0f} €</span>
              </div>
              <div class="metric-box">
                <span class="metric-label">Revenus</span>
                <span class="metric-val green">{tr:,.0f} €</span>
              </div>
              <div class="metric-box">
                <span class="metric-label">Opérations</span>
                <span class="metric-val">{nb}</span>
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Se déconnecter"):
            st.session_state.logged_in  = False
            st.session_state.user_email = ""
            st.rerun()


# ─────────────────────────────────────────────────────
# 11. ROUTAGE
# ─────────────────────────────────────────────────────
if st.session_state.logged_in:
    page_dashboard()
else:
    page_auth()
