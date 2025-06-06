# Full Updated app.py with Google Sheets integration

import streamlit as st
import random
import time
from collections import defaultdict, Counter
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Google Sheets Setup ===
def write_result_to_sheet(team_name, result):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("gspread_creds.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("RPS_game_result").sheet1
    sheet.append_row([team_name, result])

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
    st.session_state.last_ai_move = None
    st.session_state.last_player_move = None
    st.session_state.player_streak = 0
    st.session_state.ai_streak = 0
    st.session_state.max_player_streak = 0
    st.session_state.max_ai_streak = 0
    st.session_state.timer_start = time.time()
    st.session_state.team_name = ""

# Ask for Team Name (Once only)
if not st.session_state.team_name:
    st.session_state.team_name = st.text_input("Enter your team name:", key="team_name")
    st.stop()

# --- Countdown Clock ---
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
        if len(moves) >= 1:
            last_move = moves[-1]
            probs = self.transition_counts[last_move]
            total = sum(probs.values())
            rand = random.uniform(0, total)
            cum = 0
            for move, count in probs.items():
                cum += count
                if rand <= cum:
                    return move
        return random.choice(['R', 'P', 'S'])

    def update(self, player_move, result):
        self.move_counts[player_move] += 1
        self.last_player_moves.append(player_move)
        if len(self.last_player_moves) > 10:
            self.last_player_moves.pop(0)
        if len(self.last_player_moves) >= 2:
            prev = self.last_player_moves[-2]
            curr = self.last_player_moves[-1]
            self.transition_counts[prev][curr] += 1

# --- Game Logic ---
def determine_winner(ai, player):
    if ai == player:
        return 'Draw'
    return 'AI' if (ai == 'R' and player == 'S') or (ai == 'P' and player == 'R') or (ai == 'S' and player == 'P') else 'Player'

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
        st.session_state.ai_streak = 0
        st.session_state.player_streak = 0

def play_round(player_move):
    if st.session_state.get("ai") is None:
        st.session_state.ai = RPS_AI()
    if is_game_over():
        return
    ai_move = st.session_state.ai.get_move()
    result = determine_winner(ai_move, player_move)
    st.session_state.ai.update(player_move, result)
    st.session_state.stats[result] += 1
    update_streaks(result)
    st.session_state.history.append({
        'Round': st.session_state.round,
        'Player': player_move,
        'AI': ai_move,
        'Result': result
    })
    st.session_state.last_result = result
    st.session_state.last_ai_move = ai_move
    st.session_state.last_player_move = player_move
    st.session_state.round += 1
    if is_game_over():
        st.session_state.game_over = True

# --- UI ---
st.set_page_config(page_title="RPS Challenge", layout="centered")
st.title("🎮 Rock-Paper-Scissors Challenge")
st.caption("60 rounds or 60 seconds. Play smart.")

st.markdown(f"### ⏱️ Time Remaining: **{remaining_time} seconds**")
st.button("♻️ Reset Game", on_click=reset_game, key='reset_top')

st.progress(min(st.session_state.round / 60, 1.0),
    text=f"Round {min(st.session_state.round, 60)}/60")

st.write("### Make your move:")
cols = st.columns(3)
with cols[0]:
    if st.button("✊ Rock", key='R', disabled=is_game_over()):
        play_round('R')
with cols[1]:
    if st.button("✋ Paper", key='P', disabled=is_game_over()):
        play_round('P')
with cols[2]:
    if st.button("✌️ Scissors", key='S', disabled=is_game_over()):
        play_round('S')

# Stats
a, b, c = st.columns(3)
a.metric("🤖 AI Wins", st.session_state.stats['AI'])
b.metric("👤 Your Wins", st.session_state.stats['Player'])
c.metric("🤝 Draws", st.session_state.stats['Draw'])

if st.session_state.last_result and not is_game_over():
    st.subheader(f"✅ Round {st.session_state.round - 1} Result")
    st.metric("You played", label_full[st.session_state.last_player_move])
    st.metric("AI played", label_full[st.session_state.last_ai_move])
    if st.session_state.last_result == 'Player':
        st.success("You won this round!")
    elif st.session_state.last_result == 'AI':
        st.error("AI won this round!")
    else:
        st.info("It's a draw!")

if is_game_over():
    player_wins = st.session_state.stats['Player']
    ai_wins = st.session_state.stats['AI']
    result = "Player Win" if player_wins > ai_wins else "AI Win" if ai_wins > player_wins else "Draw"
    write_result_to_sheet(st.session_state.team_name, result)

    st.balloons()
    if player_wins > ai_wins:
        st.success(f"🎉 You won {player_wins} – {ai_wins}!")
    elif ai_wins > player_wins:
        st.error(f"😢 AI won {ai_wins} – {player_wins}")
    else:
        st.info(f"🤝 It's a tie! {player_wins} – {ai_wins}")

# --- Auto-refresh ---
if remaining_time > 0 and not st.session_state.game_over:
    time.sleep(1)
    st.rerun()
