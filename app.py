import streamlit as st
import random
from collections import defaultdict, Counter

# --- Label Map ---
label_full = {'R': 'Rock', 'P': 'Paper', 'S': 'Scissors'}

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

# --- Adaptive AI Class ---
class RPS_AI:
    def __init__(self):
        self.reset()

    def reset(self):
        self.move_counts = {'R': 0, 'P': 0, 'S': 0}
        self.last_player_moves = []
        self.learning_rate = 0.2
        self.pattern_memory = defaultdict(list)
        self.transition_counts = defaultdict(lambda: {'R': 1, 'P': 1, 'S': 1})

    def get_move(self):
        if st.session_state.round <= 5:
            return random.choice(['R', 'P', 'S'])
        predicted_move = self._predict_player_move()
        return self._counter_move(predicted_move)

    def _predict_player_move(self):
        moves = self.last_player_moves
        if len(moves) >= 3:
            if moves[-3:] == ['R', 'P', 'S']:
                return 'R'
            if moves[-1] == moves[-2] == moves[-3]:
                return moves[-1]
        if len(moves) >= 1:
            last = moves[-1]
            probs = self.transition_counts[last]
            total = sum(probs.values())
            r_prob = probs['R'] / total
            p_prob = probs['P'] / total
            rand = random.random()
            return 'R' if rand < r_prob else 'P' if rand < r_prob + p_prob else 'S'
        total = sum(self.move_counts.values())
        if total == 0:
            return random.choice(['R', 'P', 'S'])
        r_prob = self.move_counts['R'] / total
        p_prob = self.move_counts['P'] / total
        rand = random.random()
        return 'R' if rand < r_prob else 'P' if rand < r_prob + p_prob else 'S'

    def _counter_move(self, predicted_move):
        randomness = 0.1 + 0.1 * (1 - self.learning_rate)
        if random.random() < randomness:
            return random.choice(['R', 'P', 'S'])
        return {'R': 'P', 'P': 'S', 'S': 'R'}[predicted_move]

    def update(self, player_move, result):
        self.move_counts[player_move] += 1
        self.last_player_moves.append(player_move)
        if len(self.last_player_moves) > 5:
            self.last_player_moves.pop(0)
        if len(self.last_player_moves) >= 2:
            prev = self.last_player_moves[-2]
            curr = self.last_player_moves[-1]
            self.transition_counts[prev][curr] += 1
        self.pattern_memory[tuple(self.last_player_moves[-3:])].append(result)
        self.learning_rate = min(0.3, max(0.1,
            self.learning_rate + (0.02 if result == 'AI' else -0.01)))

# --- Game Logic ---
def determine_winner(ai_move, player_move):
    if ai_move == player_move:
        return 'Draw'
    if (ai_move == 'R' and player_move == 'S') or \
       (ai_move == 'P' and player_move == 'R') or \
       (ai_move == 'S' and player_move == 'P'):
        return 'AI'
    return 'Player'

def reset_game():
    for key in list(st.session_state.keys()):
        del st.session_state[key]

def is_game_over():
    return sum(st.session_state.stats.values()) >= 30

def play_round(player_move):
    if st.session_state.get("ai") is None:
        st.session_state.ai = RPS_AI()

    if is_game_over():
        return

    ai_move = st.session_state.ai.get_move()
    result = determine_winner(ai_move, player_move)

    st.session_state.ai.update(player_move, result)
    st.session_state.stats[result] += 1
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

# --- UI Starts Here ---
st.set_page_config(page_title="Can you defeat the computer?", layout="centered")
st.title("Can you defeat the computer, 🤖 ?")
st.caption("30 rounds. Every move you make is remembered. This is your challenge.")

st.button("♻️ Reset Game", on_click=reset_game, key='reset_top')

# ✅ Safe Progress Bar
progress_value = min(st.session_state.round / 30, 1.0)
st.progress(progress_value, text=f"Round {min(st.session_state.round, 30)}/30")

# --- Move Buttons ---
st.write("### Make your move:")
cols = st.columns(3)
with cols[0]:
    if st.button("✊ Rock", key='R', disabled=is_game_over()):
        if not is_game_over(): play_round('R')
with cols[1]:
    if st.button("✋ Paper", key='P', disabled=is_game_over()):
        if not is_game_over(): play_round('P')
with cols[2]:
    if st.button("✌️ Scissors", key='S', disabled=is_game_over()):
        if not is_game_over(): play_round('S')

# --- Scoreboard ---
col1, col2, col3 = st.columns(3)
col1.metric("🤖 Computer Wins", st.session_state.stats['AI'])
col2.metric("👤 Your Wins", st.session_state.stats['Player'])
col3.metric("🤝 Draws", st.session_state.stats['Draw'])

# --- Last Result Display ---
if st.session_state.last_result and not is_game_over():
    st.subheader(f"✅ Round {st.session_state.round - 1} Result")
    st.write(f"- You played: **{label_full.get(st.session_state.last_player_move, '?')}**")
    st.write(f"- AI played: **{label_full.get(st.session_state.last_ai_move, '?')}**")
    st.write(f"- Result: **{st.session_state.last_result}**")

# --- Game Over Block ---
if is_game_over():
    st.session_state.game_over = True
    st.balloons()
    st.success("### 🏁 Game Over!")

    winner = "You!" if st.session_state.stats['Player'] > st.session_state.stats['AI'] else \
             "AI!" if st.session_state.stats['AI'] > st.session_state.stats['Player'] else "It's a tie!"
    st.write(f"Final winner: **{winner}**")

    all_moves = [x['Player'] for x in st.session_state.history]
    most_common = Counter(all_moves).most_common(1)[0][0] if all_moves else "-"
    full_name = label_full.get(most_common, "-")
    st.info(f"🧠 Your most frequent move: **{full_name}**")

    st.markdown("🔍 This was an **Adaptive AI model**.")
    st.markdown("It learned from your choices and tried to predict your next move in real time.")

    with st.expander("🤖 How Adaptive AI can evolve into Generative AI"):
        st.markdown("""
        **Adaptive AI** learns in real time.
        It watches your moves, detects patterns, and adjusts its strategy on the fly — like a chess master who counters your every tactic mid-game.

        **Generative AI** takes this further.
        It creates strategies by simulating thousands of games, training deep neural networks (like LSTMs or Transformers), and using Reinforcement Learning to refine its decisions. It doesn’t just predict your next move — it anticipates your intent.

        Passionate about AI innovation?

        **Inspiration Behind This Game:**
        1. MIT’s Adaptive Rock-Paper-Scissors Project  
        2. DeepMind’s AlphaGo
        """)

    st.button("🔄 Play Again", on_click=reset_game, key='reset_bottom')
