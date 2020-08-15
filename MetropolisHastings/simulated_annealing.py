import sys
sys.path.insert(0,'..')
import math
import copy
from game import Game
from players.rule_of_28_player import Rule_of_28_Player
from play_game_template import simplified_play_single_game
from play_game_template import play_single_game
from players.vanilla_uct_player import Vanilla_UCT
from players.uct_player import UCTPlayer
from players.random_player import RandomPlayer
from MetropolisHastings.parse_tree import ParseTree, Node
from MetropolisHastings.DSL import DSL
from Script import Script
import time
import pickle
import os.path
from random import sample
import numpy as np
import matplotlib.pyplot as plt
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import re


class SimulatedAnnealing:
    def __init__(self, beta, n_iterations, n_games_glenn, n_games_uct, 
        n_uct_playouts, threshold, init_temp, d, tree_max_nodes, string_dataset, 
        column_dataset, max_game_rounds):
        """
        - beta is a constant used in the SA score function.
        - string_data and column_data is a 5-tuple of the game state 
          consisting of: (Game object, chosen_play, Q-value distribution, 
          importance, state round, total number of rounds)
        - n_iterations is the number of iteration in the main MH loop.
        - threshold will sample data only if the state importance is higher
          than this threshold.
        - n_games_glenn is the number of games played against Glenn's heuristic
          for evaluation of the current script.
        - n_games_uct is the number of games played against UCT for evaluation 
          of the current script.
        - n_uct_playouts is the number of playouts used inside UCT in order for 
          it to make a decision (choose an action).
        - init_temp is the temperature used for the first iteration. Following
          temperatures are calculated following self.temperature_schedule().
          Used only for Simulated Annealing.
        - d is a constant for the temperature schedule.
        - tree is a parse tree implementation.
        - string_dataset and column_dataset is the filenames of the datasets 
          generated by the oracle by each type of action.
        """
        self.beta = beta
        self.string_data = []
        self.column_data = []
        self.n_iterations = n_iterations
        self.n_games_glenn = n_games_glenn
        self.n_games_uct = n_games_uct
        self.n_uct_playouts = n_uct_playouts
        self.threshold = threshold
        self.temperature = init_temp
        self.d = d
        self.temperature = init_temp
        self.tree_max_nodes = tree_max_nodes
        self.string_dataset = string_dataset
        self.column_dataset = column_dataset
        self.max_game_rounds = max_game_rounds
        self.tree_string = ParseTree(DSL('S', True), self.tree_max_nodes)
        self.tree_column = ParseTree(DSL('S', False), self.tree_max_nodes)
        self.data_distribution = None

        self.filename = 'SA_' + str(self.n_iterations) + 'ite_' + \
        str(self.threshold).replace(".", "") + 'threshold_' + \
        str(self.tree_max_nodes) + 'tree_' + str(self.n_games_glenn) + \
        'glenn_' + str(self.n_games_uct) + 'uct_' + str(self.n_uct_playouts) + \
        'uct_playouts'

        if not os.path.exists(self.filename):
            os.makedirs(self.filename)

        # For analysis - Games against Glenn
        self.victories_against_glenn = []
        self.losses_against_glenn = []
        self.draws_against_glenn = []

        # For analysis - Games against UCT
        self.victories_against_UCT = []
        self.losses_against_UCT = []
        self.draws_against_UCT = []

    def run(self):
        """ Main routine of the MH algorithm. """

        # Read the dataset
        with open(self.string_dataset, "rb") as f:
            while True:
                try:
                    self.string_data.append(pickle.load(f))
                except EOFError:
                    break
        with open(self.column_dataset, "rb") as f:
            while True:
                try:
                    self.column_data.append(pickle.load(f))
                except EOFError:
                    break
        full_run = time.time()

        data_string, data_column = self.sample_data_from_importance_threshold()

        self.tree_string.build_tree(self.tree_string.root)
        self.tree_column.build_tree(self.tree_column.root)

        # Main loop
        # Starts at 2 because of how the schedule is calculated in SA (to avoid
        # division by zero);
        for i in range(2, self.n_iterations + 2):
            start = time.time()
            # Make a copy of the tree for future mutation
            new_tree_string = pickle.loads(pickle.dumps(self.tree_string, -1))
            new_tree_column = pickle.loads(pickle.dumps(self.tree_column, -1))

            new_tree_string.mutate_tree()
            new_tree_column.mutate_tree()

            current_program_string = self.tree_string.generate_program()
            mutated_program_string = new_tree_string.generate_program()

            current_program_column = self.tree_column.generate_program()
            mutated_program_column = new_tree_column.generate_program()

            script_best_player = self.generate_player(
                                                current_program_string, 
                                                current_program_column,
                                                i
                                                )
            script_mutated_player = self.generate_player(
                                                mutated_program_string,
                                                mutated_program_column,
                                                i
                                                )

            score_best, _, _, _ = self.calculate_score_function(
                                                        script_best_player, 
                                                        data_string,
                                                        data_column
                                                        )
            score_mutated, errors_mutated, errors_rate_mutated, data_distribution = self.calculate_score_function(
                                                        script_mutated_player, 
                                                        data_string,
                                                        data_column
                                                        )
            n_errors = errors_mutated[0]
            n_errors_yes_action = errors_mutated[1]
            n_errors_no_action = errors_mutated[2]
            n_errors_numeric_action = errors_mutated[3]
            total_errors_rate = errors_rate_mutated[0]
            total_yes_errors_rate = errors_rate_mutated[1]
            total_no_errors_rate = errors_rate_mutated[2]
            total_numeric_errors_rate = errors_rate_mutated[3]

            self.data_distribution = data_distribution

            # Update score given the temperature parameters (used only in SA)
            score_best, score_mutated = self.update_score(score_best, score_mutated)

            # Accept program only if new score is higher.
            accept = min(1, score_mutated/score_best)

            # Adjust the temperature accordingly (used only in SA)
            self.temperature = self.temperature_schedule(i)

            # If the new synthesized program is better
            if accept == 1:
                self.tree_string = new_tree_string
                self.tree_column = new_tree_column

                best_program_string = self.tree_string.generate_program()
                best_program_column = self.tree_column.generate_program()
                script_best_player = self.generate_player(
                                                        best_program_string,
                                                        best_program_column,
                                                        i
                                                        )
                start_glenn = time.time()
                v_glenn, l_glenn, d_glenn = self.validate_against_glenn(script_best_player)
                self.victories_against_glenn.append(v_glenn)
                self.losses_against_glenn.append(l_glenn)
                self.draws_against_glenn.append(d_glenn)
                elapsed_time_glenn = time.time() - start_glenn

                start_uct = time.time()
                v_uct, l_uct, d_uct = self.validate_against_UCT(script_best_player)
                self.victories_against_UCT.append(v_uct)
                self.losses_against_UCT.append(l_uct)
                self.draws_against_UCT.append(d_uct)
                elapsed_time_uct = time.time() - start_uct

                elapsed_time = time.time() - start

                # Save data file
                iteration_data = (
                                    n_errors,
                                    n_errors_yes_action,
                                    n_errors_no_action,
                                    n_errors_numeric_action,
                                    total_errors_rate,
                                    total_yes_errors_rate,
                                    total_no_errors_rate,
                                    total_numeric_errors_rate,
                                    v_glenn, l_glenn, d_glenn,
                                    v_uct, l_uct, d_uct
                                )
                folder = self.filename + '/data/' 
                if not os.path.exists(folder):
                    os.makedirs(folder)
                with open(folder + 'datafile_iteration_' + str(i) , 'wb') as file:
                    pickle.dump(iteration_data, file)
                # Save current script
                dir_path = os.path.dirname(os.path.realpath(__file__)) + '/' + self.filename + '/data/' 
                script = Script(
                                best_program_string, 
                                best_program_column, 
                                self.n_iterations, 
                                self.tree_max_nodes
                            )      
                script.save_file_custom(dir_path, self.filename + '_iteration_' + str(i))


                with open(self.filename + '/' + 'log_' + self.filename + '.txt', 'a') as f:
                    print('Iteration -', i, 'New program accepted - V/L/D against Glenn = ',
                        v_glenn, l_glenn, d_glenn, 
                        'V/L/D against UCT', self.n_uct_playouts, 'playouts = ', 
                        v_uct, l_uct, d_uct, file=f)
                    print('Iteration -', i, 'Glenn elapsed time = ', 
                        elapsed_time_glenn, 'UCT elapsed time = ', 
                        elapsed_time_uct, 'Total elapsed time = ', 
                        elapsed_time, file=f)
            else:
                elapsed_time = time.time() - start
                with open(self.filename + '/' + 'log_' + self.filename + '.txt', 'a') as f:
                    print('Iteration -', i, '- Elapsed time: ', elapsed_time, file=f)
        
        best_program_string = self.tree_string.generate_program()
        best_program_column = self.tree_column.generate_program()
        script_best_player = self.generate_player(
                                                best_program_string,
                                                best_program_column,
                                                i
                                                )

        # Save the best script
        dir_path = os.path.dirname(os.path.realpath(__file__)) + '/' + self.filename + '/'
        script = Script(
                        best_program_string, 
                        best_program_column, 
                        self.n_iterations, 
                        self.tree_max_nodes
                    )      
        script.save_file_custom(dir_path, self.filename + '_best_script')

        full_run_elapsed_time = time.time() - full_run
        with open(self.filename + '/' + 'log_' + self.filename + '.txt', 'a') as f:
            print('Full program elapsed time = ', full_run_elapsed_time, file=f)

        self.generate_report()

        return best_program_string, best_program_column, script_best_player, self.tree_string, self.tree_column

    def update_score(self, score_best, score_mutated):
        """ 
        Update the score according to the current temperature. 
        """
        
        new_score_best = score_best**(1 / self.temperature)
        new_score_mutated = score_mutated**(1 / self.temperature)
        return new_score_best, new_score_mutated

    def temperature_schedule(self, iteration):
        """ Calculate the next temperature used for the score calculation. """

        return self.d/math.log(iteration)

    def calculate_score_function(self, program, data_string, data_column):
        """ 
        Score function that calculates who the program passed as parameter 
        "imitates" the actions taken by the oracle in the saved dataset.
        Return this program's score.
        """
        errors, errors_rate, data_distribution = self.calculate_errors(
                                                                program, 
                                                                data_string,
                                                                data_column
                                                                )
        score = math.exp(-self.beta * errors_rate[0])
        return score, errors, errors_rate, data_distribution

    def calculate_errors(self, program, data_string, data_column):
        """ 
        Calculate how many times the program passed as parameter chose a 
        different action when compared to the oracle (actions from dataset).
        Return:
            - n_errors is the number of errors that the program chose when 
              compared to the actions chosen by the oracle.
            - n_errors_yes_action is the number of errors that the program 
              chose for the "yes" action.
            - n_errors_no_action is the number of errors that the program 
              chose for the "no" action.
            - n_errors_numeric_action is the number of errors that the program 
              chose when compared to the "numeric" actions chosen by the oracle.
            - chosen_default_action is the number of times the program chose
              the default action (this means it returned false for every if
              condition). Given in percentage related to the dataset.
        """
        n_errors = 0
        n_errors_yes_action = 0
        n_errors_no_action = 0
        n_errors_numeric_action = 0

        n_data_yes_action = 0
        n_data_no_action = 0
        n_data_numeric_action = 0

        # Yes / No actions
        for i in range(len(data_string)):
            chosen_play = program.get_action(data_string[i][0])
            oracle_play = data_string[i][1]
            # Compare the action chosen by the synthesized script and the oracle
            if chosen_play != oracle_play:
                n_errors += 1

                if oracle_play == 'y':
                    n_errors_yes_action += 1
                else:
                    n_errors_no_action += 1

            #For report purposes
            if oracle_play == 'y':
                n_data_yes_action += 1
            else:
                n_data_no_action += 1

        # Column actions
        for i in range(len(data_column)):
            chosen_play = program.get_action(data_column[i][0])
            oracle_play = data_column[i][1]
            # Compare the action chosen by the synthesized script and the oracle
            if chosen_play != oracle_play:
                n_errors += 1
                n_errors_numeric_action += 1

            #For report purposes
            n_data_numeric_action += 1

        # Proportion yes / no actions
        if n_data_no_action == 0:
            weight = 1
        else:
            weight = n_data_yes_action / n_data_no_action
        n_errors_no_action = n_errors_no_action * weight
        n_data_no_action = n_data_no_action * weight
        total_errors_rate = (n_errors_no_action + n_errors_yes_action + n_errors_numeric_action) / (n_data_yes_action + n_data_no_action + n_data_numeric_action)


        if n_data_yes_action == 0:
            total_yes_errors_rate = 0
        else:
            total_yes_errors_rate = n_errors_yes_action / n_data_yes_action
        if n_data_no_action == 0:
            total_no_errors_rate = 0
        else:
            total_no_errors_rate = n_errors_no_action / n_data_no_action
        if n_data_numeric_action == 0:
            total_numeric_errors_rate = 0
        else:
            total_numeric_errors_rate = n_errors_numeric_action / n_data_numeric_action
        errors = (
                    n_errors, n_errors_yes_action, 
                    n_errors_no_action, n_errors_numeric_action
                )
        errors_rate = (
                        total_errors_rate, 
                        total_yes_errors_rate,
                        total_no_errors_rate,
                        total_numeric_errors_rate
                    )
        data_distribution = (
                            n_data_yes_action,
                            n_data_no_action,
                            n_data_numeric_action  
                        )
        return errors, errors_rate, data_distribution

    def generate_player(self, program_string, program_column, iteration):
        """ Generate a Player object given the program string. """

        script = Script(
                        program_string, 
                        program_column, 
                        self.n_iterations, 
                        self.tree_max_nodes
                    )
        return self._string_to_object(script._generateTextScript(iteration))

    def _string_to_object(self, str_class, *args, **kwargs):
        """ Transform a program written inside str_class to an object. """
        exec(str_class)
        class_name = re.search("class (.*):", str_class).group(1).partition("(")[0]
        return locals()[class_name](*args, **kwargs)

    def sample_data_from_importance_threshold(self):
        """ Sample states that have importance higher than self.threshold. """
        data_string = [d for d in self.string_data if d[3] >= self.threshold]
        data_column = [d for d in self.column_data if d[3] >= self.threshold]
        return data_string, data_column

    def validate_against_glenn(self, current_script):
        """ Validate current script against Glenn's heuristic player. """

        glenn = Rule_of_28_Player()

        victories = 0
        losses = 0
        draws = 0

        for i in range(self.n_games_glenn):
            game = game = Game(2, 4, 6, [2,12], 2, 2)
            if i%2 == 0:
                    who_won = simplified_play_single_game(
                                                        current_script, 
                                                        glenn, 
                                                        game, 
                                                        self.max_game_rounds
                                                    )
                    if who_won == 1:
                        victories += 1
                    elif who_won == 2:
                        losses += 1
                    else:
                        draws += 1
            else:
                who_won = simplified_play_single_game(
                                                    glenn, 
                                                    current_script, 
                                                    game, 
                                                    self.max_game_rounds
                                                )
                if who_won == 2:
                    victories += 1
                elif who_won == 1:
                    losses += 1
                else:
                    draws += 1

        return victories, losses, draws

    def validate_against_UCT(self, current_script):
        """ Validate current script against Glenn's heuristic player. """

        victories = 0
        losses = 0
        draws = 0

        for i in range(self.n_games_glenn):
            game = game = Game(2, 4, 6, [2,12], 2, 2)
            uct = Vanilla_UCT(c = 1, n_simulations = self.n_uct_playouts)
            if i%2 == 0:
                    who_won = play_single_game(
                                                current_script, 
                                                uct, 
                                                game, 
                                                self.max_game_rounds
                                                )
                    if who_won == 1:
                        victories += 1
                    elif who_won == 2:
                        losses += 1
                    else:
                        draws += 1
            else:
                who_won = play_single_game(
                                            uct, 
                                            current_script, 
                                            game, 
                                            self.max_game_rounds
                                            )
                if who_won == 2:
                    victories += 1
                elif who_won == 1:
                    losses += 1
                else:
                    draws += 1

        return victories, losses, draws

    def generate_report(self):
        
        dir_path = os.path.dirname(os.path.realpath(__file__)) + '/' + self.filename + '/' 
        filename = dir_path + self.filename
        x = list(range(len(self.victories_against_glenn)))

        plt.plot(x, self.victories_against_glenn, color='green', label='Victory')
        plt.plot(x, self.losses_against_glenn, color='red', label='Loss')
        plt.plot(x, self.draws_against_glenn, color='gray', label='Draw')
        plt.legend(loc="best")
        plt.title("Simulated Annealing - Games against Glenn")
        plt.xlabel('Iterations')
        plt.ylabel('Number of games')
        plt.savefig(filename + '_vs_previous_script.png')

        plt.close()

        x = list(range(len(self.victories_against_UCT)))

        plt.plot(x, self.victories_against_UCT, color='green', label='Victory')
        plt.plot(x, self.losses_against_UCT, color='red', label='Loss')
        plt.plot(x, self.draws_against_UCT, color='gray', label='Draw')
        plt.legend(loc="best")
        plt.title("Simulated Annealing - Games against UCT - " + str(self.n_uct_playouts) + " playouts")
        plt.xlabel('Iterations')
        plt.ylabel('Number of games')
        plt.savefig(filename + '_vs_glenn.png')

beta = 0.5
n_iterations = 50
n_games_glenn = 10
n_games_uct = 10
n_uct_playouts = 10
threshold = 0
tree_max_nodes = 100
init_temp = 1
d = 1
string_dataset = 'fulldata_sorted_string'
column_dataset = 'fulldata_sorted_column'
max_game_rounds = 500

SA = SimulatedAnnealing(
                        beta,
                        n_iterations,
                        n_games_glenn,
                        n_games_uct,
                        n_uct_playouts,
                        threshold,
                        init_temp,
                        d, 
                        tree_max_nodes,
                        string_dataset,
                        column_dataset,
                        max_game_rounds
                    )

SA.run()