# Database
import datetime
import sqlite3
import os.path



class SqlConnector():

    def __init__(self):
        if not os.path.isfile("score_database.db"):
            self.create_database()
            
        self.con = sqlite3.connect("score_database.db",
                                   detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.cur = self.con.cursor()
        
    def create_database(self):
        # Probably a more efficient way of using the connection/cursor
        con = sqlite3.connect("score_database.db",
                                   detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cur = con.cursor()
                
        cur.execute("CREATE TABLE score_log(Date TIMESTAMP, GameID INTEGER, TimePerGuess INTEGER, TotalTrials INTEGER, TrialNumber INTEGER, TargetString VARCHAR(3), TargetLowHigh VARCHAR(4), TargetNote VARCHAR(2), PlayedNote VARCHAR(2), IsCorrect BOOLEAN)")
        
        cur.execute("CREATE TABLE final_score_log(Date TIMESTAMP, GameID INTEGER, TimerPerGuess INTEGER, TotalTrials INTEGER, TotalCorrect INTEGER)")
        
        cur.close()
        con.close()
        
        # Checking that database exists using sqlite_master
        #res = cur.execute("SELECT name FROM sqlite_master")
        #res.fetchone()
        
    def get_current_game_id(self):
        latest_id = self.cur.execute("SELECT MAX(GameID) FROM score_log").fetchone()[0]
        if latest_id is not None:
            curr_id = latest_id + 1
        else:
            curr_id = 1
        return curr_id

    def insert_trial(self, game_id, time_per_guess, trials, trial_number, target_string, target_lowhigh, target_note, played_note, is_correct):
        insertQuery = "INSERT INTO score_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"

        self.cur.execute(insertQuery,
                    (datetime.datetime.now(),
                     game_id,
                     time_per_guess,
                     trials,
                     trial_number,
                     target_string,
                     target_lowhigh,
                     target_note,
                     played_note,
                     is_correct))

        self.con.commit()

    def insert_final_score(self, game_id, time_per_guess, trials, num_correct):
        insertQuery = "INSERT INTO final_score_log VALUES (?, ?, ?, ?, ?);"

        self.cur.execute(insertQuery,
                    (datetime.datetime.now(),
                     game_id,
                     time_per_guess,
                     trials,
                     num_correct))

        self.con.commit()


    def get_best_score(self, time_per_guess, trials, num_correct):
        previous_best = self.cur.execute(f"SELECT MAX(TotalCorrect) FROM final_score_log\
                    WHERE TimerPerGuess = {time_per_guess} AND TotalTrials = {trials}").fetchall()[0][0]



        if previous_best is None:
            return "New high score!"
        elif num_correct > previous_best:
            return "New high score!"
        elif num_correct == previous_best:
            return "Matched previous best."
        else:
            return f"Previous best: {previous_best}/{trials}"

    def get_top_5_incorrect(self):
        most_incorrect = self.cur.execute("SELECT TargetString, TargetLowHigh, TargetNote, COUNT(*) AS total_incorrect FROM\
                                    score_log\
                                    WHERE IsCorrect = 0\
                                    GROUP BY TargetString, TargetLowHigh, TargetNote\
                                    ORDER BY total_incorrect DESC\
                                    LIMIT 5;"
                                     ).fetchall()

        joined_incorrect = []
        for i in most_incorrect:
            joined_incorrect.append("".join(str(i[0:3])).replace("'", "").replace(
                ",", "").replace("(", "").replace(")", "") + f": {str(i[3])} incorrect")

        top_5_incorrect = '\n'.join(joined_incorrect)

        print(f"Top 5 incorrect notes:\n{top_5_incorrect}")
        
    def close_con(self):
        self.cur.close()
        self.con.close()
        

