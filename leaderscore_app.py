import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt  # For top 3 bar chart

# --- GitHub Config ---
GITHUB_USERNAME = "limfw"
GITHUB_REPO = "sunway"
SCORE_FILE = "manual_scores.csv"
RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/{SCORE_FILE}"

# Game name mappings (game1 intentionally last)
GAME_NAMES = {
    "game2": "DodgeBall",
    "game3": "Captain Ball",
    "game4": "Graph-Theoretical",
    "game5": "Topological",
    "game6": "Logic and Recreation",
    "game1": "Rock-paper-scissors"  # Last column as requested
}

# --- Load Scores ---
@st.cache_data(ttl=60)
def load_scores():
    df = pd.read_csv(RAW_URL)
    df["Class"] = df["Class"].astype(str).str.strip().str.upper()
    return df

# --- Calculate Leaderboard ---
def calculate_leaderboard(df):
    # Define column order (game2 to game6 first, game1 last)
    game_columns = [f"game{i}" for i in range(2,7)] + ["game1"]
    game_columns = [col for col in game_columns if col in df.columns]
    
    # Calculate totals and rank
    df['Total'] = df[game_columns].sum(axis=1)
    df['Rank'] = df['Total'].rank(method='min', ascending=False).astype(int)
    
    # Return with specified column order
    return df.sort_values('Rank')[['Rank', 'Class', 'Total'] + game_columns]

# --- Streamlit UI ---
st.set_page_config(page_title="Game Leaderboard", layout="wide")
st.title("🏆 Tournament Leaderboard")

try:
    scores_df = load_scores()
    leaderboard = calculate_leaderboard(scores_df)
    
    # --- Top 3 Teams Bar Chart ---
    st.subheader("🎖️ Top 3 Teams")
    top3 = leaderboard.head(3)
    
    fig, ax = plt.subplots()
    ax.barh(
        top3['Class'], 
        top3['Total'],
        color=['gold', 'silver', 'brown']  # Medal colors
    )
    ax.set_xlabel("Total Score")
    ax.invert_yaxis()  # Highest score on top
    st.pyplot(fig)
    
    # --- Main Leaderboard Tabs ---
    tab1, tab2 = st.tabs(["Overall Ranking", "By Game"])
    
    with tab1:
        st.header("Overall Standings")
        st.dataframe(
            leaderboard,
            column_config={
                "Rank": st.column_config.NumberColumn(width="small"),
                "Class": st.column_config.TextColumn("Team"),
                "Total": st.column_config.NumberColumn("Total Score"),
                **{col: st.column_config.NumberColumn(GAME_NAMES[col]) 
                   for col in leaderboard.columns if col.startswith("game")}
            },
            hide_index=True,
            use_container_width=True
        )
    
    with tab2:
        st.header("Individual Game Rankings")
        selected_game = st.selectbox(
            "Select Game:",
            options=list(GAME_NAMES.keys()),
            format_func=lambda x: GAME_NAMES[x],
            index=0  # Default to first game (DodgeBall)
        )
        
        game_rank = scores_df[['Class', selected_game]] \
            .sort_values(selected_game, ascending=False) \
            .reset_index(drop=True)
        game_rank.insert(0, 'Rank', range(1, len(game_rank)+1))
        
        st.dataframe(
            game_rank,
            column_config={
                selected_game: st.column_config.NumberColumn(GAME_NAMES[selected_game])
            },
            use_container_width=True
        )

except Exception as e:
    st.error(f"❌ Error loading data: {str(e)}")

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()
