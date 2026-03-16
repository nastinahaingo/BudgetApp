"""
H&L Budget — Application de suivi des dépenses du foyer
Mobile-first · Supabase Auth (email + récupération MDP) · Plotly

Dépendances :
    pip install streamlit supabase plotly pandas

Configuration :
    Créez un projet sur https://supabase.com (gratuit) puis copiez
    Project URL et anon key dans les secrets Streamlit :

    .streamlit/secrets.toml
    ───────────────────────
    SUPABASE_URL = "https://xxxx.supabase.co"
    SUPABASE_KEY = "eyJh..."

    Dans Supabase > Authentication > Email Templates, personnalisez
    les templates de confirmation et de réinitialisation de MDP.
    L'envoi d'email est géré nativement par Supabase (SMTP intégré).

    SQL à exécuter dans Supabase > SQL Editor pour créer la table :
    ──────────────────────────────────────────────────────────────────
    create table transactions (
      id          uuid primary key default gen_random_uuid(),
      user_id     uuid references auth.users(id) on delete cascade,
      created_at  timestamptz default now(),
      date        date not null,
      description text not null,
      categorie   text not null,
      type        text not null,
      montant     numeric not null,
      auteur      text not null
    );
    alter table transactions enable row level security;
    create policy "Users see own rows"
      on transactions for all
      using (auth.uid() = user_id)
      with check (auth.uid() = user_id);
    ──────────────────────────────────────────────────────────────────
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from supabase import create_client, Client


# ─────────────────────────────────────────────
# 1. CONFIG & STYLE MOBILE-FIRST
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="H&L Budget",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<style>
  /* ── Globals ── */
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #F5F4F0 !important;
  }
  .main .block-container { padding: 0 1rem 5rem; max-width: 480px; }

  /* ── Header ── */
  .hl-header {
    background: #1A1A1A;
    color: #fff;
    margin: -1rem -1rem 1.5rem;
    padding: 1.5rem 1.25rem 2.5rem;
    border-radius: 0 0 24px 24px;
  }
  .hl-header small { font-size: 11px; opacity: .55; text-transform: uppercase; letter-spacing: .08em; }
  .hl-header h2 { font-size: 22px; font-weight: 700; margin-top: 4px; }
  .hl-header p { font-size: 13px; opacity: .65; margin-top: 2px; }

  /* ── Cards ── */
  .card {
    background: #fff;
    border-radius: 18px;
    padding: 1rem 1.1rem;
    margin-bottom: .75rem;
    box-shadow: 0 2px 12px rgba(0,0,0,.07);
  }

  /* ── Metric row ── */
  .metric-row { display: flex; gap: 8px; margin-bottom: .75rem; }
  .metric-box {
    flex: 1; background: #fff; border-radius: 14px;
    padding: .75rem; text-align: center;
    box-shadow: 0 2px 12px rgba(0,0,0,.07);
  }
  .metric-label { font-size: 10px; text-transform: uppercase; letter-spacing: .06em; color: #999; display: block; }
  .metric-val { font-size: 18px; font-weight: 700; color: #1A1A1A; display: block; margin-top: 2px; }
  .metric-val.green { color: #3B6D11; }
  .metric-val.red   { color: #E24B4A; }

  /* ── Transaction items ── */
  .tx { display: flex; align-items: center; gap: 12px; padding: .65rem 0; border-bottom: 0.5px solid #F0F0F0; }
  .tx:last-child { border-bottom: none; }
  .tx-icon { width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
  .tx-desc { flex: 1; }
  .tx-desc strong { font-size: 13px; font-weight: 600; color: #1A1A1A; display: block; }
  .tx-desc span   { font-size: 11px; color: #aaa; }
  .tx-amt { font-size: 14px; font-weight: 700; }
  .tx-amt.red   { color: #E24B4A; }
  .tx-amt.green { color: #3B6D11; }

  /* ── Auth ── */
  .auth-wrap { max-width: 380px; margin: 2rem auto; }
  .auth-logo { text-align: center; margin-bottom: 2rem; }
  .auth-logo h1 { font-size: 32px; font-weight: 800; color: #1A1A1A; letter-spacing: -1px; }
  .auth-logo p  { font-size: 14px; color: #888; margin-top: 4px; }

  /* ── Buttons ── */
  .stButton > button {
    width: 100%; border-radius: 14px !important;
    background: #1A1A1A !important; color: #fff !important;
    border: none !important; padding: 14px !important;
    font-size: 15px !important; font-weight: 700 !important;
    transition: opacity .2s;
  }
  .stButton > button:hover { opacity: .85; }
  div[data-testid="stForm"] { background: transparent; border: none; }
  .stTextInput input, .stNumberInput input, .stSelectbox select, .stDateInput input {
    border-radius: 12px !important; border: 1.5px solid #E0E0E0 !important;
    font-size: 15px !important; padding: 12px 14px !important;
    background: #fff !important;
  }
  .stAlert { border-radius: 12px !important; }

  /* ── Section label ── */
  .sec-label {
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .08em; color: #999; margin: 1.25rem 0 .5rem;
  }

  /* ── Tab nav ── */
  div[data-baseweb="tab-list"] { background: transparent !important; gap: 4px; }
  div[data-baseweb="tab"] { border-radius: 20px !important; padding: 6px 18px !important; font-size: 13px !important; font-weight: 600 !important; }
  div[aria-selected="true"] { background: #1A1A1A !important; color: #fff !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 2. CLIENT SUPABASE
# ─────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()


# ─────────────────────────────────────────────
# 3. ÉTAT DE SESSION
# ─────────────────────────────────────────────
def _init_session():
    defaults = {
        "access_token": None,
        "refresh_token": None,
        "user_email": "",
        "user_id": None,
        "auth_mode": "login",   # login | register | forgot
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_session()

def is_logged_in() -> bool:
    return bool(st.session_state.access_token)


# ─────────────────────────────────────────────
# 4. DONNÉES
# ─────────────────────────────────────────────
CATEGORIES = {
    "🏠 Logement":      "#1A1A1A",
    "🛒 Alimentation":  "#E24B4A",
    "🚗 Transport":     "#378ADD",
    "🎬 Loisirs":       "#639922",
    "🏥 Santé":         "#BA7517",
    "📦 Autre":         "#888",
}
TYPES = ["Variable", "Fixe", "Revenu"]

def cat_icon(cat: str) -> str:
    return cat.split(" ")[0] if cat else "📦"

def cat_bg(cat: str) -> str:
    colors = {
        "Logement": "#F0F0F0", "Alimentation": "#FFF0F0",
        "Transport": "#F0F6FF", "Loisirs": "#F0FFF4",
        "Santé": "#FFFBF0", "Autre": "#F8F8F8",
    }
    for k, v in colors.items():
        if k in cat:
            return v
    return "#F8F8F8"


@st.cache_data(ttl=10)
def load_transactions(user_id: str) -> pd.DataFrame:
    resp = (
        supabase.table("transactions")
        .select("*")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .execute()
    )
    if not resp.data:
        return pd.DataFrame()
    df = pd.DataFrame(resp.data)
    df["date"] = pd.to_datetime(df["date"])
    df["montant"] = pd.to_numeric(df["montant"])
    return df


def invalidate_cache():
    load_transactions.clear()


def add_transaction(user_id: str, email: str, row: dict):
    supabase.table("transactions").insert({
        "user_id":     user_id,
        "date":        row["date"],
        "description": row["description"],
        "categorie":   row["categorie"],
        "type":        row["type"],
        "montant":     row["montant"],
        "auteur":      email,
    }).execute()
    invalidate_cache()


def delete_transaction(tx_id: str):
    supabase.table("transactions").delete().eq("id", tx_id).execute()
    invalidate_cache()


# ─────────────────────────────────────────────
# 5. PAGE AUTHENTIFICATION
# ─────────────────────────────────────────────
def page_auth():
    st.markdown("""
    <div class="auth-logo">
        <h1>H&L</h1>
        <p>Votre budget familial</p>
    </div>
    """, unsafe_allow_html=True)

    mode = st.session_state.auth_mode

    if mode == "login":
        with st.form("login_form"):
            email = st.text_input("Adresse email", placeholder="vous@exemple.fr")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button("Se connecter")

        if submitted:
            if not email or not password:
                st.error("Veuillez remplir tous les champs.")
            else:
                try:
                    res = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password,
                    })
                    st.session_state.access_token  = res.session.access_token
                    st.session_state.refresh_token = res.session.refresh_token
                    st.session_state.user_email    = res.user.email
                    st.session_state.user_id       = str(res.user.id)
                    st.rerun()
                except Exception as e:
                    st.error("Email ou mot de passe incorrect.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Mot de passe oublié ?", key="go_forgot"):
                st.session_state.auth_mode = "forgot"
                st.rerun()
        with col2:
            if st.button("Créer un compte", key="go_register"):
                st.session_state.auth_mode = "register"
                st.rerun()

    elif mode == "register":
        st.markdown("### Créer un compte")
        with st.form("register_form"):
            email = st.text_input("Adresse email", placeholder="vous@exemple.fr")
            pwd1  = st.text_input("Mot de passe", type="password")
            pwd2  = st.text_input("Confirmer le mot de passe", type="password")
            submitted = st.form_submit_button("Créer mon compte")

        if submitted:
            if not email or not pwd1:
                st.error("Veuillez remplir tous les champs.")
            elif len(pwd1) < 8:
                st.error("Le mot de passe doit contenir au moins 8 caractères.")
            elif pwd1 != pwd2:
                st.error("Les mots de passe ne correspondent pas.")
            else:
                try:
                    supabase.auth.sign_up({"email": email, "password": pwd1})
                    st.success("✅ Compte créé ! Vérifiez votre email pour confirmer votre inscription.")
                    st.session_state.auth_mode = "login"
                except Exception as e:
                    st.error(f"Erreur lors de la création du compte : {e}")

        if st.button("← Retour à la connexion", key="back_login_reg"):
            st.session_state.auth_mode = "login"
            st.rerun()

    elif mode == "forgot":
        st.markdown("### Récupérer mon mot de passe")
        st.info("Un lien de réinitialisation sera envoyé à votre adresse email.")
        with st.form("forgot_form"):
            email = st.text_input("Adresse email", placeholder="vous@exemple.fr")
            submitted = st.form_submit_button("Envoyer le lien")

        if submitted:
            if not email:
                st.error("Veuillez saisir votre adresse email.")
            else:
                try:
                    supabase.auth.reset_password_email(email)
                    st.success("✅ Email envoyé ! Vérifiez votre boîte de réception.")
                    st.session_state.auth_mode = "login"
                except Exception:
                    # Message neutre pour ne pas révéler si l'email existe
                    st.success("✅ Si cet email existe, un lien vous a été envoyé.")

        if st.button("← Retour à la connexion", key="back_login_forgot"):
            st.session_state.auth_mode = "login"
            st.rerun()


# ─────────────────────────────────────────────
# 6. PAGE PRINCIPALE
# ─────────────────────────────────────────────
def page_dashboard():
    user_id    = st.session_state.user_id
    user_email = st.session_state.user_email
    user_name  = user_email.split("@")[0].capitalize()

    # ── Header ──
    now = datetime.now()
    month_fr = ["Janvier","Février","Mars","Avril","Mai","Juin",
                 "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
    st.markdown(f"""
    <div class="hl-header">
        <small>{month_fr[now.month - 1]} {now.year}</small>
        <h2>Bonjour {user_name} 👋</h2>
        <p>Voici votre budget du mois</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Onglets ──
    tab_home, tab_add, tab_history, tab_account = st.tabs(
        ["📊 Tableau de bord", "➕ Ajouter", "📋 Historique", "👤 Compte"]
    )

    df = load_transactions(user_id)

    # ═══ TAB 1 : TABLEAU DE BORD ═══
    with tab_home:
        if df.empty:
            st.info("Aucune transaction enregistrée. Commencez par en ajouter une !")
        else:
            # Filtre mois courant
            df_month = df[
                (df["date"].dt.month == now.month) &
                (df["date"].dt.year  == now.year)
            ]

            revenus  = df_month[df_month["type"] == "Revenu"]["montant"].sum()
            depenses = df_month[df_month["type"] != "Revenu"]["montant"].sum()
            solde    = revenus - depenses

            # Métriques
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="metric-box">
                    <span class="metric-label">Revenus</span>
                    <span class="metric-val green">+{revenus:,.0f} €</span>
                </div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="metric-box">
                    <span class="metric-label">Dépenses</span>
                    <span class="metric-val red">−{depenses:,.0f} €</span>
                </div>""", unsafe_allow_html=True)
            with col3:
                color_cls = "green" if solde >= 0 else "red"
                sign      = "+" if solde >= 0 else "−"
                st.markdown(f"""
                <div class="metric-box">
                    <span class="metric-label">Solde</span>
                    <span class="metric-val {color_cls}">{sign}{abs(solde):,.0f} €</span>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Camembert ──
            df_dep = df_month[df_month["type"] != "Revenu"]
            if not df_dep.empty:
                st.markdown('<div class="sec-label">Répartition des dépenses</div>', unsafe_allow_html=True)
                cat_totals = (
                    df_dep.groupby("categorie")["montant"]
                    .sum()
                    .reset_index()
                    .sort_values("montant", ascending=False)
                )
                fig_pie = px.pie(
                    cat_totals,
                    values="montant",
                    names="categorie",
                    hole=0.45,
                    color_discrete_sequence=[
                        "#1A1A1A", "#E24B4A", "#378ADD", "#639922", "#BA7517", "#888"
                    ],
                )
                fig_pie.update_traces(textposition="inside", textinfo="percent+label")
                fig_pie.update_layout(
                    showlegend=False,
                    height=280,
                    margin=dict(t=10, b=10, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            # ── Évolution mensuelle ──
            st.markdown('<div class="sec-label">Évolution des dépenses</div>', unsafe_allow_html=True)
            df_trend = (
                df[df["type"] != "Revenu"]
                .set_index("date")
                .resample("ME")["montant"]
                .sum()
                .reset_index()
                .tail(6)
            )
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=df_trend["date"],
                y=df_trend["montant"],
                mode="lines+markers",
                line=dict(color="#1A1A1A", width=2.5),
                marker=dict(size=6, color="#1A1A1A"),
                fill="tozeroy",
                fillcolor="rgba(26,26,26,0.06)",
            ))
            fig_line.update_layout(
                height=200,
                margin=dict(t=10, b=10, l=10, r=10),
                xaxis=dict(showgrid=False, zeroline=False, tickformat="%b"),
                yaxis=dict(showgrid=True, gridcolor="#F0F0F0", zeroline=False),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_line, use_container_width=True)

            # ── Dernières opérations ──
            st.markdown('<div class="sec-label">Dernières opérations</div>', unsafe_allow_html=True)
            recent = df.head(5)
            html_txs = '<div class="card">'
            for _, row in recent.iterrows():
                is_rev  = row["type"] == "Revenu"
                amt_cls = "green" if is_rev else "red"
                sign    = "+" if is_rev else "−"
                icon    = cat_icon(row["categorie"])
                bg      = cat_bg(row["categorie"])
                html_txs += f"""
                <div class="tx">
                    <div class="tx-icon" style="background:{bg}">{icon}</div>
                    <div class="tx-desc">
                        <strong>{row['description']}</strong>
                        <span>{row['date'].strftime('%d/%m')} · {row['categorie']} · {row['auteur'].split('@')[0]}</span>
                    </div>
                    <span class="tx-amt {amt_cls}">{sign}{row['montant']:,.2f} €</span>
                </div>"""
            html_txs += "</div>"
            st.markdown(html_txs, unsafe_allow_html=True)

    # ═══ TAB 2 : AJOUTER ═══
    with tab_add:
        st.markdown("### Nouvelle opération")
        with st.form("form_add", clear_on_submit=True):
            description = st.text_input("Description", placeholder="Ex : Courses Leclerc")
            montant     = st.number_input("Montant (€)", min_value=0.01, step=0.01, format="%.2f")
            categorie   = st.selectbox("Catégorie", list(CATEGORIES.keys()))
            type_op     = st.selectbox("Type", TYPES)
            date_op     = st.date_input("Date", value=date.today())
            submitted   = st.form_submit_button("Enregistrer ✓")

        if submitted:
            if not description.strip():
                st.warning("Veuillez saisir une description.")
            else:
                add_transaction(user_id, user_email, {
                    "date":        date_op.strftime("%Y-%m-%d"),
                    "description": description.strip(),
                    "categorie":   categorie,
                    "type":        type_op,
                    "montant":     montant,
                })
                st.success("✅ Opération enregistrée !")
                st.rerun()

    # ═══ TAB 3 : HISTORIQUE ═══
    with tab_history:
        if df.empty:
            st.info("Aucune transaction enregistrée.")
        else:
            # Filtre par catégorie
            cats = ["Toutes"] + sorted(df["categorie"].unique().tolist())
            selected_cat = st.selectbox("Filtrer par catégorie", cats, label_visibility="collapsed")

            df_filtered = df if selected_cat == "Toutes" else df[df["categorie"] == selected_cat]

            for _, row in df_filtered.iterrows():
                is_rev  = row["type"] == "Revenu"
                amt_cls = "green" if is_rev else "red"
                sign    = "+" if is_rev else "−"
                icon    = cat_icon(row["categorie"])
                bg      = cat_bg(row["categorie"])
                tx_id   = str(row["id"])

                col_tx, col_del = st.columns([5, 1])
                with col_tx:
                    st.markdown(f"""
                    <div class="card" style="margin-bottom:.4rem">
                        <div class="tx" style="padding:.2rem 0">
                            <div class="tx-icon" style="background:{bg}">{icon}</div>
                            <div class="tx-desc">
                                <strong>{row['description']}</strong>
                                <span>{row['date'].strftime('%d/%m/%Y')} · {row['categorie']}</span>
                                <span style="color:#bbb">par {row['auteur'].split('@')[0]}</span>
                            </div>
                            <span class="tx-amt {amt_cls}">{sign}{row['montant']:,.2f} €</span>
                        </div>
                    </div>""", unsafe_allow_html=True)
                with col_del:
                    if st.button("🗑", key=f"del_{tx_id}", help="Supprimer"):
                        delete_transaction(tx_id)
                        st.rerun()

    # ═══ TAB 4 : COMPTE ═══
    with tab_account:
        st.markdown(f"""
        <div class="card">
            <div style="font-size:32px;text-align:center;margin-bottom:.75rem">👤</div>
            <div style="text-align:center;font-weight:700;font-size:16px;color:#1A1A1A">{user_email}</div>
            <div style="text-align:center;font-size:12px;color:#aaa;margin-top:4px">Compte actif</div>
        </div>
        """, unsafe_allow_html=True)

        if not df.empty:
            st.markdown('<div class="sec-label">Statistiques globales</div>', unsafe_allow_html=True)
            total_dep = df[df["type"] != "Revenu"]["montant"].sum()
            total_rev = df[df["type"] == "Revenu"]["montant"].sum()
            nb_tx     = len(df)
            st.markdown(f"""
            <div class="metric-row">
                <div class="metric-box"><span class="metric-label">Toutes dépenses</span><span class="metric-val red">{total_dep:,.0f} €</span></div>
                <div class="metric-box"><span class="metric-label">Tous revenus</span><span class="metric-val green">{total_rev:,.0f} €</span></div>
                <div class="metric-box"><span class="metric-label">Opérations</span><span class="metric-val">{nb_tx}</span></div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Se déconnecter", key="logout"):
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
            for key in ["access_token", "refresh_token", "user_email", "user_id"]:
                st.session_state[key] = None if key != "user_email" else ""
            invalidate_cache()
            st.rerun()


# ─────────────────────────────────────────────
# 7. ROUTAGE
# ─────────────────────────────────────────────
if is_logged_in():
    page_dashboard()
else:
    page_auth()
