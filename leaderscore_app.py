import streamlit as st
import pandas as pd
import requests

# --- GitHub Configuration ---
GITHUB_USERNAME = "limfw"
GITHUB_REPO = "sunway"
SCORE_FILE = "manual_scores.csv"
PARTICIPANT_FILE = "participant.csv"

# --- Data URLs ---
SCORE_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/{SCORE_FILE}"
PARTICIPANT_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/{PARTICIPANT_FILE}"

# --- Load Data ---
@st.cache_data(ttl=60)
def load_data():
    score_df = pd.read_csv(SCORE_URL)
    part_df = pd.read_csv(PARTICIPANT_URL)
    score_df["Class"] = score_df["Class"].astype(str).str.strip().str.upper()
    part_df["Class"] = part_df["Class"].astype(str).str.strip().str.upper()
    return score_df, part_df

def build_team_leaderboard():
    score_df, part_df = load_data()

    # Ensure every class has a score row
    all_classes = sorted(part_df["Class"].unique())
    for cls in all_classes:
        if cls not in score_df["Class"].values:
            new_row = {"Class": cls}
            for g in range(2, 7):
                new_row[f"game{g}"] = 0
            score_df = pd.concat([score_df, pd.DataFrame([new_row])], ignore_index=True)

    score_df = score_df.drop_duplicates("Class").reset_index(drop=True)

    # Compute total score
    game_cols = [f"game{i}" for i in range(1, 7) if f"game{i}" in score_df.columns]
    score_df["Total Score"] = score_df[game_cols].sum(axis=1)

    # Sort and rank
    leaderboard = score_df[["Class", "Total Score"]].copy()
    leaderboard = leaderboard.sort_values(by="Total Score", ascending=False).reset_index(drop=True)

    return leaderboard

# --- Streamlit UI ---
st.set_page_config(page_title="Leaderboard", layout="centered")
st.title("🏆 Class Leaderboard")
st.caption("Real-time scoreboard combining all games.")

df = build_team_leaderboard()

# --- Display Top 3 Highlight ---
top3 = df.head(3)
rest = df.iloc[3:]

st.markdown("### 🥇 Top 3 Teams")
for i, row in top3.iterrows():
    if i == 0:
        st.success(f"1st: **{row['Class']}** – {row['Total Score']} points")
    elif i == 1:
        st.info(f"2nd: **{row['Class']}** – {row['Total Score']} points")
    elif i == 2:
        st.warning(f"3rd: **{row['Class']}** – {row['Total Score']} points")

# --- Show Rest of Leaderboard ---
st.markdown("### 📊 Full Leaderboard")
st.dataframe(rest.reset_index(drop=True), use_container_width=True)
