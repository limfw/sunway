import streamlit as st
import random
import time
from collections import defaultdict, Counter
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Google Sheets Setup ===
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gspread"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1ONYiSZfhSUhIHU51kTAtuHXDLILLaUnpYlogObG5dA8").worksheet("Sheet1")

# === Session Initialization ===
if "initialized" not in st.session_state:
    st.session_state.round = 1
    st.session_state.ai = None
    st.session_state.stats = {'AI': 0, 'Player': 0, 'Draw': 0}
    st.session_state.history = []
    st.session_state.game_over = False
    st.session_state.last_result = None
    st.session_state.last_ai_move = None
    st.session_state.last_player_move = None
    st.session_state.player_streak = 0
    st.session_state.ai_streak = 0
    st.session_state.max_player_streak = 0
    st.session_state.max_ai_streak = 0
    st.session_state.team_name = ""
    st.session_state.team_code = ""
    st.session_state.result_logged = False
    st.session_state.initialized = True
    st.session_state.timer_start = None

# === Timer Setup ===
remaining_time = 60
if st.session_state.timer_start:
    remaining_time = 60 - int(time.time() - st.session_state.timer_start)
    if remaining_time <= 0:
        remaining_time = 0
        st.session_state.game_over = True

# === RPS AI ===
class RPS_AI:
    def __init__(self):
        self.reset()
    def reset(self):
        self.move_counts = {'R': 1, 'P': 1, 'S': 1}
        self.last_player_moves = []
        self.learning_rate = 0.2
        self.transition_counts = defaultdict(lambda: {'R': 1, 'P': 1, 'S': 1})
        self.move_sequences = defaultdict(int)
    def get_move(self):
        base_randomness = max(0.05, 0.2 - (st.session_state.round * 0.005))
        if random.random() < base_randomness:
            return random.choice(['R', 'P', 'S'])
        predicted = self._predict_player_move()
        return {'R': 'P', 'P': 'S', 'S': 'R'}[predicted]
    def _predict_player_move(self):
        moves = self.last_player_moves
        if len(moves) >= 3 and moves[-1] == moves[-2] == moves[-3]:
            return moves[-1]
        if len(moves) >= 1:
            last = moves[-1]
            probs = self.transition_counts[last]
            total = sum(probs.values())
            rand = random.uniform(0, total)
            cumulative = 0
            for move, count in probs.items():
                cumulative += count
                if rand <= cumulative:
                    return move
        total = sum(self.move_counts.values())
        rand = random.uniform(0, total)
        for move, count in self.move_counts.items():
            rand -= count
            if rand <= 0:
                return move
        return random.choice(['R', 'P', 'S'])
    def update(self, player_move, result):
        self.move_counts[player_move] += 1
        self.last_player_moves.append(player_move)
        if len(self.last_player_moves) > 10:
            self.last_player_moves.pop(0)
        if len(self.last_player_moves) >= 2:
            prev, curr = self.last_player_moves[-2], self.last_player_moves[-1]
            self.transition_counts[prev][curr] += 1
        self.learning_rate = min(0.3, self.learning_rate + 0.02) if result == 'AI' else max(0.1, self.learning_rate - 0.01)

# === Helper Functions ===
def is_game_over():
    return st.session_state.game_over or sum(st.session_state.stats.values()) >= 60

def determine_winner(ai, player):
    if ai == player:
        return 'Draw'
    if (ai == 'R' and player == 'S') or (ai == 'P' and player == 'R') or (ai == 'S' and player == 'P'):
        return 'AI'
    return 'Player'

def update_streaks(result):
    if result == 'Player':
        st.session_state.player_streak += 1
        st.session_state.ai_streak = 0
        st.session_state.max_player_streak = max(st.session_state.max_player_streak, st.session_state.player_streak)
    elif result == 'AI':
        st.session_state.ai_streak += 1
        st.session_state.player_streak = 0
        st.session_state.max_ai_streak = max(st.session_state.max_ai_streak, st.session_state.ai_streak)
    else:
        st.session_state.player_streak = 0
        st.session_state.ai_streak = 0

def play_round(player_move):
    if st.session_state.ai is None:
        st.session_state.ai = RPS_AI()
    if is_game_over():
        return
    ai_move = st.session_state.ai.get_move()
    result = determine_winner(ai_move, player_move)
    st.session_state.ai.update(player_move, result)
    st.session_state.stats[result] += 1
    update_streaks(result)
    st.session_state.history.append({'Round': st.session_state.round, 'Player': player_move, 'AI': ai_move, 'Result': result})
    st.session_state.last_result = result
    st.session_state.last_ai_move = ai_move
    st.session_state.last_player_move = player_move
    st.session_state.round += 1
    if is_game_over():
        st.session_state.game_over = True

# === UI ===
st.set_page_config("RPS Challenge", layout="centered")
st.title("🎮 Rock-Paper-Scissors Challenge")
st.markdown(f"### ⏱️ Time Remaining: **{remaining_time} seconds**")

# Form for team info
if not st.session_state.team_name or not st.session_state.team_code:
    with st.form("team_info"):
        st.session_state.team_name = st.text_input("Enter Team Name")
        st.session_state.team_code = st.text_input("Enter Team Code")
        submitted = st.form_submit_button("Start Game")
        if submitted:
            st.session_state.timer_start = time.time()
        else:
            st.stop()

# Buttons
st.progress(min(st.session_state.round / 60, 1.0), text=f"Round {min(st.session_state.round, 60)}/60")
cols = st.columns(3)
for move, label in zip(['R', 'P', 'S'], ['✊ Rock', '✋ Paper', '✌️ Scissors']):
    with cols[['R', 'P', 'S'].index(move)]:
        if st.button(label, key=move, disabled=is_game_over(), use_container_width=True):
            play_round(move)

# Metrics
col1, col2, col3 = st.columns(3)
col1.metric("🤖 Computer", st.session_state.stats['AI'], f"Streak: {st.session_state.max_ai_streak}")
col2.metric("👤 You", st.session_state.stats['Player'], f"Streak: {st.session_state.max_player_streak}")
col3.metric("🤝 Draws", st.session_state.stats['Draw'])

# Summary
label_full = {'R': '✊ Rock', 'P': '✋ Paper', 'S': '✌️ Scissors'}
if st.session_state.last_result and not is_game_over():
    st.subheader(f"✅ Round {st.session_state.round - 1} Result")
    res1, res2 = st.columns(2)
    res1.metric("You played", label_full[st.session_state.last_player_move])
    res2.metric("AI played", label_full[st.session_state.last_ai_move])
    st.success("Draw!" if st.session_state.last_result == 'Draw' else "You win!" if st.session_state.last_result == 'Player' else "AI wins!")

# Game over
if is_game_over() and not st.session_state.result_logged:
    result_flag = 1 if st.session_state.stats['Player'] > st.session_state.stats['AI'] else 0
    try:
        cell = sheet.find(st.session_state.team_code)
        time.sleep(1.2)
        sheet.update_cell(cell.row, 3, result_flag)
        st.success("✅ Result updated to Google Sheet!")
    except Exception as e:
        st.error("❌ Could not update result. Please check your team code.")
        st.write(str(e))
    st.session_state.result_logged = True

# Auto refresh
if remaining_time > 0 and not st.session_state.game_over:
    time.sleep(1)
    st.rerun()
