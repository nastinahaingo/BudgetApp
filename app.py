"""
H&L Budget — Application de suivi des dépenses du foyer
Stack : Streamlit Cloud · CSV stockés sur GitHub · Outlook SMTP

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECRETS À CONFIGURER (Streamlit Cloud > Manage app > Settings > Secrets)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EMAIL_ADDRESS  = "votre_adresse@outlook.com"
EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"     ← mot de passe d'application Outlook
GITHUB_TOKEN   = "ghp_..."                 ← Personal Access Token (scope: repo)
GITHUB_REPO    = "votre_user/nom_du_repo"
APP_URL        = "https://votre-app.streamlit.app"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FICHIERS dans le repo GitHub (créés automatiquement au 1er lancement) :
  budget_data.csv  →  transactions
  users.csv        →  comptes utilisateurs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hashlib, secrets, smtplib, base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
from io import StringIO
import requests


# ─────────────────────────────────────────────────────
# 1. CONFIG & STYLE MOBILE-FIRST
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
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# 2. CONSTANTES
# ─────────────────────────────────────────────────────
BUDGET_FILE = "budget_data.csv"   # ← ton fichier existant dans le repo
USERS_FILE  = "users.csv"

COLS_BUDGET = ["id","user_email","date","description","categorie","type","montant","auteur"]
COLS_USERS  = ["email","password_hash","salt","token","token_expiry"]

CATEGORIES = {
    "🏠 Logement":     ("#F0F0EE", "#1A1A1A"),
    "🛒 Alimentation": ("#FFF0F0", "#D94040"),
    "🚗 Transport":    ("#EEF4FF", "#2563EB"),
    "🎬 Loisirs":      ("#F0FFF4", "#2D6A0F"),
    "🏥 Santé":        ("#FFFBEE", "#A16207"),
    "📦 Autre":        ("#F8F8F8", "#888"),
}
TYPES = ["Variable", "Fixe", "Revenu"]
MONTH_FR = ["Janvier","Février","Mars","Avril","Mai","Juin",
            "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]


# ─────────────────────────────────────────────────────
# 3. GITHUB — LECTURE / ÉCRITURE CSV
# ─────────────────────────────────────────────────────
def _gh_headers() -> dict:
    return {
        "Authorization": f"token {st.secrets['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github.v3+json",
    }

def _gh_base() -> str:
    return f"https://api.github.com/repos/{st.secrets['GITHUB_REPO']}/contents"


def _gh_read(filename: str) -> tuple[str, str]:
    """Lit un fichier GitHub. Retourne (contenu_csv, sha)."""
    r = requests.get(f"{_gh_base()}/{filename}", headers=_gh_headers(), timeout=10)
    if r.status_code == 200:
        data = r.json()
        return base64.b64decode(data["content"]).decode("utf-8"), data["sha"]
    return "", ""


def _gh_write(filename: str, content: str, sha: str, msg: str) -> bool:
    """Écrit (crée ou met à jour) un fichier sur GitHub."""
    payload = {
        "message": msg,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(f"{_gh_base()}/{filename}",
                     headers=_gh_headers(), json=payload, timeout=10)
    return r.status_code in (200, 201)


@st.cache_data(ttl=8)
def _load(filename: str, columns: list) -> tuple[pd.DataFrame, str]:
    """Charge un CSV depuis GitHub, le crée s'il est absent."""
    content, sha = _gh_read(filename)
    if content.strip():
        df = pd.read_csv(StringIO(content))
        for col in columns:          # ajoute colonnes manquantes sans casser l'existant
            if col not in df.columns:
                df[col] = ""
        return df, sha
    # Fichier absent → on le crée vide sur GitHub
    empty = pd.DataFrame(columns=columns)
    _gh_write(filename, empty.to_csv(index=False), "", f"init {filename}")
    return empty, ""


def _save(filename: str, df: pd.DataFrame, sha: str, columns: list, msg: str) -> None:
    _load.clear()
    df_save = df.copy()
    for col in df_save.columns:
        if "date" in col.lower() and df_save[col].dtype != object:
            df_save[col] = df_save[col].apply(
                lambda x: x.strftime("%Y-%m-%d") if hasattr(x, "strftime") else x)
    _gh_write(filename, df_save.reindex(columns=columns).to_csv(index=False), sha, msg)


# Raccourcis publics
def get_users() -> tuple[pd.DataFrame, str]:
    return _load(USERS_FILE, COLS_USERS)

def get_budget() -> tuple[pd.DataFrame, str]:
    df, sha = _load(BUDGET_FILE, COLS_BUDGET)
    if not df.empty:
        df["date"]    = pd.to_datetime(df["date"], errors="coerce")
        df["montant"] = pd.to_numeric(df["montant"], errors="coerce").fillna(0)
        df = df.dropna(subset=["date"])
    return df, sha

def save_users(df, sha):  _save(USERS_FILE,  df, sha, COLS_USERS,  "update users")
def save_budget(df, sha): _save(BUDGET_FILE, df, sha, COLS_BUDGET, "update budget_data")


# ─────────────────────────────────────────────────────
# 4. SÉCURITÉ — MOT DE PASSE
# ─────────────────────────────────────────────────────
def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return key.hex(), salt

def verify_password(password: str, stored: str, salt: str) -> bool:
    computed, _ = hash_password(password, salt)
    return secrets.compare_digest(computed, stored)


# ─────────────────────────────────────────────────────
# 5. EMAIL — OUTLOOK SMTP
# ─────────────────────────────────────────────────────
def _send(to: str, subject: str, html: str) -> bool:
    try:
        sender = st.secrets["EMAIL_ADDRESS"]
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"H&L Budget <{sender}>"
        msg["To"]      = to
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP("smtp-mail.outlook.com", 587, timeout=15) as s:
            s.starttls()
            s.login(sender, st.secrets["EMAIL_PASSWORD"])
            s.sendmail(sender, to, msg.as_string())
        return True
    except Exception as e:
        st.warning(f"Email non envoyé : {e}")
        return False

def email_bienvenue(to: str):
    _send(to, "Bienvenue sur H&L Budget 🎉", f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;
                background:#fff;border-radius:16px">
        <h1 style="font-size:28px;font-weight:800;color:#1A1A1A">H&L Budget</h1>
        <p style="color:#666;font-size:15px;line-height:1.7">
            Votre compte a été créé avec succès.<br>
            Adresse : <strong>{to}</strong>
        </p>
        <p style="color:#bbb;font-size:12px;margin-top:24px">H&L Budget · Application familiale</p>
    </div>""")

def email_reset(to: str, token: str):
    url = f"{st.secrets.get('APP_URL','http://localhost:8501')}?reset_token={token}"
    _send(to, "Réinitialisation de votre mot de passe", f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;
                background:#fff;border-radius:16px">
        <h1 style="font-size:28px;font-weight:800;color:#1A1A1A">H&L Budget</h1>
        <p style="color:#666;font-size:15px;line-height:1.7">
            Lien valable <strong>30 minutes</strong> :
        </p>
        <a href="{url}" style="display:inline-block;margin:20px 0;background:#1A1A1A;
           color:#fff;padding:14px 28px;border-radius:12px;font-weight:700;
           text-decoration:none;font-size:15px">
           Réinitialiser mon mot de passe →
        </a>
        <p style="color:#bbb;font-size:12px">
            Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.
        </p>
    </div>""")


# ─────────────────────────────────────────────────────
# 6. LOGIQUE AUTH
# ─────────────────────────────────────────────────────
def register(email: str, pwd: str, pwd2: str) -> tuple[bool, str]:
    email = email.strip().lower()
    if "@" not in email:      return False, "Adresse email invalide."
    if len(pwd) < 8:          return False, "Mot de passe trop court (8 car. min.)."
    if pwd != pwd2:           return False, "Les mots de passe ne correspondent pas."
    df, sha = get_users()
    if not df.empty and email in df["email"].values:
        return False, "Un compte existe déjà avec cet email."
    h, s = hash_password(pwd)
    row  = pd.DataFrame([[email, h, s, "", ""]], columns=COLS_USERS)
    save_users(pd.concat([df, row], ignore_index=True), sha)
    email_bienvenue(email)
    return True, "Compte créé ! Connectez-vous."

def login(email: str, pwd: str) -> tuple[bool, str]:
    email = email.strip().lower()
    df, _ = get_users()
    if df.empty: return False, "Identifiants incorrects."
    row = df[df["email"] == email]
    if row.empty: return False, "Identifiants incorrects."
    r = row.iloc[0]
    if not verify_password(pwd, str(r["password_hash"]), str(r["salt"])):
        return False, "Identifiants incorrects."
    return True, "OK"

def forgot(email: str) -> str:
    email = email.strip().lower()
    df, sha = get_users()
    if df.empty or email not in df["email"].values:
        return "Si cette adresse est connue, un lien vous a été envoyé."   # message neutre
    token  = secrets.token_urlsafe(32)
    expiry = (datetime.now() + timedelta(minutes=30)).isoformat()
    df.loc[df["email"] == email, "token"]        = token
    df.loc[df["email"] == email, "token_expiry"] = expiry
    save_users(df, sha)
    email_reset(email, token)
    return "Lien envoyé ! Vérifiez votre boîte de réception."

def do_reset(token: str, pwd: str, pwd2: str) -> tuple[bool, str]:
    if pwd != pwd2:  return False, "Les mots de passe ne correspondent pas."
    if len(pwd) < 8: return False, "Mot de passe trop court (8 car. min.)."
    df, sha = get_users()
    if df.empty or "token" not in df.columns:
        return False, "Lien invalide ou expiré."
    row = df[df["token"] == token]
    if row.empty: return False, "Lien invalide ou expiré."
    try:
        if datetime.fromisoformat(str(row.iloc[0]["token_expiry"])) < datetime.now():
            return False, "Ce lien a expiré. Faites une nouvelle demande."
    except Exception:
        return False, "Lien invalide."
    h, s = hash_password(pwd)
    df.loc[df["token"] == token, ["password_hash","salt","token","token_expiry"]] = h, s, "", ""
    save_users(df, sha)
    return True, "Mot de passe mis à jour ! Connectez-vous."


# ─────────────────────────────────────────────────────
# 7. SESSION
# ─────────────────────────────────────────────────────
for k, v in {"logged_in": False, "user_email": "",
             "auth_mode": "login", "reset_token": ""}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Détection token reset dans l'URL
rt = st.query_params.get("reset_token", "")
if rt and not st.session_state.logged_in:
    st.session_state.auth_mode   = "reset"
    st.session_state.reset_token = rt


# ─────────────────────────────────────────────────────
# 8. PAGE AUTH
# ─────────────────────────────────────────────────────
def page_auth():
    st.markdown('<div class="auth-logo"><h1>H&L</h1><p>Votre budget familial</p></div>',
                unsafe_allow_html=True)
    mode = st.session_state.auth_mode

    # ── Connexion ──
    if mode == "login":
        with st.form("fl"):
            email = st.text_input("Adresse email", placeholder="vous@outlook.com")
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
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Mot de passe oublié ?"):
                st.session_state.auth_mode = "forgot"; st.rerun()
        with c2:
            if st.button("Créer un compte"):
                st.session_state.auth_mode = "register"; st.rerun()

    # ── Inscription ──
    elif mode == "register":
        st.markdown("### Créer un compte")
        with st.form("fr"):
            email = st.text_input("Adresse email")
            pwd1  = st.text_input("Mot de passe (8 car. min.)", type="password")
            pwd2  = st.text_input("Confirmer le mot de passe", type="password")
            sub   = st.form_submit_button("Créer mon compte")
        if sub:
            ok, msg = register(email, pwd1, pwd2)
            (st.success if ok else st.error)(msg)
            if ok: st.session_state.auth_mode = "login"
        if st.button("← Retour"):
            st.session_state.auth_mode = "login"; st.rerun()

    # ── Mot de passe oublié ──
    elif mode == "forgot":
        st.markdown("### Mot de passe oublié")
        st.info("Un lien valable 30 minutes vous sera envoyé par email.")
        with st.form("ff"):
            email = st.text_input("Adresse email")
            sub   = st.form_submit_button("Envoyer le lien")
        if sub:
            st.success(forgot(email))
        if st.button("← Retour"):
            st.session_state.auth_mode = "login"; st.rerun()

    # ── Reset MDP (depuis lien email) ──
    elif mode == "reset":
        st.markdown("### Nouveau mot de passe")
        with st.form("frs"):
            pwd1 = st.text_input("Nouveau mot de passe (8 car. min.)", type="password")
            pwd2 = st.text_input("Confirmer le mot de passe", type="password")
            sub  = st.form_submit_button("Enregistrer")
        if sub:
            ok, msg = do_reset(st.session_state.reset_token, pwd1, pwd2)
            (st.success if ok else st.error)(msg)
            if ok:
                st.query_params.clear()
                st.session_state.auth_mode = "login"; st.rerun()


# ─────────────────────────────────────────────────────
# 9. PAGE DASHBOARD
# ─────────────────────────────────────────────────────
def page_dashboard():
    email     = st.session_state.user_email
    user_name = email.split("@")[0].capitalize()
    now       = datetime.now()

    st.markdown(f"""
    <div class="hl-header">
        <small>{MONTH_FR[now.month-1]} {now.year}</small>
        <h2>Bonjour {user_name} 👋</h2>
        <p>Votre budget du mois</p>
    </div>""", unsafe_allow_html=True)

    tab_home, tab_add, tab_history, tab_account = st.tabs(
        ["📊 Dashboard", "➕ Ajouter", "📋 Historique", "👤 Compte"])

    # Charge TOUTES les transactions puis filtre sur l'utilisateur connecté
    df_all, sha_budget = get_budget()
    df = pd.DataFrame()
    if not df_all.empty and "user_email" in df_all.columns:
        df = df_all[df_all["user_email"] == email].copy()
        df = df.sort_values("date", ascending=False)

    # ══ DASHBOARD ════════════════════════════════════
    with tab_home:
        if df.empty:
            st.info("Aucune transaction. Commencez par en ajouter une !")
        else:
            df_m = df[(df["date"].dt.month == now.month) & (df["date"].dt.year == now.year)]
            rev  = df_m[df_m["type"] == "Revenu"]["montant"].sum()
            dep  = df_m[df_m["type"] != "Revenu"]["montant"].sum()
            sold = rev - dep
            sc   = "green" if sold >= 0 else "red"
            sg   = "+" if sold >= 0 else "−"

            # Métriques
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

            # Camembert dépenses du mois
            df_dep = df_m[df_m["type"] != "Revenu"]
            if not df_dep.empty:
                st.markdown('<div class="sec-label">Répartition des dépenses</div>',
                            unsafe_allow_html=True)
                totals  = df_dep.groupby("categorie")["montant"].sum().reset_index()
                fig_pie = px.pie(
                    totals, values="montant", names="categorie", hole=0.45,
                    color_discrete_sequence=["#1A1A1A","#D94040","#2563EB",
                                             "#2D6A0F","#A16207","#888"])
                fig_pie.update_traces(textposition="inside", textinfo="percent+label",
                                      textfont_size=11)
                fig_pie.update_layout(showlegend=False, height=260,
                                      paper_bgcolor="rgba(0,0,0,0)",
                                      margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig_pie, use_container_width=True)

            # Courbe évolution mensuelle (6 derniers mois)
            st.markdown('<div class="sec-label">Évolution des dépenses (6 mois)</div>',
                        unsafe_allow_html=True)
            trend = (df[df["type"] != "Revenu"]
                     .set_index("date").resample("ME")["montant"]
                     .sum().reset_index().tail(6))
            fig_line = go.Figure(go.Scatter(
                x=trend["date"], y=trend["montant"],
                mode="lines+markers",
                line=dict(color="#1A1A1A", width=2.5),
                marker=dict(size=7, color="#1A1A1A"),
                fill="tozeroy", fillcolor="rgba(26,26,26,0.07)",
            ))
            fig_line.update_layout(
                height=190, paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10,b=10,l=10,r=10),
                xaxis=dict(showgrid=False, tickformat="%b", zeroline=False),
                yaxis=dict(showgrid=True, gridcolor="#F0F0F0", zeroline=False),
            )
            st.plotly_chart(fig_line, use_container_width=True)

            # 5 dernières opérations
            st.markdown('<div class="sec-label">Dernières opérations</div>',
                        unsafe_allow_html=True)
            html = '<div class="card">'
            for _, row in df.head(5).iterrows():
                is_rev  = row["type"] == "Revenu"
                bg, _   = CATEGORIES.get(row["categorie"], ("#F8F8F8","#888"))
                icon    = row["categorie"].split(" ")[0]
                amt_cls = "green" if is_rev else "red"
                sign    = "+" if is_rev else "−"
                html   += f"""
                <div class="tx">
                  <div class="tx-icon" style="background:{bg}">{icon}</div>
                  <div class="tx-desc">
                    <strong>{row['description']}</strong>
                    <span>{row['date'].strftime('%d/%m')} · {row['categorie']}</span>
                  </div>
                  <span class="tx-amt {amt_cls}">{sign}{row['montant']:,.2f} €</span>
                </div>"""
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

    # ══ AJOUTER ══════════════════════════════════════
    with tab_add:
        st.markdown("### Nouvelle opération")
        with st.form("fa", clear_on_submit=True):
            desc = st.text_input("Description", placeholder="Ex : Courses Leclerc")
            mt   = st.number_input("Montant (€)", min_value=0.01, step=0.01, format="%.2f")
            cat  = st.selectbox("Catégorie", list(CATEGORIES.keys()))
            tp   = st.selectbox("Type", TYPES)
            dt   = st.date_input("Date", value=date.today())
            sub  = st.form_submit_button("Enregistrer ✓")

        if sub:
            if not desc.strip():
                st.warning("Veuillez saisir une description.")
            else:
                full_df, sha = get_budget()
                new_row = pd.DataFrame([{
                    "id":          secrets.token_hex(8),
                    "user_email":  email,
                    "date":        dt.strftime("%Y-%m-%d"),
                    "description": desc.strip(),
                    "categorie":   cat,
                    "type":        tp,
                    "montant":     mt,
                    "auteur":      email.split("@")[0],
                }])
                save_budget(pd.concat([full_df, new_row], ignore_index=True), sha)
                st.success("✅ Enregistré dans budget_data.csv !")
                st.rerun()

    # ══ HISTORIQUE ═══════════════════════════════════
    with tab_history:
        if df.empty:
            st.info("Aucune transaction enregistrée.")
        else:
            cats = ["Toutes"] + sorted(df["categorie"].dropna().unique().tolist())
            sel  = st.selectbox("Filtrer par catégorie", cats, label_visibility="collapsed")
            df_f = df if sel == "Toutes" else df[df["categorie"] == sel]

            for _, row in df_f.iterrows():
                is_rev  = row["type"] == "Revenu"
                bg, _   = CATEGORIES.get(row["categorie"], ("#F8F8F8","#888"))
                icon    = row["categorie"].split(" ")[0]
                amt_cls = "green" if is_rev else "red"
                sign    = "+" if is_rev else "−"
                tx_id   = str(row["id"])

                col_card, col_del = st.columns([6, 1])
                with col_card:
                    st.markdown(f"""
                    <div class="card" style="margin-bottom:.3rem">
                      <div class="tx" style="padding:.15rem 0">
                        <div class="tx-icon" style="background:{bg}">{icon}</div>
                        <div class="tx-desc">
                          <strong>{row['description']}</strong>
                          <span>{row['date'].strftime('%d/%m/%Y')} · {row['categorie']} · {row['type']}</span>
                        </div>
                        <span class="tx-amt {amt_cls}">{sign}{row['montant']:,.2f} €</span>
                      </div>
                    </div>""", unsafe_allow_html=True)
                with col_del:
                    if st.button("🗑", key=f"d_{tx_id}"):
                        full_df, sha = get_budget()
                        full_df = full_df[full_df["id"].astype(str) != tx_id]
                        save_budget(full_df, sha)
                        st.rerun()

    # ══ COMPTE ═══════════════════════════════════════
    with tab_account:
        st.markdown(f"""
        <div class="card" style="text-align:center;padding:1.75rem">
            <div style="font-size:42px;margin-bottom:.5rem">👤</div>
            <div style="font-weight:800;font-size:16px;color:#1A1A1A">{email}</div>
            <div style="font-size:12px;color:#aaa;margin-top:4px">Compte actif</div>
        </div>""", unsafe_allow_html=True)

        if not df.empty:
            st.markdown('<div class="sec-label">Statistiques globales</div>',
                        unsafe_allow_html=True)
            td = df[df["type"] != "Revenu"]["montant"].sum()
            tr = df[df["type"] == "Revenu"]["montant"].sum()
            nb = len(df)
            st.markdown(f"""
            <div class="metric-row">
              <div class="metric-box">
                <span class="metric-label">Dépenses totales</span>
                <span class="metric-val red">{td:,.0f} €</span>
              </div>
              <div class="metric-box">
                <span class="metric-label">Revenus totaux</span>
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
            _load.clear()
            st.rerun()


# ─────────────────────────────────────────────────────
# 10. ROUTAGE
# ─────────────────────────────────────────────────────
if st.session_state.logged_in:
    page_dashboard()
else:
    page_auth()
