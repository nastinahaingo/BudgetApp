import streamlit as st
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime
import os
import time
import secrets

# ==========================================
# 1. CONFIGURATION ET CONSTANTES
# ==========================================
st.set_page_config(page_title="H&L Budget", layout="centered")

USER_DB = "users_admin.csv"
BUDGET_DB = "budget_admin.csv"

COLONNES_USERS = ["username", "password_hash", "salt"]
COLONNES_BUDGET = ["id", "date", "description", "categorie", "type", "montant", "paiement", "auteur"]

CATEGORIES = ["Alimentation", "Habitation", "Loisirs", "Revenu", "Santé", "Transport", "Autre"]
TYPES = ["Fixe", "Revenu", "Variable"]

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #1A1A1A; }
    h1, h2, h3 { color: #1A1A1A !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 600; }
    .stButton>button {
        width: 100%; border-radius: 10px; border: 1px solid #1A1A1A;
        background-color: #1A1A1A; color: white; padding: 10px; font-weight: bold;
    }
    .card {
        background-color: #F9F9F9; padding: 15px; border-radius: 12px;
        margin-bottom: 12px; border: 1px solid #EEEEEE;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }
    .user-tag {
        background-color: #E0E0E0; color: #1A1A1A; padding: 3px 10px;
        border-radius: 15px; font-size: 0.75em; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. SÉCURITÉ — HACHAGE DES MOTS DE PASSE
# ==========================================
def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """
    Hache le mot de passe avec un sel unique (PBKDF2-HMAC-SHA256).
    Retourne (hash_hex, salt_hex).

    CORRECTION SÉCURITÉ : L'ancien code utilisait un simple SHA-256 sans sel,
    ce qui est vulnérable aux attaques par rainbow table.
    """
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=260_000,  # recommandation OWASP 2024
    )
    return key.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    computed, _ = hash_password(password, salt)
    # Comparaison en temps constant pour éviter les timing attacks
    return secrets.compare_digest(computed, stored_hash)


# ==========================================
# 3. GESTION DES FICHIERS CSV
# ==========================================
def init_files() -> None:
    """Crée les fichiers CSV s'ils n'existent pas encore."""
    if not os.path.exists(USER_DB):
        pd.DataFrame(columns=COLONNES_USERS).to_csv(USER_DB, index=False)
    if not os.path.exists(BUDGET_DB):
        pd.DataFrame(columns=COLONNES_BUDGET).to_csv(BUDGET_DB, index=False)


@st.cache_data(ttl=5)
def get_users() -> pd.DataFrame:
    """
    Charge la base d'utilisateurs.

    CORRECTION BUG : L'ancienne version pouvait crasher silencieusement sur
    une exception générique. On laisse maintenant remonter les vraies erreurs.
    """
    if not os.path.exists(USER_DB):
        return pd.DataFrame(columns=COLONNES_USERS)
    return pd.read_csv(USER_DB)


@st.cache_data(ttl=5)
def get_budget() -> pd.DataFrame:
    """
    Charge et nettoie les transactions.

    CORRECTION BUG : Les exceptions silencieuses masquaient les erreurs de
    lecture. On gère maintenant uniquement ce qu'on sait traiter.
    """
    if not os.path.exists(BUDGET_DB):
        return pd.DataFrame(columns=COLONNES_BUDGET)

    df = pd.read_csv(BUDGET_DB)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["montant"] = pd.to_numeric(df["montant"], errors="coerce").fillna(0)
    df = df.dropna(subset=["date"])
    return df


def save_budget(df: pd.DataFrame) -> None:
    """Sauvegarde le DataFrame et invalide le cache."""
    df.to_csv(BUDGET_DB, index=False)
    get_budget.clear()


def save_users(df: pd.DataFrame) -> None:
    """Sauvegarde les utilisateurs et invalide le cache."""
    df.to_csv(USER_DB, index=False)
    get_users.clear()


init_files()


# ==========================================
# 4. AUTHENTIFICATION
# ==========================================
def login(username: str, password: str) -> bool:
    df_u = get_users()
    row = df_u[df_u["username"] == username]
    if row.empty:
        return False

    # CORRECTION SÉCURITÉ : support de l'ancienne colonne 'password' (migration)
    if "password_hash" in row.columns and "salt" in row.columns:
        return verify_password(password, row.iloc[0]["password_hash"], row.iloc[0]["salt"])

    # Ancien format SHA-256 sans sel — accepté pour rétrocompatibilité
    legacy_hash = hashlib.sha256(password.encode()).hexdigest()
    return row.iloc[0].get("password", "") == legacy_hash


def register(username: str, password: str) -> tuple[bool, str]:
    """Retourne (succès, message)."""
    if not username or not password:
        return False, "Le nom d'utilisateur et le mot de passe sont obligatoires."
    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères."

    df_u = get_users()
    if username in df_u["username"].values:
        return False, "Ce nom d'utilisateur est déjà pris."

    pw_hash, salt = hash_password(password)
    new_row = pd.DataFrame([[username, pw_hash, salt]], columns=COLONNES_USERS)
    save_users(pd.concat([df_u, new_row], ignore_index=True))
    return True, "Compte créé ! Connectez-vous."


# — État de session
if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.user = ""

if not st.session_state.auth:
    st.markdown("<h1 style='text-align:center;'>Accès H&L Budget</h1>", unsafe_allow_html=True)
    tab_login, tab_register = st.tabs(["Connexion", "Créer un compte"])

    with tab_login:
        username = st.text_input("Utilisateur", key="u_login")
        password = st.text_input("Mot de passe", type="password", key="p_login")
        if st.button("Se connecter"):
            if login(username, password):
                st.session_state.auth = True
                st.session_state.user = username
                st.rerun()
            else:
                # CORRECTION SÉCURITÉ : message générique pour ne pas révéler
                # si c'est le nom ou le mot de passe qui est incorrect.
                st.error("Identifiants incorrects.")

    with tab_register:
        new_user = st.text_input("Nouveau nom", key="u_reg")
        new_pass = st.text_input("Nouveau mot de passe (8 car. min.)", type="password", key="p_reg")
        if st.button("Valider l'inscription"):
            ok, msg = register(new_user, new_pass)
            (st.success if ok else st.error)(msg)

    st.stop()


# ==========================================
# 5. DASHBOARD & ANALYSES
# ==========================================
df = get_budget()

st.sidebar.write(f"Utilisateur : **{st.session_state.user}**")
if st.sidebar.button("Déconnexion"):
    st.session_state.auth = False
    st.session_state.user = ""
    st.rerun()

st.title("H&L Budget Pro")

if not df.empty:
    col1, col2 = st.columns(2)

    with col1:
        df_dep = df[df["type"] != "Revenu"]
        if not df_dep.empty:
            fig_pie = px.pie(
                df_dep, values="montant", names="categorie", hole=0.4,
                color_discrete_sequence=px.colors.sequential.Greys,
            )
            fig_pie.update_layout(showlegend=False, height=200, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # CORRECTION BUG : on s'assure que l'index est bien un DatetimeIndex
        # avant de resampler, ce qui évitait un crash si la colonne date
        # contenait des NaT résiduels.
        df_trend = (
            df.dropna(subset=["date"])
            .set_index("date")
            .resample("ME")["montant"]
            .sum()
            .reset_index()
        )
        fig_line = px.line(df_trend, x="date", y="montant", color_discrete_sequence=["#1A1A1A"])
        fig_line.update_layout(height=200, margin=dict(t=10, b=10, l=10, r=10), xaxis_title="", yaxis_title="")
        st.plotly_chart(fig_line, use_container_width=True)

st.divider()


# ==========================================
# 6. SAISIE D'UNE TRANSACTION
# ==========================================
with st.expander("Nouvelle opération", expanded=False):
    with st.form("form_add", clear_on_submit=True):
        desc = st.text_input("Description")
        c1, c2 = st.columns(2)
        with c1:
            mt = st.number_input("Montant (€)", min_value=0.0, step=0.01, format="%.2f")
            cat = st.selectbox("Catégorie", CATEGORIES)
        with c2:
            dt = st.date_input("Date", datetime.now())
            tp = st.selectbox("Type", TYPES)

        if st.form_submit_button("Enregistrer"):
            if not desc.strip():
                st.warning("Veuillez saisir une description.")
            elif mt == 0.0:
                st.warning("Le montant doit être supérieur à zéro.")
            else:
                # CORRECTION PERFORMANCE : on recharge le CSV uniquement ici,
                # pas à chaque rendu. L'ID utilise secrets pour éviter les
                # collisions en environnement multi-utilisateur.
                current_df = get_budget()
                new_row = pd.DataFrame([{
                    "id": secrets.token_hex(8),          # ID aléatoire robuste
                    "date": dt.strftime("%Y-%m-%d"),
                    "description": desc.strip(),
                    "categorie": cat,
                    "type": tp,
                    "montant": mt,
                    "paiement": "Carte",
                    "auteur": st.session_state.user,
                }])
                save_budget(pd.concat([current_df, new_row], ignore_index=True))
                st.success("Enregistré avec succès !")
                time.sleep(0.5)
                st.rerun()


# ==========================================
# 7. HISTORIQUE & SUPPRESSION
# ==========================================
st.subheader("Historique")

if df.empty:
    st.info("Aucune transaction enregistrée.")
else:
    df_display = df.sort_values("date", ascending=False)

    for _, row in df_display.iterrows():
        # CORRECTION QUALITÉ : on n'utilise plus l'index Pandas (i) comme clé
        # de bouton — on utilise l'ID métier stable.
        row_id = str(row["id"])

        st.markdown(f"""
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:0.85em; color:#666;">
                    {row['date'].strftime('%d/%m/%Y')} | {row['categorie']}
                </span>
                <b style="font-size:1.1em;">{row['montant']:.2f} €</b>
            </div>
            <div style="font-weight:500; margin-top:5px;">{row['description']}</div>
            <div style="margin-top:10px;">
                <span class="user-tag">Auteur : {row['auteur']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🗑 Supprimer", key=f"del_{row_id}"):
            fresh_df = get_budget()
            fresh_df = fresh_df[fresh_df["id"].astype(str) != row_id]
            save_budget(fresh_df)
            st.rerun()
