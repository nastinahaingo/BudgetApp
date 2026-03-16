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
    "💵 Epargne":      ("#F0FFF4", "#2D6A0F"),
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
for k, v in {"logged_in": False, "user_email": "",
             "editing_id": None, "add_success": False, "edit_success": False,
             "add_desc_val": "", "add_mt_val": 0.01}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────
# 9. PAGE AUTH
# ─────────────────────────────────────────────────────
def page_auth():
    st.markdown('<div class="auth-logo"><h1>H&L</h1><p>Votre budget familial</p></div>',
                unsafe_allow_html=True)

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

    tab_home, tab_add, tab_history, tab_import, tab_account = st.tabs(
        ["📊 Dashboard", "➕ Ajouter", "📋 Historique", "📥 Importer", "👤 Compte"])

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

            st.markdown('<div class="sec-label">Évolution</div>', unsafe_allow_html=True)

            gc1, gc2, gc3 = st.columns([2, 2, 3])
            with gc1:
                periode_label = st.selectbox(
                    "Période", ["Jour", "Semaine", "Mois", "Année"],
                    index=2, key="chart_period", label_visibility="collapsed")
            with gc2:
                affichage_label = st.selectbox(
                    "Affichage", ["Dépenses", "Revenus", "Les deux"],
                    index=0, key="chart_display", label_visibility="collapsed")
            with gc3:
                cats_graph = ["Toutes"] + sorted(set(
                    get_cat_base(c) for c in df["categorie"].dropna().unique()))
                sel_cat_graph = st.selectbox(
                    "Catégorie", cats_graph, key="chart_cat", label_visibility="collapsed")

            periode_map = {
                "Jour":    ("D",  "%d/%m"),
                "Semaine": ("W",  "S%W %b"),
                "Mois":    ("ME", "%b %Y"),
                "Année":   ("YE", "%Y"),
            }
            resample_rule, tick_fmt = periode_map[periode_label]
            n_periods = {"Jour": 30, "Semaine": 12, "Mois": 12, "Année": 5}[periode_label]

            df_graph = df.copy()
            if sel_cat_graph != "Toutes":
                df_graph = df_graph[df_graph["categorie"].apply(get_cat_base) == sel_cat_graph]

            fig_line = go.Figure()

            if affichage_label in ("Dépenses", "Les deux"):
                dep_trend = (
                    df_graph[df_graph["type"] != "Revenu"]
                    .set_index("date").resample(resample_rule)["montant"]
                    .sum().reset_index().tail(n_periods)
                )
                if not dep_trend.empty:
                    fig_line.add_trace(go.Scatter(
                        x=dep_trend["date"], y=dep_trend["montant"],
                        name="Dépenses", mode="lines+markers",
                        line=dict(color="#D94040", width=2.5),
                        marker=dict(size=6, color="#D94040"),
                        fill="tozeroy" if affichage_label == "Dépenses" else "none",
                        fillcolor="rgba(217,64,64,0.07)",
                    ))

            if affichage_label in ("Revenus", "Les deux"):
                rev_trend = (
                    df_graph[df_graph["type"] == "Revenu"]
                    .set_index("date").resample(resample_rule)["montant"]
                    .sum().reset_index().tail(n_periods)
                )
                if not rev_trend.empty:
                    fig_line.add_trace(go.Scatter(
                        x=rev_trend["date"], y=rev_trend["montant"],
                        name="Revenus", mode="lines+markers",
                        line=dict(color="#2D6A0F", width=2.5),
                        marker=dict(size=6, color="#2D6A0F"),
                        fill="tozeroy" if affichage_label == "Revenus" else "none",
                        fillcolor="rgba(45,106,15,0.07)",
                    ))

            fig_line.update_layout(
                height=220,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10, b=10, l=10, r=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                            xanchor="right", x=1, font=dict(size=11)),
                xaxis=dict(showgrid=False, tickformat=tick_fmt, zeroline=False),
                yaxis=dict(showgrid=True, gridcolor="#F0F0F0", zeroline=False,
                           ticksuffix=" €"),
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
        st.markdown("### Nouvelle opération")

        if st.session_state.get("add_success"):
            st.success("✅ Transaction enregistrée avec succès !")
            st.session_state.add_success = False

        desc = st.text_input("Description", placeholder="Ex : Courses Leclerc",
                             key="add_desc", value=st.session_state.get("add_desc_val",""))
        mt   = st.number_input("Montant (€)", min_value=0.01, step=0.01,
                               format="%.2f", key="add_mt",
                               value=st.session_state.get("add_mt_val", 0.01))
        cat, sous_cat, nouvelle_cat = cat_selector("add")
        tp   = st.selectbox("Type", TYPES, key="add_tp")
        dt   = st.date_input("Date", value=date.today(), key="add_dt")

        if st.button("Enregistrer ✓", use_container_width=True, key="add_sub"):
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
                    st.session_state.add_success  = True
                    st.session_state.add_desc_val = ""
                    st.session_state.add_mt_val   = 0.01
                    for k in list(st.session_state.keys()):
                        if k.startswith("add_") and k not in (
                                "add_success","add_desc_val","add_mt_val"):
                            del st.session_state[k]
                    st.rerun()
                else:
                    st.error(f"Erreur : {err}")

    # ══ HISTORIQUE ═══════════════════════════════════
    with tab_history:
        if st.session_state.get("edit_success"):
            st.success("✅ Transaction modifiée avec succès !")
            st.session_state.edit_success = False

        if df.empty:
            st.info("Aucune transaction enregistrée.")
        else:
            with st.expander("🔍 Filtres", expanded=False):
                auteurs      = ["Tous"] + sorted(df["auteur"].dropna().unique().tolist())
                sel_auteur   = st.selectbox("Auteur", auteurs, key="f_auteur")
                sel_type     = st.selectbox("Type", ["Tous"] + TYPES, key="f_type")
                cats_dispo   = sorted(set(get_cat_base(c) for c in df["categorie"].dropna().unique()))
                sel_cat      = st.selectbox("Catégorie", ["Toutes"] + cats_dispo, key="f_cat")
                sel_sous     = None
                if sel_cat == "🚗 Transport":
                    sous_dispo = sorted(set(
                        get_cat_sous(c) for c in df["categorie"].dropna()
                        if get_cat_base(c) == "🚗 Transport" and get_cat_sous(c)))
                    if sous_dispo:
                        sel_sous = st.selectbox("Sous-catégorie",
                                                ["Toutes"] + sous_dispo, key="f_sous")

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

            # ── Styles boutons icône ──────────────────────────────
            st.markdown("""
            <style>
            .tx-actions > div[data-testid="stHorizontalBlock"] {
                gap: 6px !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            /* Bouton modifier — fond orange clair, icône crayon */
            .btn-modifier button {
                background: #FFF3E0 !important;
                color: #E65100 !important;
                border: none !important;
                border-radius: 10px !important;
                font-size: 16px !important;
                min-height: 34px !important;
                height: 34px !important;
                width: 34px !important;
                padding: 0 !important;
                line-height: 1 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            .btn-modifier button:hover {
                background: #FFE0B2 !important;
                opacity: 1 !important;
            }
            /* Bouton supprimer — fond gris clair, icône poubelle */
            .btn-supprimer button {
                background: #F5F5F5 !important;
                color: #9E9E9E !important;
                border: none !important;
                border-radius: 10px !important;
                font-size: 16px !important;
                min-height: 34px !important;
                height: 34px !important;
                width: 34px !important;
                padding: 0 !important;
                line-height: 1 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            .btn-supprimer button:hover {
                background: #FFEBEE !important;
                color: #D94040 !important;
                opacity: 1 !important;
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
                is_editing_this = st.session_state.editing_id == tx_id

                amt_color = "#2D6A0F" if is_rev else "#D94040"
                # Icône du bouton modifier selon état (✕ si en cours d'édition)
                edit_icon = "✕" if is_editing_this else "✏️"

                st.markdown(f"""
                <div style="background:#fff;border-radius:16px;
                     padding:.75rem 1rem .75rem;
                     margin-bottom:.1rem;
                     box-shadow:0 2px 14px rgba(0,0,0,.07);
                     display:flex;align-items:center;gap:10px">
                  <div style="width:36px;height:36px;border-radius:10px;background:{bg};
                       display:flex;align-items:center;justify-content:center;
                       font-size:18px;flex-shrink:0">{icon}</div>
                  <div style="flex:1;min-width:0">
                    <div style="font-size:13px;font-weight:600;color:#1A1A1A;
                         white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                      {row['description']}</div>
                    <div style="font-size:11px;color:#bbb;margin-top:2px">
                      {row['date'].strftime('%d/%m/%Y')} · {row['categorie']} · {row['type']}
                      {badge}</div>
                  </div>
                  <div style="font-size:14px;font-weight:800;color:{amt_color};
                       white-space:nowrap;margin-right:8px">
                    {sign}{row['montant']:,.2f} €</div>
                  <div style="display:flex;gap:4px;flex-shrink:0">
                    <span style="width:34px;height:34px"></span>
                    <span style="width:34px;height:34px"></span>
                  </div>
                </div>""", unsafe_allow_html=True)

                st.markdown(f"""
                <style>
                [data-testid="stHorizontalBlock"]:has(> [data-testid="column"] #e_{tx_id}) {{
                    position: relative;
                    margin-top: -44px !important;
                    margin-bottom: 0 !important;
                    background: transparent !important;
                    pointer-events: none;
                }}
                </style>""", unsafe_allow_html=True)

                col_spacer, col_e, col_d = st.columns([10, 1, 1])
                with col_spacer:
                    st.markdown("")
                with col_e:
                    st.markdown('<div class="btn-modifier">', unsafe_allow_html=True)
                    if st.button(edit_icon, key=f"e_{tx_id}", use_container_width=True):
                        st.session_state.editing_id = None if is_editing_this else tx_id
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with col_d:
                    st.markdown('<div class="btn-supprimer">', unsafe_allow_html=True)
                    if st.button("🗑️", key=f"d_{tx_id}", use_container_width=True):
                        _, fresh_sha = gh_read(BUDGET_FILE)
                        full_df, _   = read_budget_cached()
                        full_df      = full_df[full_df["id"].astype(str) != tx_id]
                        ok, err      = write_budget(full_df, fresh_sha or _)
                        if ok: st.rerun()
                        else:  st.error(f"Erreur : {err}")
                    st.markdown('</div>', unsafe_allow_html=True)

                # ── Bloc modifier inline ──
                if is_editing_this:
                    r            = row
                    default_base = get_cat_base(r["categorie"])
                    default_sous = get_cat_sous(r["categorie"])
                    st.markdown("""
                    <div style="background:#F5F4F0;border-radius:0 0 16px 16px;
                         padding:1rem 1.1rem;margin-top:-4px;margin-bottom:.75rem;
                         border:1.5px solid #E8E8E8;border-top:none">
                    """, unsafe_allow_html=True)
                    ed_desc = st.text_input("Description", value=r["description"],
                                            key=f"ed_desc_{tx_id}")
                    ed_mt   = st.number_input("Montant (€)", value=float(r["montant"]),
                                              min_value=0.01, step=0.01, format="%.2f",
                                              key=f"ed_mt_{tx_id}")
                    ed_cat, ed_sous, ed_nouvelle = cat_selector(
                        f"ed_{tx_id}", default_cat=default_base, default_sous=default_sous)
                    tp_idx  = TYPES.index(r["type"]) if r["type"] in TYPES else 0
                    ed_tp   = st.selectbox("Type", TYPES, index=tp_idx, key=f"ed_tp_{tx_id}")
                    ed_dt   = st.date_input("Date",
                                            value=r["date"].date() if hasattr(r["date"],"date")
                                            else date.today(), key=f"ed_dt_{tx_id}")
                    if st.button("💾 Enregistrer la modification", key=f"ed_save_{tx_id}",
                                 use_container_width=True):
                        if not ed_desc.strip():
                            st.warning("Description vide.")
                        else:
                            cat_finale = resolve_cat(ed_cat, ed_sous, ed_nouvelle)
                            full_df, sha = read_budget_cached()
                            _, fresh_sha = gh_read(BUDGET_FILE)
                            if fresh_sha: sha = fresh_sha
                            full_df.loc[full_df["id"].astype(str)==tx_id,"description"] = ed_desc.strip()
                            full_df.loc[full_df["id"].astype(str)==tx_id,"montant"]     = ed_mt
                            full_df.loc[full_df["id"].astype(str)==tx_id,"categorie"]   = cat_finale
                            full_df.loc[full_df["id"].astype(str)==tx_id,"type"]        = ed_tp
                            full_df.loc[full_df["id"].astype(str)==tx_id,"date"]        = ed_dt.strftime("%Y-%m-%d")
                            ok, err = write_budget(full_df, sha)
                            if ok:
                                st.session_state.editing_id   = None
                                st.session_state.edit_success = True
                                st.rerun()
                            else:
                                st.error(f"Erreur : {err}")
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='margin-bottom:.5rem'></div>",
                                unsafe_allow_html=True)

    # ══ IMPORTER CSV ═════════════════════════════════
    with tab_import:
        st.markdown("### 📥 Importer un fichier CSV")
        st.markdown("""
        <div class="card">
            <div style="font-size:12px;color:#888;line-height:1.8">
                <b style="color:#1A1A1A">Colonnes reconnues :</b><br>
                <code>date</code> · <code>description</code> · <code>categorie</code>
                · <code>type</code> · <code>montant</code><br><br>
                <b style="color:#1A1A1A">Formats acceptés :</b><br>
                • Date : <code>DD/MM/YYYY</code> ou <code>YYYY-MM-DD</code><br>
                • Type : <code>Variable</code>, <code>Fixe</code> ou <code>Revenu</code><br>
                • Montant : nombre positif (ex: <code>250.00</code> ou <code>250,00</code>)<br>
                • Séparateur : virgule <code>,</code> ou point-virgule <code>;</code>
            </div>
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader("Choisir un fichier CSV", type=["csv"])

        if uploaded:
            try:
                raw = uploaded.read().decode("utf-8-sig")
                sep = ";" if raw.count(";") > raw.count(",") else ","
                df_imp = pd.read_csv(StringIO(raw), sep=sep)
                df_imp.columns = [c.strip().lower() for c in df_imp.columns]

                required = {"date", "description", "montant"}
                missing  = required - set(df_imp.columns)
                if missing:
                    st.error(f"Colonnes manquantes : {', '.join(missing)}")
                else:
                    df_imp["montant"] = (
                        df_imp["montant"].astype(str)
                        .str.replace(",", ".", regex=False)
                        .str.replace("[^0-9.]", "", regex=True)
                    )
                    df_imp["montant"] = pd.to_numeric(df_imp["montant"], errors="coerce").fillna(0)
                    df_imp["date"] = pd.to_datetime(
                        df_imp["date"], dayfirst=True, errors="coerce")
                    df_imp = df_imp.dropna(subset=["date"])
                    df_imp["date"] = df_imp["date"].dt.strftime("%Y-%m-%d")

                    if "categorie" not in df_imp.columns: df_imp["categorie"] = "📦 Autre"
                    if "type"      not in df_imp.columns: df_imp["type"]      = "Variable"

                    type_map = {
                        "variable": "Variable", "fixe": "Fixe", "revenu": "Revenu",
                        "income": "Revenu", "fixed": "Fixe"
                    }
                    df_imp["type"] = df_imp["type"].astype(str).str.strip().str.lower().map(
                        type_map).fillna("Variable")
                    df_imp["description"] = df_imp["description"].astype(str).str.strip()

                    st.markdown(f'<div class="sec-label">{len(df_imp)} ligne(s) détectée(s)</div>',
                                unsafe_allow_html=True)

                    preview = df_imp[["date","description","categorie","type","montant"]].head(10).copy()
                    preview.columns = ["Date","Description","Catégorie","Type","Montant (€)"]
                    st.dataframe(preview, use_container_width=True, hide_index=True)

                    if len(df_imp) > 10:
                        st.caption(f"… et {len(df_imp)-10} ligne(s) supplémentaire(s)")

                    full_df, sha = read_budget_cached()
                    existing_descs = set()
                    if not full_df.empty:
                        existing_descs = set(
                            full_df["description"].astype(str) + "|" +
                            full_df["date"].astype(str).str[:10])
                    new_descs = df_imp["description"].astype(str) + "|" + df_imp["date"].astype(str)
                    doublons  = new_descs.isin(existing_descs).sum()
                    if doublons:
                        st.warning(f"⚠️ {doublons} ligne(s) semblent déjà exister (même description + date).")

                    col_imp, col_skip = st.columns(2)
                    with col_imp:
                        if st.button("✅ Importer tout", use_container_width=True):
                            _, fresh_sha = gh_read(BUDGET_FILE)
                            if fresh_sha: sha = fresh_sha
                            new_rows = pd.DataFrame([{
                                "id":          secrets.token_hex(8),
                                "user_email":  email,
                                "date":        row["date"],
                                "description": row["description"],
                                "categorie":   row["categorie"],
                                "type":        row["type"],
                                "montant":     row["montant"],
                                "auteur":      email.split("@")[0],
                            } for _, row in df_imp.iterrows()])
                            ok, err = write_budget(
                                pd.concat([full_df, new_rows], ignore_index=True), sha)
                            if ok:
                                st.success(f"✅ {len(df_imp)} transaction(s) importée(s) !")
                                st.rerun()
                            else:
                                st.error(f"Erreur : {err}")
                    with col_skip:
                        if st.button("⏭ Ignorer les doublons", use_container_width=True):
                            _, fresh_sha = gh_read(BUDGET_FILE)
                            if fresh_sha: sha = fresh_sha
                            df_new_only = df_imp[~new_descs.isin(existing_descs)]
                            if df_new_only.empty:
                                st.info("Aucune nouvelle transaction à importer.")
                            else:
                                new_rows = pd.DataFrame([{
                                    "id":          secrets.token_hex(8),
                                    "user_email":  email,
                                    "date":        row["date"],
                                    "description": row["description"],
                                    "categorie":   row["categorie"],
                                    "type":        row["type"],
                                    "montant":     row["montant"],
                                    "auteur":      email.split("@")[0],
                                } for _, row in df_new_only.iterrows()])
                                ok, err = write_budget(
                                    pd.concat([full_df, new_rows], ignore_index=True), sha)
                                if ok:
                                    st.success(f"✅ {len(df_new_only)} transaction(s) importée(s) (doublons ignorés).")
                                    st.rerun()
                                else:
                                    st.error(f"Erreur : {err}")

            except Exception as e:
                st.error(f"Erreur de lecture du fichier : {e}")

        st.markdown('<div class="sec-label">Modèle à télécharger</div>', unsafe_allow_html=True)
        template = "date,description,categorie,type,montant\n16/03/2026,Loyer,🏠 Logement,Fixe,1200\n16/03/2026,Salaire,💰 Salaire,Revenu,2500\n16/03/2026,Courses,🛒 Alimentation,Variable,120.50"
        st.download_button(
            label="📄 Télécharger le modèle CSV",
            data=template,
            file_name="modele_budget.csv",
            mime="text/csv",
            use_container_width=True,
        )

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
