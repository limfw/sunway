import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- GitHub Config ---
GITHUB_USERNAME = "limfw"
GITHUB_REPO = "sunway"
GITHUB_TOKEN = st.secrets['github']['token']
GITHUB_FOLDER = "results"
PARTICIPANT_FILE = "participant.csv"
MANUAL_SCORE_FILE = "manual_scores.csv"

# Game name mappings (consistent with the first app)
GAME_NAMES = {
    "game1": "Rock-paper-scissor",
    "game2": "Dodge ball",
    "game3": "Captain ball",
    "game4": "Graph-theoretical",
    "game5": "Topological",
    "game6": "Logic and Recreation game"
}

# --- Load RPS Results (Game 1) ---
@st.cache_data(ttl=30)
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
@st.cache_data(ttl=30)
def load_manual_scores():
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{MANUAL_SCORE_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        content = response.json()["content"]
        decoded = base64.b64decode(content)
        return pd.read_csv(io.StringIO(decoded.decode()))
    else:
        st.error("❌ Failed to load manual_scores.csv from GitHub")
        return pd.DataFrame()

# --- Build Team-Level Leaderboard ---
def build_team_leaderboard():
    rps_df = load_rps_results()
    part_df = load_participant_info()
    score_df = load_manual_scores()

    rps_df["team_code"] = rps_df["team_code"].astype(str).str.strip().str.upper()
    part_df["team_code"] = part_df["team_code"].astype(str).str.strip().str.upper()
    part_df["Class"] = part_df["Class"].astype(str).str.strip().str.upper()
    score_df["Class"] = score_df["Class"].astype(str).str.strip().str.upper()

    if rps_df.empty:
        rps_df = pd.DataFrame(columns=['team_code', 'win', 'timestamp'])

    rps_df = pd.merge(rps_df, part_df, on="team_code", how="left")
    team_rps = rps_df.groupby("Class")['win'].sum().reset_index(name="game1")
    all_teams = part_df[['Class']].drop_duplicates()
    team_rps = pd.merge(all_teams, team_rps, on="Class", how="left").fillna({"game1": 0})
    
    # Merge scores with game1 (Rock-paper-scissor) coming from RPS results
    merged = pd.merge(score_df, team_rps, on="Class", how="left").fillna(0)
    
    # Reorder columns to put game1 last
    score_cols = ['game2', 'game3', 'game4', 'game5', 'game6', 'game1']
    merged['total'] = merged[score_cols + ['game1']].sum(axis=1)  # Include all games in total calculation
    
    return merged.sort_values("total", ascending=False).reset_index(drop=True)

# --- Streamlit UI ---
st.set_page_config("🏆 MATRIX Leaderboard", layout="centered")
st.title("🏆 Top Teams Across All 6 Games")

# --- Manual Refresh Button ---
if st.button("🔁 Refresh Leaderboard Now"):
    st.cache_data.clear()
    st.experimental_rerun()

df = build_team_leaderboard()

if df.empty:
    st.warning("No results available yet.")
else:
    st.markdown("## 🏅 Top 3 Teams")

    def format_class(c): return str(c).upper().strip()

    top3 = df.head(3).copy()
    top3["Class"] = top3["Class"].apply(format_class)

    st.markdown(
        f"""
        <div style='display: flex; justify-content: center; align-items: flex-end; gap: 40px; margin-top: 30px;'>
            <div style='flex:1; background:#E0E0E0; padding:15px; border-radius:20px; text-align:center; box-shadow:2px 2px 8px rgba(0,0,0,0.2);'>
                <div style='font-size: 40px;'>🥈</div>
                <div style='font-size: 20px; font-weight:bold;'>{top3.iloc[1]["Class"]}</div>
                <div style='font-size: 18px;'>{int(top3.iloc[1]["total"])} pts</div>
            </div>
            <div style='flex:1.2; background:#FFD700; padding:20px; border-radius:20px; text-align:center; transform: scale(1.1); box-shadow:2px 2px 10px rgba(0,0,0,0.4);'>
                <div style='font-size: 60px;'>🏆</div>
                <div style='font-size: 24px; font-weight:bold;'>Champion</div>
                <div style='font-size: 22px; font-weight:bold; margin-top:5px;'>{top3.iloc[0]["Class"]}</div>
                <div style='font-size: 20px;'>{int(top3.iloc[0]["total"])} pts</div>
            </div>
            <div style='flex:1; background:#CD7F32; padding:15px; border-radius:20px; text-align:center; box-shadow:2px 2px 8px rgba(0,0,0,0.2);'>
                <div style='font-size: 38px;'>🥉</div>
                <div style='font-size: 20px; font-weight:bold;'>{top3.iloc[2]["Class"]}</div>
                <div style='font-size: 18px;'>{int(top3.iloc[2]["total"])} pts</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ... (keep all previous imports and setup code the same until the display section) ...

    st.markdown("## 📋 Full Results")
    
    # Display with full column names
    display_df = df.copy()
    display_df = display_df.rename(columns=GAME_NAMES)
    display_df = display_df.rename(columns={'total': 'Total Score'})
    
    # Reorder columns to put Rock-paper-scissor last
    column_order = ['Class', 'Dodge ball', 'Captain ball', 'Graph-theoretical', 
                   'Topological', 'Logic and Recreation game', 'Rock-paper-scissor', 'Total Score']
    display_df = display_df[column_order]

    # Custom CSS for better table display
    st.markdown("""
    <style>
        /* Main table styling */
        div[data-testid="stDataFrame"] {
            width: 100% !important;
        }
        
        /* Header styling */
        .stDataFrame thead tr th {
            background-color: #f8f9fa;
            font-weight: bold;
            text-align: center !important;
            position: sticky;
            top: 0;
        }
        
        /* Cell styling */
        .stDataFrame td {
            text-align: center !important;
            padding: 8px 12px !important;
        }
        
        /* Zebra striping */
        .stDataFrame tbody tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        /* Hover effect */
        .stDataFrame tbody tr:hover {
            background-color: #e9ecef;
        }
        
        /* Remove index column */
        .stDataFrame thead tr th:first-child,
        .stDataFrame tbody tr th {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Display the dataframe with optimized settings
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=min(800, (len(display_df) * 35 + 35)),  # Limits height to 800px max
        column_config={
            "Class": st.column_config.TextColumn("Class", width="medium"),
            "Dodge ball": st.column_config.NumberColumn("Dodge ball", width="small"),
            "Captain ball": st.column_config.NumberColumn("Captain ball", width="small"),
            "Graph-theoretical": st.column_config.NumberColumn("Graph-theoretical", width="small"),
            "Topological": st.column_config.NumberColumn("Topological", width="small"),
            "Logic and Recreation game": st.column_config.NumberColumn("Logic and Recreation game", width="medium"),
            "Rock-paper-scissor": st.column_config.NumberColumn("Rock-paper-scissor", width="medium"),
            "Total Score": st.column_config.NumberColumn("Total Score", width="small")
        }
    )
