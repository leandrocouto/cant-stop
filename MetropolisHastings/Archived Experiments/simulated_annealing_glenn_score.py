import sys
sys.path.insert(0,'..')
import math
import pickle
import time
import os
import re
import matplotlib.pyplot as plt

from MetropolisHastings.DSL import DSL
from Script import Script
from game import Game
from MetropolisHastings.parse_tree import ParseTree
from players.glenn_player import Glenn_Player
from players.vanilla_uct_player import Vanilla_UCT
from play_game_template import simplified_play_single_game
from play_game_template import play_single_game

class SimulatedAnnealingGlennScore:
    def __init__(self, beta, n_iterations, tree_max_nodes, d, init_temp, 
        n_games, n_games_glenn, n_games_uct, uct_playouts, eval_step, max_game_rounds):
        """
        Hybrid between selfplay and Simulated Annealing. Each procedure is 
        responsible for 50% of the score.
        """

        self.beta = beta
        self.n_iterations = n_iterations
        self.tree_max_nodes = tree_max_nodes
        self.d = d
        self.temperature = init_temp
        self.n_games = n_games
        self.n_games_glenn = n_games_glenn
        self.n_games_uct = n_games_uct
        self.uct_playouts = uct_playouts
        self.eval_step = eval_step
        self.max_game_rounds = max_game_rounds

        self.filename = 'glenn_SA_' + str(self.n_iterations) + 'ite_' + \
        str(self.tree_max_nodes) + 'tree_' + str(self.n_games) + 'selfplay_' + \
        str(self.n_games_glenn) + 'glenn' + str(self.n_games_uct) + 'uct'

        if not os.path.exists(self.filename):
            os.makedirs(self.filename)

        self.tree_string = ParseTree(DSL('S', True), self.tree_max_nodes)
        self.tree_column = ParseTree(DSL('S', False), self.tree_max_nodes)

        # For analysis - Games against Glenn
        self.victories_against_glenn = []
        self.losses_against_glenn = []
        self.draws_against_glenn = []

        # For analysis - Games against UCT
        self.victories_against_UCT = []
        self.losses_against_UCT = []
        self.draws_against_UCT = []


    def run(self):
        """ Main routine of the SA algorithm. """

        full_run = time.time()

        self.tree_string.build_tree(self.tree_string.root)
        self.tree_column.build_tree(self.tree_column.root)

        # Main loop
        for i in range(2, self.n_iterations + 2):
            start = time.time()
            # Make a copy of the tree for future mutation
            new_tree_string = pickle.loads(pickle.dumps(self.tree_string, -1))
            new_tree_column = pickle.loads(pickle.dumps(self.tree_column, -1))

            new_tree_string.mutate_tree()
            new_tree_column.mutate_tree()

            current_program_string = self.tree_string.generate_program()
            current_program_column = self.tree_column.generate_program()
            
            mutated_program_string = new_tree_string.generate_program()
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

            score_best, score_mutated  = self.calculate_score_function(
                                                        script_best_player, 
                                                        script_mutated_player
                                                        )
            # Instead of the classical SA that we divide the mutated score by
            # the current best program score (which we use the error rate), in
            # here we use best/mut because we are using the victory rate as
            # parameter for the score function.
            # Update score given the SA parameters
            score_best, score_mutated = self.update_score(score_best, score_mutated)

            # Accept program only if new score is higher.
            if score_mutated == 0:
                accept = 0
            else:
                accept = min(1, score_best/score_mutated)
            
            # Adjust the temperature accordingly.
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
                v_uct = None 
                l_uct = None 
                d_uct = None
                if len(self.victories_against_glenn) % self.eval_step == 0:
                    v_uct, l_uct, d_uct = self.validate_against_UCT(script_best_player)
                    self.victories_against_UCT.append(v_uct)
                    self.losses_against_UCT.append(l_uct)
                    self.draws_against_UCT.append(d_uct)
                elapsed_time_uct = time.time() - start_uct

                elapsed_time = time.time() - start

                # Save data file
                iteration_data = (
                                    v_glenn, l_glenn, d_glenn,
                                    v_uct, l_uct, d_uct,
                                    self.tree_string, self.tree_column
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
                    print('Iteration -', i, 
                        'New program accepted - V/L/D against Glenn = ', v_glenn, l_glenn, d_glenn, 
                        'V/L/D against UCT', self.uct_playouts, 'playouts = ', v_uct, l_uct, d_uct, 
                        file=f)
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

    def calculate_score_function(self, script_best_player, script_mutated_player):

        vic_cur, _, _ = self.validate_against_glenn(script_best_player)
        vic_mut, _, _ = self.validate_against_glenn(script_mutated_player)
        victory_rate_glenn_cur = vic_cur / self.n_games_glenn
        victory_rate_glenn_mut = vic_mut / self.n_games_glenn

        score_cur = math.exp(-self.beta * victory_rate_glenn_cur)
        score_mut = math.exp(-self.beta * victory_rate_glenn_mut)

        return score_cur, score_mut

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

    def validate_against_glenn(self, current_script):
        """ Validate current script against Glenn's heuristic player. """

        glenn = Glenn_Player()

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
        """ Validate current script against UCT. """

        victories = []
        losses = []
        draws = []

        for i in range(len(self.uct_playouts)):
            v = 0
            l = 0
            d = 0
            for j in range(self.n_games_uct):
                game = game = Game(2, 4, 6, [2,12], 2, 2)
                uct = Vanilla_UCT(c = 1, n_simulations = self.uct_playouts[i])
                if j%2 == 0:
                        who_won = play_single_game(
                                                    current_script, 
                                                    uct, 
                                                    game, 
                                                    self.max_game_rounds
                                                    )
                        if who_won == 1:
                            v += 1
                        elif who_won == 2:
                            l += 1
                        else:
                            d += 1
                else:
                    who_won = play_single_game(
                                                uct, 
                                                current_script, 
                                                game, 
                                                self.max_game_rounds
                                                )
                    if who_won == 2:
                        v += 1
                    elif who_won == 1:
                        l += 1
                    else:
                        d += 1
            
            victories.append(v)
            losses.append(l)
            draws.append(d)

        return victories, losses, draws


    def generate_report(self):
        
        dir_path = os.path.dirname(os.path.realpath(__file__)) + '/' + self.filename + '/' 
        filename = dir_path + self.filename
        x = list(range(len(self.victories_against_glenn)))

        plt.plot(x, self.victories_against_glenn, color='green', label='Victory')
        plt.plot(x, self.losses_against_glenn, color='red', label='Loss')
        plt.plot(x, self.draws_against_glenn, color='gray', label='Draw')
        plt.legend(loc="best")
        plt.title("Glenn Simulated Annealing - Games against Glenn")
        plt.xlabel('Iterations')
        plt.ylabel('Number of games')
        plt.savefig(filename + '_vs_glenn.png')

        plt.close()

        for i in range(len(self.uct_playouts)):
            victories = [vic[i] for vic in self.victories_against_UCT]  
            losses = [loss[i] for loss in self.losses_against_UCT]
            draws = [draw[i] for draw in self.draws_against_UCT]
            
            x = list(range(len(victories)))

            plt.plot(x, victories, color='green', label='Victory')
            plt.plot(x, losses, color='red', label='Loss')
            plt.plot(x, draws, color='gray', label='Draw')
            plt.legend(loc="best")
            plt.title("Glenn Simulated Annealing - Games against UCT - " + str(self.uct_playouts[i]) + " playouts")
            plt.xlabel('Iterations')
            plt.ylabel('Number of games')
            plt.savefig(filename + '_vs_UCT_' + str(self.uct_playouts[i]) +'.png')

            plt.close()

if __name__ == "__main__":
    beta = 0.5
    n_iterations = 10
    tree_max_nodes = 100
    d = 1
    init_temp = 1
    n_games = 100
    n_games_glenn = 100
    n_games_uct = 10
    uct_playouts = [2, 3, 4]
    eval_step = 1
    max_game_rounds = 500

    SA_glenn_score = SimulatedAnnealingGlennScore(
                                        beta,
                                        n_iterations,
                                        tree_max_nodes,
                                        d,
                                        init_temp,
                                        n_games,
                                        n_games_glenn,
                                        n_games_uct,
                                        uct_playouts,
                                        eval_step,
                                        max_game_rounds
                                    )

    SA_glenn_score.run()