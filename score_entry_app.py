import streamlit as st
import pandas as pd
import requests
import base64

# --- GitHub Config ---
GITHUB_USERNAME = "limfw"
GITHUB_REPO = "sunway"
GITHUB_TOKEN = st.secrets["github"]["token"]
SCORE_FILE = "manual_scores.csv"
PARTICIPANT_FILE = "participant.csv"
RAW_SCORE_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/{SCORE_FILE}"
RAW_PARTICIPANT_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/{PARTICIPANT_FILE}"

# --- Load CSVs ---
@st.cache_data(ttl=60)
def load_data():
    score_df = pd.read_csv(RAW_SCORE_URL)
    score_df["Class"] = score_df["Class"].astype(str).str.strip().str.upper()

    part_df = pd.read_csv(RAW_PARTICIPANT_URL)
    part_df["Class"] = part_df["Class"].astype(str).str.strip().str.upper()
    return score_df, part_df

# --- Build Leaderboard ---
def build_team_leaderboard():
    score_df, part_df = load_data()

    # Ensure score_df has all game columns
    for g in range(2, 7):
        col = f"game{g}"
        if col not in score_df.columns:
            score_df[col] = 0

    score_df = score_df.groupby("Class")[
        [f"game{i}" for i in range(2, 7)]
    ].sum().reset_index()

    score_df["Total"] = score_df[[f"game{i}" for i in range(2, 7)]].sum(axis=1)
    return score_df.sort_values("Total", ascending=False).reset_index(drop=True)

# --- Streamlit App UI ---
st.set_page_config(page_title="Class Leaderboard", layout="wide")
st.title("🎯 Class Leaderboard: Combined Scores from All 6 Games")

# --- Main Leaderboard Display ---
df = build_team_leaderboard()

if df.empty:
    st.warning("No scores found yet.")
else:
    top3 = df.head(3).copy()
    rest = df.iloc[3:].copy()

    medal_icons = ["🥇", "🥈", "🥉"]
    top3["Rank"] = [f"{medal} {cls}" for medal, cls in zip(medal_icons, top3["Class"])]
    top3_display = top3[["Rank", "Total"] + [f"game{i}" for i in range(2, 7)]]
    top3_display.index = [1, 2, 3]

    st.subheader("🏆 Top 3 Teams")
    st.dataframe(top3_display, use_container_width=True)

    if not rest.empty:
        st.subheader("📋 Other Teams")
        rest = rest.reset_index(drop=True)
        rest.index = rest.index + 4
        rest_display = rest[["Class", "Total"] + [f"game{i}" for i in range(2, 7)]]
        st.dataframe(rest_display, use_container_width=True)
