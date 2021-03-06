from collections import defaultdict
import random
import time
import numpy as np
import copy
import random
import collections
from game import Board, Game
from statistics import Statistic
from players.vanilla_uct_player import Vanilla_UCT
from players.scripts.random_script import RandomPlayer
from players.scripts.lelis_script import LelisPlayer
from players.scripts.DSL import DSL
import sys


if __name__ == "__main__":    
    
    random = RandomPlayer()
    lelis = LelisPlayer()
    
#     import importlib
#     module = importlib.import_module('players.scripts.generated.Script1')
#     class_ = getattr(module, 'Script1')
#     instance = class_()
    
    dsl = DSL()
    dsl.generateRandomScript(1)

    victories1 = 0
    victories2 = 0
    for _ in range(1):
        game = Game(n_players = 2, dice_number = 4, dice_value = 3, column_range = [2,6],
                    offset = 2, initial_height = 1)
        uct1 = Vanilla_UCT(c = 1, n_simulations = 10)
        uct2 = Vanilla_UCT(c = 10, n_simulations = 1)
        
        is_over = False
        who_won = None
    
        infinite_loop = 0
        current_player = game.player_turn
        while not is_over:
#             print('Player: ', current_player)
            moves = game.available_moves()
            if game.is_player_busted(moves):
#                 print('Player ', current_player, ' busted!')
                if current_player == 1:
                    current_player = 2
                else:
                    current_player = 1
                continue
            else:
                if game.player_turn == 1:
#                     chosen_play = uct1.get_action(game)
                    chosen_play = lelis.get_action(game)
                else:
#                     chosen_play = instance.get_action(game)
                    chosen_play = random.get_action(game)
                if chosen_play == 'n':
                    if current_player == 1:
                        current_player = 2
                    else:
                        current_player = 1
                print('Chose: ', chosen_play)
                game.print_board()
                game.play(chosen_play)
                game.print_board()
                
                print()
            who_won, is_over = game.is_finished()
        
        print(who_won, is_over)
        if who_won == 1:
            victories1 += 1
        if who_won == 2:
            victories2 += 1
    print(victories1, victories2)
    print('Player 1: ', victories1 / (victories1 + victories2))
    print('Player 2: ', victories2 / (victories1 + victories2))
            
    
    #main()