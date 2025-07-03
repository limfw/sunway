import streamlit as st
import random
import time
from collections import defaultdict, Counter
import json
from datetime import datetime
import requests
import base64
import uuid

# --- Label Map ---
label_full = {'R': '✊ Rock', 'P': '✋ Paper', 'S': '✌️ Scissors'}

# @st.cache_data(ttl=60)
def is_team_code_used(team_code):
    github_username = st.secrets['github']['username']
    github_repo = st.secrets['github']['repo']
    github_token = st.secrets['github']['token']
    folder_path = st.secrets['github']['folder']

    url = f"https://api.github.com/repos/{github_username}/{github_repo}/contents/{folder_path}"
    headers = {"Authorization": f"Bearer {github_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        files = response.json()
        for file in files:
            if file["name"].startswith(f"{team_code}_") and file["name"].endswith(".json"):
                return True
        return False
    else:
        st.error("❌ Could not verify previous submissions.")
        return False

# --- Load valid team codes from GitHub CSV ---
@st.cache_data(ttl=60)
def load_team_codes():
    github_username = st.secrets['github']['username']
    github_repo = st.secrets['github']['repo']
    github_token = st.secrets['github']['token']
    file_path = "team_code.csv"

    url = f"https://raw.githubusercontent.com/{github_username}/{github_repo}/main/{file_path}"
    headers = {"Authorization": f"Bearer {github_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        codes = response.text.strip().splitlines()
        return [c.strip() for c in codes if c.strip()]
    else:
        st.error("🚫 Unable to load team codes - please seek for advice.")
        return []


# save the result to github
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


# --- Session Initialization ---
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
    st.session_state.timer_start = None
    st.session_state.initialized = True

# --- Countdown Clock ---
if st.session_state.timer_start is not None:
    remaining_time = max(0, 60 - int(time.time() - st.session_state.timer_start))
    if remaining_time == 0:
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

# --- Helpers ---
def determine_winner(ai_move, player_move):
    if ai_move == player_move:
        return 'Draw'
    if (ai_move == 'R' and player_move == 'S') or \
       (ai_move == 'P' and player_move == 'R') or \
       (ai_move == 'S' and player_move == 'P'):
        return 'AI'
    return 'Player'

def is_game_over():
    return st.session_state.game_over or sum(st.session_state.stats.values()) >= 60

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
st.caption("60 rounds against an adaptive AI that learns your patterns. Can you outsmart it?")


# --- Team Info Form ---
#if "team_code" not in st.session_state or not st.session_state.team_code:
#    with st.form("team_info"):
#        team_name = st.text_input("Enter Team Name")
#        team_code = st.text_input("Enter Team Code")
#        submitted = st.form_submit_button("Start Game")

#        if submitted:
#            st.session_state.team_name = team_name
#            st.session_state.team_code = team_code
#            st.session_state.timer_start = time.time()
#            st.rerun()  # start fresh now that form is submitted
#        else:
#            st.stop()

# --- Team Info Form with GitHub Validation ---
if "team_code" not in st.session_state or not st.session_state.team_code:
    allowed_codes = load_team_codes()

    with st.form("team_info"):
        team_code = st.text_input("Enter Team Code")
        submitted = st.form_submit_button("Start Game")

        if submitted:
            team_code = team_code.strip()
            if team_code in allowed_codes:
                if is_team_code_used(team_code):
                    st.error("🚫 This team has already played. You are not allowed to play again.")
                    st.stop()
                else:
                    st.session_state.team_code = team_code
                    st.session_state.timer_start = time.time()
                    st.success("✅ Valid team code. Starting the game...")
                    st.rerun()
            else:
                st.error("❌ Invalid team code. You are not authorized to play.")
                st.stop()
        else:
            st.stop()


# --- Timer Display ---
if st.session_state.timer_start is not None:
    st.markdown(f"### ⏱️ Time Remaining: **{remaining_time} seconds**")
else:
    st.info("⌛ Waiting for game to start...")

# --- Progress Bar ---
progress_value = min(st.session_state.round / 60, 1.0)
st.progress(progress_value, text=f"Round {min(st.session_state.round, 60)}/60")

# --- Move Buttons ---
st.write("### Make your move:")
cols = st.columns(3)
with cols[0]:
    if st.button("✊ Rock", key='R', disabled=is_game_over(), use_container_width=True):
        play_round('R')
with cols[1]:
    if st.button("✋ Paper", key='P', disabled=is_game_over(), use_container_width=True):
        play_round('P')
with cols[2]:
    if st.button("✌️ Scissors", key='S', disabled=is_game_over(), use_container_width=True):
        play_round('S')

# --- Score Display ---
col1, col2, col3 = st.columns(3)
col1.metric("🤖 Computer Wins", st.session_state.stats['AI'], f"Max streak: {st.session_state.max_ai_streak}")
col2.metric("👤 Your Wins", st.session_state.stats['Player'], f"Max streak: {st.session_state.max_player_streak}")
col3.metric("🤝 Draws", st.session_state.stats['Draw'])

# --- Last Result ---
if st.session_state.last_result and not is_game_over():
    st.subheader(f"✅ Round {st.session_state.round - 1} Result")
    res_col1, res_col2 = st.columns(2)
    with res_col1:
        st.metric("You played", label_full[st.session_state.last_player_move])
    with res_col2:
        st.metric("AI played", label_full[st.session_state.last_ai_move])
    if st.session_state.last_result == 'Draw':
        st.success("It's a draw!")
    elif st.session_state.last_result == 'Player':
        st.success("You won this round!")
    else:
        st.error("AI won this round!")

# --- Stats Summary ---
if st.session_state.history:
    st.write("## Move Statistics")
    all_player_moves = [x['Player'] for x in st.session_state.history]
    player_move_counts = Counter(all_player_moves)
    for move in ['R', 'P', 'S']:
        count = player_move_counts.get(move, 0)
        st.write(f"{label_full[move]}: {count} times ({count / len(all_player_moves) * 100:.1f}%)")

# --- Game Over ---
if is_game_over():
    st.balloons()
    st.success("### 🏁 Game Over!")
    player_wins = st.session_state.stats['Player']
    ai_wins = st.session_state.stats['AI']
    if player_wins > ai_wins:
        st.success(f"## 🎉 You won {player_wins}-{ai_wins}!")
    elif ai_wins > player_wins:
        st.error(f"## 😢 AI won {ai_wins}-{player_wins}")
    else:
        st.info(f"## 🤝 It's a tie! {player_wins}-{ai_wins}")

# Save results when game is over (only once)
if is_game_over() and not st.session_state.result_logged:
    st.session_state.result_logged = True
    try:
        file_url = save_result_to_github()
        st.session_state.saved_file_url = file_url
        st.success("✅ Result saved - Thanks.")
    except Exception as e:
        st.error("❌ Could not save, please seek advise .")
        st.write(str(e))

# --- Auto Refresh Logic (Safe) ---
# Only auto-rerun when game is still ongoing
if (
    "timer_start" in st.session_state and
    st.session_state.timer_start is not None and
    remaining_time > 0 and
    not st.session_state.game_over and
    not st.session_state.result_logged  # ✅ Don't rerun after logging
):
    time.sleep(1)
    st.rerun()

