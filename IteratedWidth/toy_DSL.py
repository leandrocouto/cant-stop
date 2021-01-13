class ToyDSL:
    """
    Implementation of a Domain Specific Language (DSL) for the Can't Stop
    domain.
    """
    def __init__(self):
        
        self.start = 'S'
        
        self._grammar = {}
       	
        self._grammar[self.start] = [r"\t\t\t statement"]

        self._grammar['statement']   = [
                                        r"statement \n\t\t\t statement",
                                        r"assign_expr \n\t\t\t",
                                        r"for iterable_for_variable in range(len(scores)): \n\t\t\t\t statement_1",
                                        r"return ret_expr \n\t\t\t"
                                        ]

        self._grammar['statement_1']   = [
                                        r"statement_1 \n\t\t\t\t statement_1",
                                        r"assign_expr \n\t\t\t\t",
                                        r"return ret_expr \n\t\t\t\t"
                                        ]

        self._grammar['assign_expr'] = [
                                        "variable = math_expr",
                                        "variable += math_expr",
                                        "variable -= math_expr",
                                        "variable *= math_expr"
                                        ]

        self._grammar['math_expr'] = [
                                        "math_expr OP math_term",
                                        "math_term"
                                        ]

        self._grammar['math_term'] = [
                                        "INTEGERS",
                                        "variable",
                                        "functions_num",
                                        ]

        self._grammar['variable'] = [
                                    "a",
                                    "b",
                                    ]

        self._grammar['iterable_for_variable'] = [
                                    "i",
        ]

        self._grammar['ret_expr'] = [
                                    'actions[ iterable_for_variable ]',
                                    'actions[ variable ]'
                                ]

        self._grammar['functions_num'] = [
                                'ToyDSL.get_player_total_advance(state)',
                                'ToyDSL.get_opponent_total_advance(state)',
                                ]

        self._grammar['INTEGERS'] = [str(i) for i in range(1, 3)] 
        self._grammar['OP'] = ['+', '-', '*']

        # Used in the parse tree to finish expanding hanging nodes
        self.finishable_nodes = [self.start, 'statement', 'statement_1', 'assign_expr', 
                                'math_expr', 'math_term', 'variable', 
                                'iterable_for_variable', 'functions_num', 'ret_expr',
                                'INTEGERS', 'OP']

        # Dictionary to "quickly" finish the tree.
        # Needed for the tree to not surpass the max node limit.
        self.quickly_finish = {
                                self.start : self._grammar[self.start],
                                'statement' : [r"assign_expr \n\t\t\t", r"return ret_expr \n\t\t\t"],
                                'statement_1' : [r"assign_expr \n\t\t\t\t", r"return ret_expr \n\t\t\t\t"],
                                'assign_expr' : self._grammar["assign_expr"],
                                'math_expr' : self._grammar["math_expr"],
                                'math_term' : self._grammar["math_term"],
                                'variable' :self._grammar['variable'],
                                'iterable_for_variable' :self._grammar['iterable_for_variable'],
                                'functions_num' :self._grammar['functions_num'],
                                'ret_expr' :self._grammar['ret_expr'],
                                'INTEGERS' :self._grammar['INTEGERS'],
                                'OP' :self._grammar['OP'],
                            }

    @staticmethod
    def get_player_total_advance(state):
        """ A score is the number of cells advanced in all columns. """

        counter = 0
        player = state.player_turn
        won = []
        # First look for columns already won and sum it accordingly
        for won_column in state.finished_columns:
            won.append(won_column[0])
            if won_column[1] == player:
                counter += len(state.board_game.board[won_column[0]]) + 1
        # Now sum for the remaining columns
        for column in range(state.column_range[0], state.column_range[1]+1):
            # Ignore columns alread won, they are already counted above
            if column in won:
                continue
            previously_conquered = -1
            neutral_position = -1
            list_of_cells = state.board_game.board[column]

            for i in range(len(list_of_cells)):
                if player in list_of_cells[i].markers:
                    previously_conquered = i
                if 0 in list_of_cells[i].markers:
                    neutral_position = i
            if neutral_position != -1:
                counter += neutral_position + 1
                for won_column in state.player_won_column:
                    if won_column[0] == column:
                        counter += 1
            elif previously_conquered != -1 and neutral_position == -1:
                counter += previously_conquered + 1
                for won_column in state.player_won_column:
                    if won_column[0] == column:
                        counter += len(list_of_cells) - previously_conquered
        
        return counter

    @staticmethod
    def get_opponent_total_advance(state):
        """ A score is the number of cells advanced in all columns. """

        counter = 0
        if state.player_turn == 1:
            player = 2
        else:
            player = 1
        won = []
        # First look for columns already won and sum it accordingly
        for won_column in state.finished_columns:
            won.append(won_column[0])
            if won_column[1] == player:
                counter += len(state.board_game.board[won_column[0]]) + 1
        # Now sum for the remaining columns
        for column in range(state.column_range[0], state.column_range[1]+1):
            # Ignore columns alread won, they are already counted above
            if column in won:
                continue
            previously_conquered = -1
            list_of_cells = state.board_game.board[column]

            for i in range(len(list_of_cells)):
                if player in list_of_cells[i].markers:
                    previously_conquered = i
            if previously_conquered != -1:
                counter += previously_conquered + 1
        return counter

    @staticmethod
    def will_player_win_after_n(state):
        """ 
        Return a boolean in regards to if the player will win the game or not 
        if they choose to stop playing the current round (i.e.: choose the 
        'n' action). 
        """
        clone_state = state.clone()
        clone_state.play('n')
        won_columns = 0
        for won_column in clone_state.finished_columns:
            if state.player_turn == won_column[1]:
                won_columns += 1
        #This means if the player stop playing now, they will win the game
        if won_columns == 3:
            return True
        else:
            return False

    @staticmethod
    def number_cells_advanced_this_round(state):
        """
        Return the number of positions advanced in this round for current
        player for all columns.
        """
        counter = 0
        for column in range(state.column_range[0], state.column_range[1]+1):
            counter += ToyDSL.number_cells_advanced_this_round_for_col(state, column)
        return counter

    @staticmethod
    def number_cells_advanced_this_round_for_col(state, column):
        """
        Return the number of positions advanced in this round for a given
        column by the player.
        """
        counter = 0
        previously_conquered = -1
        neutral_position = -1
        list_of_cells = state.board_game.board[column]

        for i in range(len(list_of_cells)):
            if state.player_turn in list_of_cells[i].markers:
                previously_conquered = i
            if 0 in list_of_cells[i].markers:
                neutral_position = i
        if previously_conquered == -1 and neutral_position != -1:
            counter += neutral_position + 1
            for won_column in state.player_won_column:
                if won_column[0] == column:
                    counter += 1
        elif previously_conquered != -1 and neutral_position != -1:
            counter += neutral_position - previously_conquered
            for won_column in state.player_won_column:
                if won_column[0] == column:
                    counter += 1
        elif previously_conquered != -1 and neutral_position == -1:
            for won_column in state.player_won_column:
                if won_column[0] == column:
                    counter += len(list_of_cells) - previously_conquered
        return counter

    @staticmethod
    def calculate_difficulty_score(state, odds, evens, highs, lows):
        """
        Add an integer to the current score given the peculiarities of the
        neutral marker positions on the board.
        """
        difficulty_score = 0

        neutral = [n[0] for n in state.neutral_positions]
        # If all neutral markers are in odd columns
        if all([x % 2 != 0 for x in neutral]):
            difficulty_score += odds
        # If all neutral markers are in even columns
        if all([x % 2 == 0 for x in neutral]):
            difficulty_score += evens
        # If all neutral markers are is "low" columns
        if all([x <= 7 for x in neutral]):
            difficulty_score += lows
        # If all neutral markers are is "high" columns
        if all([x >= 7 for x in neutral]):
            difficulty_score += highs

        return difficulty_score

    @staticmethod
    def are_there_available_columns_to_play(state):
        """
        Return a booleanin regards to if there available columns for the player
        to choose. That is, if the does not yet have all three neutral markers
        used AND there are available columns that are not finished/won yet.
        """
        available_columns = ToyDSL.get_available_columns(state)
        return state.n_neutral_markers != 3 and len(available_columns) > 0

    @staticmethod
    def get_available_columns(state):
        """ Return a list of all available columns. """

        # List containing all columns, remove from it the columns that are
        # available given the current board
        available_columns = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        for neutral in state.neutral_positions:
            available_columns.remove(neutral[0])
        for finished in state.finished_columns:
            if finished[0] in available_columns:
                available_columns.remove(finished[0])

        return available_columns

    @staticmethod
    def calculate_score(state, progress_value):
        score = 0
        neutrals = [col[0] for col in state.neutral_positions]
        for col in neutrals:
            advance = ToyDSL.number_cells_advanced_this_round_for_col(state, col)
            # +1 because whenever a neutral marker is used, the weight of that
            # column is summed
            # Interporlated formula to find the array index given the column
            # y = 5-|x-7|
            score += (advance + 1) * progress_value[5 - abs(col - 7)]
        return score
