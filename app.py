import streamlit as st
import random
import time
from collections import defaultdict
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Google Sheets Setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gspread_creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open("RPS_Game_Result").worksheet("Sheet1")

# --- Label Map ---
label_full = {'R': '✊ Rock', 'P': '✋ Paper', 'S': '✌️ Scissors'}

# --- Session Initialization ---
if "round" not in st.session_state:
    st.session_state.round = 1
    st.session_state.ai = None
    st.session_state.stats = {'AI': 0, 'Player': 0, 'Draw': 0}
    st.session_state.history = []
    st.session_state.game_over = False
    st.session_state.last_result = None
    st.session_state.timer_start = time.time()
    st.session_state.result_logged = False
    st.session_state.team_name = ""
    st.session_state.team_code = ""

# --- Timer ---
remaining_time = 60 - int(time.time() - st.session_state.timer_start)
if remaining_time <= 0:
    remaining_time = 0
    st.session_state.game_over = True

def is_game_over():
    return st.session_state.game_over or sum(st.session_state.stats.values()) >= 60

def reset_game():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.timer_start = time.time()

# --- AI Class ---
class RPS_AI:
    def __init__(self):
        self.reset()

    def reset(self):
        self.move_counts = {'R': 1, 'P': 1, 'S': 1}
        self.last_player_moves = []
        self.transition_counts = defaultdict(lambda: {'R': 1, 'P': 1, 'S': 1})

    def get_move(self):
        if len(self.last_player_moves) >= 1:
            last = self.last_player_moves[-1]
            probs = self.transition_counts[last]
            total = sum(probs.values())
            rand = random.uniform(0, total)
            cum = 0
            for move, count in probs.items():
                cum += count
                if rand <= cum:
                    return self._counter_move(move)
        return random.choice(['R', 'P', 'S'])

    def _counter_move(self, move):
        return {'R': 'P', 'P': 'S', 'S': 'R'}[move]

    def update(self, player_move, result):
        self.move_counts[player_move] += 1
        self.last_player_moves.append(player_move)
        if len(self.last_player_moves) >= 2:
            prev = self.last_player_moves[-2]
            curr = self.last_player_moves[-1]
            self.transition_counts[prev][curr] += 1

# --- Game Logic ---
def determine_winner(ai, player):
    if ai == player:
        return 'Draw'
    if (ai == 'R' and player == 'S') or (ai == 'P' and player == 'R') or (ai == 'S' and player == 'P'):
        return 'AI'
    return 'Player'

def play_round(player_move):
    if st.session_state.get("ai") is None:
        st.session_state.ai = RPS_AI()
    if is_game_over():
        return
    ai_move = st.session_state.ai.get_move()
    result = determine_winner(ai_move, player_move)
    st.session_state.ai.update(player_move, result)
    st.session_state.stats[result] += 1
    st.session_state.history.append((st.session_state.round, player_move, ai_move, result))
    st.session_state.last_result = result
    st.session_state.round += 1
    if is_game_over():
        st.session_state.game_over = True

# --- UI ---
st.set_page_config(page_title="Rock Paper Scissors", layout="centered")
st.title("🎮 Rock-Paper-Scissors Challenge")

# --- Team Form ---
if not st.session_state.team_name or not st.session_state.team_code:
    with st.form("team_form"):
        st.session_state.team_name = st.text_input("Team Name")
        st.session_state.team_code = st.text_input("Team Code")
        submitted = st.form_submit_button("Start Game")
        if not submitted:
            st.stop()

if not is_game_over():
    st.write(f"⏳ Time Remaining: {remaining_time} seconds")
    st.write(f"Round {st.session_state.round}/60")
    col1, col2, col3 = st.columns(3)
    if col1.button("✊ Rock"): play_round('R')
    if col2.button("✋ Paper"): play_round('P')
    if col3.button("✌️ Scissors"): play_round('S')
    st.write(f"Last result: **{st.session_state.last_result}**")

# --- Final Result Logging ---
if is_game_over() and not st.session_state.result_logged:
    player_wins = st.session_state.stats['Player']
    ai_wins = st.session_state.stats['AI']
    win_flag = 1 if player_wins > ai_wins else 0
    sheet.append_row([st.session_state.team_name, st.session_state.team_code, win_flag])
    st.success("✅ Result saved to Google Sheet!")
    st.session_state.result_logged = True

    with st.expander("🤖 AI Performance Analysis"):
        st.markdown("""
        **Adaptive AI Insights:**
        - The AI started randomly but gradually learned your patterns
        - It adjusted its strategy based on your move sequences
        """)
        if player_wins > ai_wins:
            st.success("You outsmarted the AI! Try again to see if it can learn better.")
        else:
            st.info("The AI adapted well. Try new patterns next time!")

    st.button("🔄 Play Again", on_click=reset_game, key='reset_bottom')
