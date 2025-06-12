import streamlit as st
import pandas as pd
import requests
from io import StringIO

# --- GitHub Config ---
GITHUB_USERNAME = "limfw"
GITHUB_REPO = "sunway"
SCORE_FILE = "manual_scores.csv"
PARTICIPANT_FILE = "participant.csv"

SCORE_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/{SCORE_FILE}"
PARTICIPANT_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/{PARTICIPANT_FILE}"

# --- Load Data (always fresh) ---
@st.cache_data(ttl=0)
def load_data():
    score_df = pd.read_csv(SCORE_URL)
    part_df = pd.read_csv(PARTICIPANT_URL)
    score_df["Class"] = score_df["Class"].astype(str).str.strip().str.upper()
    part_df["Class"] = part_df["Class"].astype(str).str.strip().str.upper()
    return score_df, part_df

# --- Compute Leaderboard ---
def build_leaderboard():
    score_df, part_df = load_data()
    team_scores = (
        score_df
        .groupby("Class")
        [[f"game{i}" for i in range(2, 7)]]
        .sum()
        .reset_index()
    )
    team_scores["Total"] = team_scores[[f"game{i}" for i in range(2, 7)]].sum(axis=1)
    team_scores = team_scores.sort_values("Total", ascending=False).reset_index(drop=True)
    return team_scores

# --- Display Leaderboard ---
st.set_page_config(page_title="🏆 Team Leaderboard", layout="wide")
st.title("🏆 Class Team Leaderboard")
st.caption("Leaderboard based on Game 2 to Game 6")

leaderboard = build_leaderboard()

# --- Display Top 3 ---
st.subheader("🥇 Top 3 Teams")
cols = st.columns(3)
top3 = leaderboard.head(3)
medals = ["🥇", "🥈", "🥉"]
for i in range(len(top3)):
    with cols[i]:
        st.metric(f"{medals[i]} {top3.iloc[i]['Class']}", f"{top3.iloc[i]['Total']} pts")

# --- Display Full Table ---
st.subheader("📋 Full Leaderboard")
st.dataframe(leaderboard, use_container_width=True)

st.caption("Note: Scores update live from GitHub whenever changed via score entry portal.")
