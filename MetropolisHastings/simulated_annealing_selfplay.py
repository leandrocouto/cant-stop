import math
import sys
import pickle
import time
import os
import matplotlib.pyplot as plt
import random
sys.path.insert(0,'..')
from MetropolisHastings.parse_tree import ParseTree
from MetropolisHastings.DSL import DSL
from game import Game
from sketch import Sketch
from algorithm import Algorithm
from play_game_template import simplified_play_single_game
from play_game_template import play_single_game
from play_game_template import play_solitaire_single_game

class SimulatedAnnealingSelfplay(Algorithm):
    """
    Simulated Annealing but instead of keeping a score on how many actions this
    algorithm got it correctly (when compared to an oracle), the score is now
    computed on how many victories the mutated get against the current program.
    The mutated program is accepted if it gets more victories than the current
    program playing against itself.
    """
    def __init__(self, algo_id, n_iterations, n_SA_iterations, 
        tree_max_nodes, d, init_temp, n_games_evaluate, n_games_glenn, 
        n_games_uct, n_games_solitaire, uct_playouts, eval_step, 
        max_game_rounds, iteration_run, yes_no_dsl, column_dsl, reg):
        """
        Metropolis Hastings with temperature schedule. This allows the 
        algorithm to explore more the space search.
        - d is a constant for the temperature schedule.
        - init_temp is the temperature used for the first iteration. Following
          temperatures are calculated following self.temperature_schedule().
        - n_games is the number of games played in selfplay evaluation.
        - n_games_glenn is the number of games played against Glenn's heuristic.
        - max_game_rounds is the number of rounds necessary in a game to
        consider it a draw. This is necessary because Can't Stop games can
        theoretically last forever.
        """

        self.algo_id = algo_id
        self.n_SA_iterations = n_SA_iterations
        self.d = d
        self.init_temp = init_temp
        self.n_games_evaluate = n_games_evaluate
        self.eval_step = eval_step
        self.iteration_run = iteration_run

        super().__init__(tree_max_nodes, n_iterations, n_games_glenn, 
                            n_games_uct, n_games_solitaire, uct_playouts,
                            max_game_rounds, yes_no_dsl, column_dsl, reg
                        )

        self.filename = str(self.algo_id) + '_' + \
                        str(self.n_iterations) + 'ite_' + \
                        str(self.n_SA_iterations) + 'SAite_' + \
                        str(self.n_games_evaluate) + 'eval_' + \
                        str(self.n_games_glenn) + 'glenn_' + \
                        str(self.n_games_uct) + 'uct_' + \
                        str(self.n_games_solitaire) + 'solitaire_' + \
                        str(self.iteration_run) + 'run'

        if not os.path.exists(self.filename):
            os.makedirs(self.filename)

    def run(self):

        full_run = time.time()
        p_tree_string = ParseTree(self.yes_no_dsl, self.tree_max_nodes)
        p_tree_column = ParseTree(self.column_dsl, self.tree_max_nodes)

        p_tree_string.build_tree(p_tree_string.root)
        p_tree_column.build_tree(p_tree_column.root)

        p_program_string = p_tree_string.generate_program()
        p_program_column = p_tree_column.generate_program()

        p = self.generate_player(p_program_string, p_program_column, 'p')

        for i in range(self.n_iterations):
            start = time.time()
            br_tree_string, br_tree_column, br_p = self.simulated_annealing(
                                                    p_tree_string,
                                                    p_tree_column,
                                                    p)

            self.games_played += self.n_SA_iterations * self.n_games_evaluate
            self.games_played_all.append(self.games_played)

            elapsed_time = time.time() - start
            
            victories, losses, draws = self.evaluate(br_p, p)

            # if br_p is better, keep it
            if victories > losses:
                p_tree_string = br_tree_string
                p_tree_column = br_tree_column
                p = br_p
                self.victories.append(victories)
                self.losses.append(losses)
                self.draws.append(draws)

                self.games_played_successful.append(self.games_played)

                # Validade against Glenn's heuristic
                start_glenn = time.time()
                v_glenn, l_glenn, d_glenn = self.validate_against_glenn(p)
                self.victories_against_glenn.append(v_glenn)
                self.losses_against_glenn.append(l_glenn)
                self.draws_against_glenn.append(d_glenn)
                elapsed_time_glenn = time.time() - start_glenn

                # Validade against UCT
                start_uct = time.time()
                v_uct = None 
                l_uct = None 
                d_uct = None
                if len(self.victories_against_glenn) % self.eval_step == 0:
                    self.games_played_uct.append(self.games_played)
                    v_uct, l_uct, d_uct = self.validate_against_UCT(p)
                    self.victories_against_UCT.append(v_uct)
                    self.losses_against_UCT.append(l_uct)
                    self.draws_against_UCT.append(d_uct)
                elapsed_time_uct = time.time() - start_uct

                # Validate with Solitaire
                start_solitaire = time.time()
                avg_solitaire, std_solitaire = self.validate_solitaire(p)
                self.avg_rounds_solitaire.append(avg_solitaire)
                self.std_rounds_solitaire.append(std_solitaire)
                elapsed_time_solitaire = time.time() - start_solitaire

                # Save data file
                iteration_data = (
                                    self.victories,
                                    self.losses,
                                    self.draws,
                                    self.victories_against_glenn,
                                    self.losses_against_glenn,
                                    self.draws_against_glenn,
                                    self.victories_against_UCT,
                                    self.losses_against_UCT,
                                    self.draws_against_UCT,
                                    self.avg_rounds_solitaire,
                                    self.std_rounds_solitaire,
                                    self.games_played,
                                    self.games_played_successful,
                                    self.games_played_all,
                                    self.games_played_uct,
                                    p_tree_string, p_tree_column
                                )
                folder = self.filename + '/data/' 
                if not os.path.exists(folder):
                    os.makedirs(folder)
                with open(folder + 'datafile_iteration_' + str(i) , 'wb') as file:
                    pickle.dump(iteration_data, file)
                # Save current script
                dir_path = os.path.dirname(os.path.realpath(__file__)) + '/' + self.filename + '/data/' 
                script = Sketch(
                                p_tree_string.generate_program(), 
                                p_tree_column.generate_program(), 
                                self.n_iterations, 
                                self.tree_max_nodes
                            )      
                script.save_file_custom(dir_path, self.filename + '_iteration_' + str(i))

                # Generate the graphs with current data
                self.generate_report()

                with open(self.filename + '/' + 'log_' + self.filename + '.txt', 'a') as f:
                    print('Iteration -', i, 'New program accepted - ', 
                        'V/L/D new script vs old = ', victories, losses, draws, 
                        'V/L/D against Glenn = ', v_glenn, l_glenn, d_glenn, 
                        'V/L/D against UCT', self.uct_playouts, 'playouts = ', v_uct, l_uct, d_uct, 
                        'Avg and std in Solitaire = ', avg_solitaire, std_solitaire, 
                        'Games played = ', self.games_played,
                        file=f)
                    print('Iteration -', i, 'SA elapsed time = ', elapsed_time,
                        'Glenn elapsed time = ', elapsed_time_glenn, 
                        'UCT elapsed time = ', elapsed_time_uct, 
                        'Solitaire elapsed time = ', elapsed_time_solitaire,
                        'Total elapsed time = ', elapsed_time + elapsed_time_glenn + elapsed_time_uct + elapsed_time_solitaire, file=f)

            # The new script was not better, ignore this iteration
            else:
                with open(self.filename + '/' + 'log_' + self.filename + '.txt', 'a') as f:
                    print('Iteration -', i, '- Elapsed time: ', elapsed_time, 'Games played = ', self.games_played, file=f)

        # Save the best script
        dir_path = os.path.dirname(os.path.realpath(__file__)) + '/' + self.filename + '/'
        script = Sketch(
                        p_program_string, 
                        p_program_column, 
                        self.n_iterations, 
                        self.tree_max_nodes
                    )      
        script.save_file_custom(dir_path, self.filename + '_best_script')

        full_run_elapsed_time = time.time() - full_run
        with open(self.filename + '/' + 'log_' + self.filename + '.txt', 'a') as f:
            print('Full program elapsed time = ', full_run_elapsed_time, file=f)

        return p_program_string, p_program_column, p, p_tree_string, p_tree_column

    def simulated_annealing(self, p_tree_string, p_tree_column, p):
        
        # Builds an initially random program (curr)
        curr_tree_string = ParseTree(self.yes_no_dsl, self.tree_max_nodes)
        curr_tree_column = ParseTree(self.column_dsl, self.tree_max_nodes)
        curr_tree_string.build_tree(curr_tree_string.root)
        curr_tree_column.build_tree(curr_tree_column.root)
        curr_p_string = curr_tree_string.generate_program()
        curr_p_column = curr_tree_column.generate_program()
        curr_p = self.generate_player(curr_p_string, curr_p_column, 'SA_curr')

        # Evaluates this program against p.
        victories, losses, draws = self.evaluate(curr_p, p)
        score = victories
        best_score = score
        # Initially assumes that p is the best script of all
        best_solution_string_tree = p_tree_string
        best_solution_column_tree = p_tree_column
        best_solution = p

        curr_temp = self.init_temp

        for i in range(2, self.n_SA_iterations + 2):
            start = time.time()
            # Make a copy of curr_p
            mutated_tree_string = pickle.loads(pickle.dumps(curr_tree_string, -1))
            mutated_tree_column = pickle.loads(pickle.dumps(curr_tree_column, -1))
            # Mutate it
            mutated_tree_string.mutate_tree()
            mutated_tree_column.mutate_tree()
            # Get the programs for each type of actions
            mutated_curr_p_string = mutated_tree_string.generate_program()
            mutated_curr_p_column = mutated_tree_column.generate_program()
            # Build the script
            mutated_curr_p = self.generate_player(mutated_curr_p_string, mutated_curr_p_column, 'mutated_curr_' + str(i))
            # Evaluates the mutated program against p
            victories_mut, losses_mut, draws_mut = self.evaluate(mutated_curr_p, p)
            new_score = victories_mut
            # if mutated_curr_p is better than p, then accept it
            if new_score > score:
                #print('new score bateu score')
                score = new_score
                # Copy the trees
                curr_tree_string = mutated_tree_string 
                curr_tree_column = mutated_tree_column
                # Copy the programs
                curr_p_string = mutated_curr_p_string
                curr_p_column = mutated_curr_p_column
                # Copy the script
                curr_p = mutated_curr_p
                # Keep track of the best solution
                if new_score > best_score:
                    best_score = new_score
                    # Copy the trees
                    best_solution_string_tree = mutated_tree_string
                    best_solution_column_tree = mutated_tree_column
                    # Copy the script
                    best_solution = mutated_curr_p
            # even if not better, there is a chance to accept it
            else:
                delta = math.exp(-(score-new_score)/curr_temp)
                if(random.random() < delta):
                    score = new_score
                    # Copy the trees
                    curr_tree_string = mutated_tree_string 
                    curr_tree_column = mutated_tree_column
                    # Copy the programs
                    curr_p_string = mutated_curr_p_string
                    curr_p_column = mutated_curr_p_column
                    # Copy the script
                    curr_p = mutated_curr_p
            # update temperature according to schedule
            curr_temp = self.temperature_schedule(i)
            elapsed_time = time.time() - start
        return best_solution_string_tree, best_solution_column_tree, best_solution

    def accept_new_program(self, victories, losses, new_tree_string, new_tree_column):
        # If regularization is used
        if self.reg:
            pass
        else:
            pass

    def evaluate(self, first_player, second_player):
        victories = 0
        losses = 0
        draws = 0
        for i in range(self.n_games_evaluate):
            game = Game(2, 4, 6, [2,12], 2, 2)
            if i%2 == 0:
                    who_won = simplified_play_single_game(
                                                        first_player, 
                                                        second_player, 
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
                                                    second_player, 
                                                    first_player, 
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

    def temperature_schedule(self, iteration):
        """ Calculate the next temperature used for the score calculation. """

        return self.d/math.log(iteration)

    def generate_report(self):
        
        dir_path = os.path.dirname(os.path.realpath(__file__)) + '/' + self.filename + '/' 
        filename = dir_path + self.filename

        axes = plt.gca()
        axes.set_ylim([0, 1])
        y_victories = [vic / self.n_games_evaluate for vic in self.victories]
        y_losses = [loss / self.n_games_evaluate for loss in self.losses]
        plt.plot(self.games_played_successful, y_victories, color='green', label='Victory')
        plt.plot(self.games_played_successful, y_losses, color='red', label='Loss')
        plt.legend(loc="best")
        plt.title(str(self.algo_id) + " - Generated script against previous script")
        plt.xlabel('Games played')
        plt.ylabel('Rate - ' + str(self.n_games_evaluate) + ' games')
        plt.savefig(filename + '_vs_previous_script.png')
        plt.close()

        axes = plt.gca()
        axes.set_ylim([0, 1])
        y_victories = [vic / self.n_games_glenn for vic in self.victories_against_glenn]
        plt.plot(self.games_played_successful, y_victories, color='green')
        plt.title(str(self.algo_id) + " - Games against Glenn")
        plt.xlabel('Games played')
        plt.ylabel('Victory rate - ' + str(self.n_games_glenn) + ' games')
        plt.savefig(filename + '_vs_glenn.png')
        plt.close()

        axes = plt.gca()
        axes.set_ylim([0, 1])
        for i in range(len(self.uct_playouts)):
            victories = [vic[i] / self.n_games_uct for vic in self.victories_against_UCT]  
            plt.plot(self.games_played_uct, victories, label=str(self.uct_playouts[i]) + " playouts")
        plt.legend(loc="best")
        plt.title(str(self.algo_id) + " - Games against UCT")
        plt.xlabel('Games played')
        plt.ylabel('Victory rate - ' + str(self.n_games_uct) + ' games')
        plt.savefig(filename + '_vs_UCT.png')
        plt.close()

        plt.errorbar(self.games_played_successful, self.avg_rounds_solitaire, yerr=self.std_rounds_solitaire, fmt='-')
        plt.title(str(self.algo_id) + " - Average rounds in Solitaire Can't Stop")
        plt.xlabel('Games played')
        plt.ylabel('Number of rounds')
        plt.savefig(filename + '_solitaire.png')
        plt.close()

if __name__ == "__main__":
    algo_id = 'SASP'
    n_iterations = 20
    n_SA_iterations = 10
    tree_max_nodes = 100
    d = 1
    init_temp = 1
    n_games_evaluate = 100
    n_games_glenn = 1000
    n_games_uct = 5
    n_games_solitaire = 3
    uct_playouts = [2, 3, 4]
    eval_step = 1
    max_game_rounds = 500
    iteration_run = 0
    reg = False

    yes_no_dsl = DSL('S')
    yes_no_dsl.set_type_action(True)
    column_dsl = DSL('S')
    column_dsl.set_type_action(False)

    selfplay_SA = SimulatedAnnealingSelfplay(
                                        algo_id,
                                        n_iterations,
                                        n_SA_iterations,
                                        tree_max_nodes,
                                        d,
                                        init_temp,
                                        n_games_evaluate,
                                        n_games_glenn,
                                        n_games_uct,
                                        n_games_solitaire,
                                        uct_playouts,
                                        eval_step,
                                        max_game_rounds,
                                        iteration_run,
                                        yes_no_dsl,
                                        column_dsl,
                                        reg
                                    )
    selfplay_SA.run()
