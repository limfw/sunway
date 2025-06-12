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

        # Update streaks
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

    # Show current status
    st.markdown(f"**🧠 AI Move:** {st.session_state.last_ai_move}")
    st.markdown(f"**🧑 Player Move:** {st.session_state.last_player_move}")
    st.markdown(f"**🏁 Result:** {st.session_state.last_result}")
    st.markdown("---")
    st.metric("Player Wins", st.session_state.stats['Player'])
    st.metric("AI Wins", st.session_state.stats['AI'])
    st.metric("Draws", st.session_state.stats['Draw'])

    if st.session_state.round > 30 or remaining_time <= 0:
        st.session_state.game_over = True
        st.success("🏁 Game Over! Thanks for playing.")
