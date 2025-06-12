import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- GitHub Config ---
GITHUB_USERNAME = "limfw"
GITHUB_REPO = "sunway"
GITHUB_TOKEN = st.secrets['github']['token']
GITHUB_FOLDER = "results"
PARTICIPANT_FILE = "participant.csv"
MANUAL_SCORE_FILE = "manual_scores.csv"

# --- Load RPS Results (Game 1) ---
@st.cache_data(ttl=60)
def load_rps_results():
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{GITHUB_FOLDER}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    resp = requests.get(url, headers=headers)

    results = []
    if resp.status_code == 200:
        for file in resp.json():
            if file["name"].endswith(".json"):
                json_url = file["download_url"]
                data = requests.get(json_url).json()
                results.append(data)
    return pd.DataFrame(results)

# --- Load participant.csv ---
@st.cache_data(ttl=60)
def load_participant_info():
    url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/{PARTICIPANT_FILE}"
    return pd.read_csv(url)

# --- Load manual_scores.csv ---
@st.cache_data(ttl=60)
def load_manual_scores():
    url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/{MANUAL_SCORE_FILE}"
    return pd.read_csv(url)

# --- Build Team-Level Leaderboard (Grouped by Class) ---
def build_team_leaderboard():
    rps_df = load_rps_results()
    part_df = load_participant_info()
    score_df = load_manual_scores()

    # Normalize keys
    rps_df["team_code"] = rps_df["team_code"].astype(str).str.strip().str.upper()
    part_df["team_code"] = part_df["team_code"].astype(str).str.strip().str.upper()
    part_df["Class"] = part_df["Class"].astype(str).str.strip().str.upper()
    score_df["Class"] = score_df["Class"].astype(str).str.strip().str.upper()
    score_df = score_df.rename(columns={"Class": "Class"})

    if rps_df.empty:
        rps_df = pd.DataFrame(columns=['team_code', 'win', 'timestamp'])

    # Merge RPS results with participant info
    rps_df = pd.merge(rps_df, part_df, on="team_code", how="left")

    # Sum RPS wins by Class
    team_rps = rps_df.groupby("Class")['win'].sum().reset_index(name="game1")

    # Include all teams even if no RPS played yet
    all_teams = part_df[['Class']].drop_duplicates()
    team_rps = pd.merge(all_teams, team_rps, on="Class", how="left").fillna({"game1": 0})

    # Merge with manual scores
    merged = pd.merge(score_df, team_rps, on="Class", how="left").fillna(0)

    # Calculate total score
    score_cols = ['game1', 'game2', 'game3', 'game4', 'game5', 'game6']
    merged['total'] = merged[score_cols].sum(axis=1)

    return merged.sort_values("total", ascending=False)

# --- Streamlit UI ---
st.set_page_config("🏆 Class Leaderboard", layout="centered")
st.title("🎯 Class Leaderboard: Combined Scores from All 6 Games")

df = build_team_leaderboard()

if df.empty:
    st.warning("No results available yet.")
else:
    st.dataframe(
        df[['Class', 'game1', 'game2', 'game3', 'game4', 'game5', 'game6', 'total']],
        use_container_width=True
    )

    csv = df.to_csv(index=False)
    st.download_button("📥 Download Leaderboard as CSV", data=csv, file_name="leaderboard.csv", mime="text/csv")
