import streamlit as st
import random
import time
from collections import defaultdict, Counter
import json
from datetime import datetime
import os
import requests
import base64
import uuid

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
    st.session_state.team_name = ""
    st.session_state.team_code = ""
    st.session_state.result_logged = False
    st.session_state.timer_start = None
    st.session_state.saved_file_url = ""

# --- Team Info Form ---
if not st.session_state.team_code:
    with st.form("team_info"):
        team_name = st.text_input("Enter Team Name")
        team_code = st.text_input("Enter Team Code")
        submitted = st.form_submit_button("Start Game")

        if submitted:
            st.session_state.team_name = team_name
            st.session_state.team_code = team_code
            st.session_state.timer_start = time.time()

# --- Countdown Clock ---
if st.session_state.timer_start is not None:
    remaining_time = 60 - int(time.time() - st.session_state.timer_start)
    if remaining_time <= 0:
        remaining_time = 0
        st.session_state.game_over = True
else:
    remaining_time = 60

# --- AI Class ---
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

# --- GitHub Save Function ---
def save_result_to_github():
    result_data = {
        "team_code": st.session_state.team_code,
        "timestamp": datetime.now().isoformat(),
        "win": 1 if st.session_state.stats['Player'] > st.session_state.stats['AI'] else 0
    }
    json_content = json.dumps(result_data, indent=2)
    encoded = base64.b64encode(json_content.encode()).decode()
    unique_id = uuid.uuid4().hex
    filename = f"{st.session_state.team_code}_{unique_id}.json"
    filepath = f"{st.secrets['github']['folder']}/{filename}"
    url = f"https://api.github.com/repos/{st.secrets['github']['username']}/{st.secrets['github']['repo']}/contents/{filepath}"

    headers = {
        "Authorization": f"Bearer {st.secrets['github']['token']}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "message": f"Save result for team {st.session_state.team_code}",
        "content": encoded
    }

    put_resp = requests.put(url, headers=headers, json=payload)

    if put_resp.status_code in [200, 201]:
        return f"https://github.com/{st.secrets['github']['username']}/{st.secrets['github']['repo']}/blob/main/{filepath}"
    else:
        raise Exception(f"GitHub upload failed: {put_resp.status_code} — {put_resp.text}")

# --- Countdown display block ---
if st.session_state.timer_start is not None:
    st.markdown(f"### ⏱️ Time Remaining: **{remaining_time} seconds**")

# --- Gameplay block ---
if st.session_state.team_code and not st.session_state.game_over:
    st.subheader(f"Round {st.session_state.round}")
    st.write("Choose your move:")
    col1, col2, col3 = st.columns(3)
    move = None
    if col1.button("✊ Rock"):
        move = 'R'
    elif col2.button("✋ Paper"):
        move = 'P'
    elif col3.button("✌️ Scissors"):
        move = 'S'

    if move:
        if not st.session_state.ai:
            st.session_state.ai = RPS_AI()
        ai_move = st.session_state.ai.get_move()
        player_move = move

        st.session_state.last_player_move = label_full[player_move]
        st.session_state.last_ai_move = label_full[ai_move]

        result = None
        if player_move == ai_move:
            result = 'Draw'
        elif (player_move == 'R' and ai_move == 'S') or \
             (player_move == 'P' and ai_move == 'R') or \
             (player_move == 'S' and ai_move == 'P'):
            result = 'Player'
        else:
            result = 'AI'

        st.session_state.stats[result] += 1
        st.session_state.history.append((label_full[player_move], label_full[ai_move], result))

        if result == 'Player':
            st.session_state.player_streak += 1
            st.session_state.ai_streak = 0
        elif result == 'AI':
            st.session_state.ai_streak += 1
            st.session_state.player_streak = 0
        else:
            st.session_state.player_streak = 0
            st.session_state.ai_streak = 0

        st.session_state.max_player_streak = max(st.session_state.max_player_streak, st.session_state.player_streak)
        st.session_state.max_ai_streak = max(st.session_state.max_ai_streak, st.session_state.ai_streak)

        st.session_state.round += 1
        st.session_state.ai.update(player_move, result)

    st.markdown(f"**🧠 AI Move:** {st.session_state.last_ai_move}")
    st.markdown(f"**🧑 Player Move:** {st.session_state.last_player_move}")
    st.markdown("---")
    st.metric("Player Wins", st.session_state.stats['Player'])
    st.metric("AI Wins", st.session_state.stats['AI'])
    st.metric("Draws", st.session_state.stats['Draw'])

    if st.session_state.round > 30 or remaining_time <= 0:
        st.session_state.game_over = True
        st.success("🏁 Game Over! Thanks for playing.")

# --- Save result when game ends ---
if st.session_state.game_over and not st.session_state.result_logged:
    try:
        file_url = save_result_to_github()
        st.session_state.saved_file_url = file_url
        st.session_state.result_logged = True
        st.success("✅ Result saved to GitHub.")
    except Exception as e:
        st.error("❌ Failed to save result to GitHub.")
        st.text(str(e))
