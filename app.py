import streamlit as st
import random
import time
from collections import defaultdict, Counter
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

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
    st.session_state.last_ai_move = None
    st.session_state.last_player_move = None
    st.session_state.player_streak = 0
    st.session_state.ai_streak = 0
    st.session_state.max_player_streak = 0
    st.session_state.max_ai_streak = 0
    st.session_state.timer_start = time.time()
    st.session_state.result_logged = False
    st.session_state.team_name = ""
    st.session_state.team_code = ""

# --- Countdown Clock ---
remaining_time = 60 - int(time.time() - st.session_state.timer_start)
if remaining_time <= 0:
    remaining_time = 0
    st.session_state.game_over = True

# --- Game Over Check ---
def is_game_over():
    return st.session_state.game_over or sum(st.session_state.stats.values()) >= 60

# --- Reset Game ---
def reset_game():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.timer_start = time.time()

# --- Enhanced AI Class ---
class RPS_AI:
    def __init__(self):
        self.reset()

    def reset(self):
        self.move_counts = {'R': 1, 'P': 1, 'S': 1}
        self.last_player_moves = []
        self.learning_rate = 0.2
        self.pattern_memory = defaultdict(list)
        self.transition_counts = defaultdict(lambda: {'R': 1, 'P': 1, 'S': 1})
        self.move_sequences = defaultdict(int)

    def get_move(self):
        base_randomness = max(0.05, 0.2 - (st.session_state.round * 0.005))
        if random.random() < base_randomness:
            return random.choice(['R', 'P', 'S'])
        predicted_move = self._predict_player_move()
        return self._counter_move(predicted_move)

    def _predict_player_move(self):
        moves = self.last_player_moves
        if len(moves) >= 4:
            if moves[-4:-1] == moves[-3:]:
                return moves[-1]
            sequence = tuple(moves[-4:])
            if sequence in self.move_sequences:
                return self.move_sequences[sequence]
        if len(moves) >= 3:
            if moves[-1] == moves[-2] == moves[-3]:
                return moves[-1]
            common_sequences = {
                ('R', 'P', 'S'): 'R',
                ('P', 'S', 'R'): 'P',
                ('S', 'R', 'P'): 'S'
            }
            last_three = tuple(moves[-3:])
            if last_three in common_sequences:
                return common_sequences[last_three]
        if len(moves) >= 1:
            last_move = moves[-1]
            probs = self.transition_counts[last_move]
            total = sum(probs.values())
            rand = random.uniform(0, total)
            cumulative = 0
            for move, count in probs.items():
                cumulative += count
                if rand <= cumulative:
                    return move
        total = sum(self.move_counts.values())
        rand = random.uniform(0, total)
        cumulative = 0
        for move, count in self.move_counts.items():
            cumulative += count
            if rand <= cumulative:
                return move
        return random.choice(['R', 'P', 'S'])

    def _counter_move(self, predicted_move):
        if random.random() < 0.15:
            return random.choice(['R', 'P', 'S'])
        return {'R': 'P', 'P': 'S', 'S': 'R'}[predicted_move]

    def update(self, player_move, result):
        self.move_counts[player_move] += 1
        self.last_player_moves.append(player_move)
        if len(self.last_player_moves) > 10:
            self.last_player_moves.pop(0)
        if len(self.last_player_moves) >= 2:
            prev = self.last_player_moves[-2]
            curr = self.last_player_moves[-1]
            self.transition_counts[prev][curr] += 1
        if len(self.last_player_moves) >= 4:
            sequence = tuple(self.last_player_moves[-4:-1])
            self.move_sequences[sequence] = self.last_player_moves[-1]
        if result == 'AI':
            self.learning_rate = min(0.3, self.learning_rate + 0.02)
        else:
            self.learning_rate = max(0.1, self.learning_rate - 0.01)

# --- Game Logic ---
def determine_winner(ai_move, player_move):
    if ai_move == player_move:
        return 'Draw'
    if (ai_move == 'R' and player_move == 'S') or \
       (ai_move == 'P' and player_move == 'R') or \
       (ai_move == 'S' and player_move == 'P'):
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

# Team name + code
if not st.session_state.team_name or not st.session_state.team_code:
    with st.form("team_form"):
        st.session_state.team_name = st.text_input("Enter Team Name")
        st.session_state.team_code = st.text_input("Enter Team Code")
        submitted = st.form_submit_button("Start Game")
        if not submitted:
            st.stop()

# Game logic triggers on button clicks
if not is_game_over():
    st.write(f"⏳ Time Remaining: {remaining_time} seconds")
    st.write(f"Round {st.session_state.round} of 60")
    col1, col2, col3 = st.columns(3)
    if col1.button("✊ Rock"):
        play_round('R')
    if col2.button("✋ Paper"):
        play_round('P')
    if col3.button("✌️ Scissors"):
        play_round('S')

    st.write(f"Last result: **{st.session_state.last_result}**" if st.session_state.last_result else "No move yet")

# --- Auto-log result if game is over and not logged ---
if is_game_over() and not st.session_state.result_logged:
    player_wins = st.session_state.stats['Player']
    ai_wins = st.session_state.stats['AI']
    win_flag = 1 if player_wins > ai_wins else 0
    sheet.append_row([st.session_state.team_name, st.session_state.team_code, win_flag])
    st.success("✅ Result saved to Google Sheet!")
    st.session_state.result_logged = True
