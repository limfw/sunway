import streamlit as st
import pandas as pd
import requests

# --- GitHub Config ---
GITHUB_USERNAME = "limfw"
GITHUB_REPO = "sunway"
GITHUB_TOKEN = st.secrets['github']['token']
GITHUB_FOLDER = "results"
PARTICIPANT_FILE = "participant.csv"
MANUAL_SCORE_FILE = "manual_scores.csv"

# --- Load RPS JSON Results ---
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

# --- Build Leaderboard ---
def build_team_leaderboard():
    rps_df = load_rps_results()
    part_df = load_participant_info()
    score_df = load_manual_scores()

    # Normalize keys
    rps_df["team_code"] = rps_df["team_code"].astype(str).str.strip().str.upper()
    part_df["team_code"] = part_df["team_code"].astype(str).str.strip().str.upper()
    part_df["Class"] = part_df["Class"].astype(str).str.strip().str.upper()
    score_df["Class"] = score_df["Class"].astype(str).str.strip().str.upper()

    if rps_df.empty:
        rps_df = pd.DataFrame(columns=['team_code', 'win', 'timestamp'])

    rps_df = pd.merge(rps_df, part_df, on="team_code", how="left")
    team_rps = rps_df.groupby("Class")["win"].sum().reset_index(name="game1")
    all_classes = part_df[['Class']].drop_duplicates()
    team_rps = pd.merge(all_classes, team_rps, on="Class", how="left").fillna({"game1": 0})
    merged = pd.merge(score_df, team_rps, on="Class", how="left").fillna(0)
    score_cols = ['game1', 'game2', 'game3', 'game4', 'game5', 'game6']
    merged['total'] = merged[score_cols].sum(axis=1)
    merged = merged.sort_values("total", ascending=False).reset_index(drop=True)
    merged["Rank"] = merged.index + 1
    return merged

# --- Streamlit UI ---
st.set_page_config("🏆 Final Leaderboard", layout="wide")
st.markdown("""
    <style>
    .title {
        text-align: center;
        font-size: 50px;
        font-weight: bold;
        color: #333;
        margin-bottom: 10px;
    }
    .subtitle {
        text-align: center;
        font-size: 24px;
        color: #666;
        margin-top: -15px;
    }
    .highlight {
        background-color: #f8f9fa;
        border-left: 6px solid #2196F3;
        padding: 10px;
        margin-bottom: 20px;
    }
    </style>
    <div class="title">🏆 Final Class Leaderboard</div>
    <div class="subtitle">Combined Scores from All 6 Games</div>
""", unsafe_allow_html=True)

df = build_team_leaderboard()

if df.empty:
    st.warning("No results available yet. Please wait for teams to complete their games.")
else:
    top3 = df.head(3)
    medals = ["🥇", "🥈", "🥉"]
    colors = ["#FFD700", "#C0C0C0", "#CD7F32"]
    st.markdown("### 🏅 Top 3 Classes")
    cols = st.columns(3)
    for i in range(min(3, len(top3))):
        with cols[i]:
            st.markdown(f"""
            <div style="text-align: center; background-color:{colors[i]}; padding: 20px; border-radius: 15px;">
                <h2 style='margin-bottom:10px'>{medals[i]} {top3.iloc[i]['Class']}</h2>
                <p style='font-size:18px;'>Total Score: <strong>{int(top3.iloc[i]['total'])}</strong></p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### 📊 Full Leaderboard")
    st.dataframe(
        df[['Rank', 'Class', 'game1', 'game2', 'game3', 'game4', 'game5', 'game6', 'total']],
        use_container_width=True,
        hide_index=True
    )
