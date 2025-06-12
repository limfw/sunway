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

# --- Load Participant Info ---
@st.cache_data(ttl=60)
def load_class_list():
    url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/{PARTICIPANT_FILE}"
    df = pd.read_csv(url)
    df["Class"] = df["Class"].astype(str).str.strip().str.upper()
    return sorted(df["Class"].unique())

# --- Load Scores from GitHub ---
@st.cache_data(ttl=60)
def load_scores():
    df = pd.read_csv(RAW_URL)
    df["Class"] = df["Class"].astype(str).str.strip().str.upper()
    return df

# --- GitHub Upload Function ---
def upload_to_github(updated_df):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    # Step 1: Get current SHA of file
    get_resp = requests.get(API_URL, headers=headers)
    if get_resp.status_code != 200:
        st.error(f"\u274c Failed to fetch file SHA: {get_resp.text}")
        return False

    sha = get_resp.json()["sha"]

    # Step 2: Prepare content
    csv_content = updated_df.to_csv(index=False)
    encoded_content = base64.b64encode(csv_content.encode()).decode()

    data = {
        "message": "\u2705 Update manual_scores.csv via score_entry_app",
        "content": encoded_content,
        "branch": "main",
        "sha": sha
    }

    # Step 3: PUT request to update file
    put_resp = requests.put(API_URL, headers=headers, json=data)
    if put_resp.status_code == 200:
        return True
    else:
        st.error(f"\u274c Upload failed: {put_resp.status_code} – {put_resp.text}")
        return False

# --- Streamlit UI ---
st.set_page_config(page_title="\ud83c\udfaf Enter Game Scores", layout="centered")
st.title("\ud83c\udfaf Game Score Entry Portal")
st.info("Select a game and enter scores for each class.")

# --- Game Selector ---
game_option = st.selectbox("Select game to enter score (Game 2 to Game 6):", [f"game{i}" for i in range(2, 7)])

# --- Load Data ---
all_classes = load_class_list()
scores_df = load_scores()

# --- Ensure all classes exist ---
for c in all_classes:
    if c not in scores_df["Class"].values:
        new_row = {"Class": c}
        for g in range(2, 7):
            new_row[f"game{g}"] = 0
        scores_df = pd.concat([scores_df, pd.DataFrame([new_row])], ignore_index=True)

scores_df["Class"] = scores_df["Class"].astype(str).str.strip().str.upper()
scores_df = scores_df.drop_duplicates("Class").reset_index(drop=True)

# --- Score Entry UI ---
st.markdown("### \ud83d\udcdd Enter scores")
updated_scores = {}
for c in all_classes:
    score = st.number_input(f"{c} score:", min_value=0, max_value=100, step=1, key=c)
    updated_scores[c] = score

if st.button("\u2705 Submit Scores"):
    for c in updated_scores:
        scores_df.loc[scores_df["Class"] == c, game_option] = updated_scores[c]

    if upload_to_github(scores_df):
        st.success("\u2705 Scores updated successfully to GitHub!")
    else:
        st.error("\u274c Failed to upload scores.")
