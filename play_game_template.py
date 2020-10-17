from game import Game
from players.vanilla_uct_player import Vanilla_UCT
from players.random_player import RandomPlayer
from players.uct_player import UCTPlayer

def play_single_game(player1, player2, game, max_game_length):
    """
    Play a single game between player1 and player2.
    Return 1 if player1 won, 2 if player2 won or if the game reached the max
    number of iterations, it returns 0 representing a draw.
    """

    is_over = False
    rounds = 0
    # actions_taken actions in a row from a player. Used in UCTPlayer players. 
    # List of tuples (action taken, player turn, Game instance).
    # If players change turn, empty the list.
    actions_taken = []
    actions_from_player = 1

    # Game loop
    while not is_over:
        rounds += 1
        moves = game.available_moves()
        if game.is_player_busted(moves):
            actions_taken = []
            actions_from_player = game.player_turn
            continue
        else:
            # UCTPlayer players receives an extra parameter in order to
            # maintain the tree between plays whenever possible
            if game.player_turn == 1 and isinstance(player1, UCTPlayer):
                if actions_from_player == game.player_turn:
                    chosen_play = player1.get_action(game, [])
                else:
                    chosen_play = player1.get_action(game, actions_taken)
            elif game.player_turn == 1 and not isinstance(player1, UCTPlayer):
                    chosen_play = player1.get_action(game)
            elif game.player_turn == 2 and isinstance(player2, UCTPlayer):
                if actions_from_player == game.player_turn:
                    chosen_play = player2.get_action(game, [])
                else:
                    chosen_play = player2.get_action(game, actions_taken)
            elif game.player_turn == 2 and not isinstance(player2, UCTPlayer):
                    chosen_play = player2.get_action(game)

            # Needed because game.play() can automatically change 
            # the player_turn attribute.
            actual_player = game.player_turn
            
            # Clear the plays info so far if player_turn 
            # changed last iteration.
            if actions_from_player != actual_player:
                actions_taken = []
                actions_from_player = game.player_turn

            # Apply the chosen_play in the game
            game.play(chosen_play)

            # Save game history
            actions_taken.append((chosen_play, actual_player, game.clone()))

        # if the game has reached its max number of plays, end the game
        # and who_won receives 0, which means no players won.

        if rounds > max_game_length:
            who_won = 0
            is_over = True
        else:
            who_won, is_over = game.is_finished()

    return who_won

def simplified_play_single_game(player1, player2, game, max_game_length):
    """
    Play a single game between player1 and player2.
    Return 1 if player1 won, 2 if player2 won or if the game reached the max
    number of iterations, it returns 0 representing a draw.
    In this method, it is not stored what the other player played in previous
    rounds (this info is used in UCTPlayer players in order to maintain the 
    UCT tree between plays).
    """

    is_over = False
    rounds = 0

    # Game loop
    while not is_over:
        rounds += 1
        moves = game.available_moves()
        if game.is_player_busted(moves):
            continue
        else:
            if game.player_turn == 1:
                chosen_play = player1.get_action(game)
            else:
                chosen_play = player2.get_action(game)

            # Apply the chosen_play in the game
            game.play(chosen_play)

        # if the game has reached its max number of plays, end the game
        # and who_won receives 0, which means no players won.

        if rounds > max_game_length:
            who_won = 0
            is_over = True
        else:
            who_won, is_over = game.is_finished()

    return who_won

def play_solitaire_single_game(player, game, max_game_length):
    """ Play a solitaire version of the Can't Stop game. """

    is_over = False
    rounds = 0

    # Game loop
    while not is_over:
        moves = game.available_moves()
        if game.is_player_busted(moves):
            game.player_turn = 1
            rounds += 1
            continue
        else:
            chosen_play = player.get_action(game)
            # Apply the chosen_play in the game
            game.play(chosen_play)
            if chosen_play == 'n':
                rounds += 1
            game.player_turn = 1

        # if the game has reached its max number of plays, end the game
        # and who_won receives 0, which means no players won.

        if rounds > max_game_length:
            who_won = 0
            is_over = True
        else:
            who_won, is_over = game.is_finished()

    return rounds

def play_solitaire_single_game_for_uct(player, game, max_game_length):
    """ Play a solitaire version of the Can't Stop game. """

    is_over = False
    rounds = 0

    # Game loop
    while not is_over:
        moves = game.available_moves()
        if game.is_player_busted(moves):
            game.player_turn = 1
            rounds += 1
            continue
        else:
            chosen_play = player.get_action(game, [])
            # Apply the chosen_play in the game
            game.play(chosen_play)
            if chosen_play == 'n':
                rounds += 1
            game.player_turn = 1

        # if the game has reached its max number of plays, end the game
        # and who_won receives 0, which means no players won.

        if rounds > max_game_length:
            who_won = 0
            is_over = True
        else:
            who_won, is_over = game.is_finished()

    return rounds


def main():
    
    # Original version
    column_range = [2,12]
    offset = 2
    initial_height = 2 
    n_players = 2
    dice_number = 4
    dice_value = 6 
    max_game_length = 500
    '''
    for i in range(10):
        game = Game(n_players, dice_number, dice_value, column_range, offset, 
                initial_height)
        uct_vanilla_1 = Vanilla_UCT(c = 1, n_simulations = 10)
        uct_vanilla_2 = Vanilla_UCT(c = 1, n_simulations = 100)
        random_player = RandomPlayer()

        who_won = play_single_game(uct_vanilla_1, uct_vanilla_2, game, 50)
        print('Winner from game', i, '= ', who_won)
    '''
    from players.vanilla_uct_player import Vanilla_UCT
    from players.random_player import RandomPlayer
    from players.uct_player import UCTPlayer
    from players.rule_of_28_player import Rule_of_28_Player
    from players.glenn_player import Glenn_Player
    import pickle
    import math
    n_games = 100
    n_simulations = 500
    rounds = []
    filename = 'solitaire_vanilla_' + str(n_simulations) + '.txt'
    print('n_simulations = ', n_simulations)
    for i in range(n_games):
        game = Game(n_players, dice_number, dice_value, column_range, offset, 
                initial_height)
        #script = Rule_of_28_Player()
        #script = Glenn_Player()
        script = Vanilla_UCT(c = 1, n_simulations = n_simulations)

        #n_round = play_solitaire_single_game(script, game, 5000)
        n_round = play_solitaire_single_game_for_uct(script, game, 10000)
        rounds.append(n_round)
        with open(filename, 'a') as f:
            print('Iteration', i, '- Number of rounds = ', n_round, file=f)
        with open('solitaire_vanilla_' + str(n_simulations) + '_data' , 'wb') as file:
                    pickle.dump(rounds, file)

    avg = sum(rounds) / len(rounds)
    std_sum = 0
    for i in range(len(rounds)):
        std_sum += (rounds[i] - avg) * (rounds[i] - avg)

    std_round = math.sqrt(std_sum / len(rounds)) 
    with open(filename, 'a') as f:
        print('Round average = ', avg, file=f)
        print('Round std = ', std_round, file=f)
        print('Max = ', max(rounds), file=f)
    #print(rounds)

if __name__ == "__main__":
    main()