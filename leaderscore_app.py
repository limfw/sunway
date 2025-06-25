import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO

# --- GitHub Config ---
GITHUB_USERNAME = "limfw"
GITHUB_REPO = "sunway"
GITHUB_TOKEN = st.secrets["github"]["token"]
PARTICIPANT_FILE = "participant.csv"
SCORE_FILE = "manual_scores.csv"

RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/{SCORE_FILE}"
API_URL = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{SCORE_FILE}"

# Game name mappings
GAME_NAMES = {
    "game2": "DodgeBall",
    "game3": "Captain Ball",
    "game4": "Graph-Theoretical",
    "game5": "Topological",
    "game6": "Logic and Recreation"
}

# --- Load Data with Caching ---
@st.cache_data(ttl=0)  # Disable caching for live updates
def load_class_list():
    url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/{PARTICIPANT_FILE}"
    df = pd.read_csv(url)
    df["Class"] = df["Class"].astype(str).str.strip().str.upper()
    return sorted(df["Class"].unique())

@st.cache_data(ttl=0)
def load_scores():
    try:
        df = pd.read_csv(RAW_URL)
        df["Class"] = df["Class"].astype(str).str.strip().str.upper()
        return df
    except:
        return pd.DataFrame(columns=["Class"] + list(GAME_NAMES.keys()))

# --- GitHub Upload Function ---
def upload_to_github(updated_df):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    # Get current SHA
    get_resp = requests.get(API_URL, headers=headers)
    if get_resp.status_code != 200:
        st.error(f"❌ Failed to fetch file SHA: {get_resp.text}")
        return False

    sha = get_resp.json()["sha"]
    csv_content = updated_df.to_csv(index=False)
    encoded_content = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")

    data = {
        "message": "✅ Update manual_scores.csv via score_entry_app",
        "content": encoded_content,
        "branch": "main",
        "sha": sha
    }

    put_resp = requests.put(API_URL, headers=headers, json=data)
    return put_resp.status_code == 200

# --- Streamlit UI ---
st.set_page_config(page_title="Enter Game Scores", layout="centered")
st.title("🎯 Game Score Entry Portal")
st.info("Select a game and enter scores for each team.")

# --- Force Refresh Button ---
if st.button("♻️ Force Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# --- Game Selector ---
game_option = st.selectbox(
    "Select game to enter score:", 
    options=list(GAME_NAMES.keys()),
    format_func=lambda x: GAME_NAMES[x]
)

# --- Load Data ---
all_classes = load_class_list()
scores_df = load_scores()

# Ensure all classes exist in scores
for c in all_classes:
    if c not in scores_df["Class"].values:
        new_row = {"Class": c}
        for g in GAME_NAMES:
            new_row[g] = 0
        scores_df = pd.concat([scores_df, pd.DataFrame([new_row])], ignore_index=True)

# --- Score Entry UI ---
st.markdown(f"### 📝 Enter scores for {GAME_NAMES[game_option]}")
updated_scores = {}
for c in all_classes:
    score = st.number_input(f"Team {c} score:", min_value=0, max_value=100, step=1, key=c)
    updated_scores[c] = score

if st.button("✅ Submit Scores"):
    for c in updated_scores:
        scores_df.loc[scores_df["Class"] == c, game_option] = updated_scores[c]
    
    if upload_to_github(scores_df):
        st.success("✅ Scores updated successfully!")
    else:
        st.error("❌ Failed to upload scores.")

# --- Display Tables ---
st.markdown("### 📊 Current Scores")
tab1, tab2 = st.tabs(["Horizontal Scroll", "Transposed View"])

with tab1:
    st.dataframe(scores_df, width=1000, height=400, use_container_width=True)

with tab2:
    st.dataframe(
        scores_df.set_index("Class").T,
        width=1000,
        height=400,
        use_container_width=True
    )
