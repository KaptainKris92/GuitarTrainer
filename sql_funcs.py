# Database
import datetime
import sqlite3
import os.path
#import numpy as np
import matplotlib.pyplot as plt

def create_database():
    # Probably a more efficient way of using the connection/cursor
    con = sqlite3.connect("score_database.db",
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()

    cur.execute("CREATE TABLE score_log(Date TIMESTAMP, GameID INTEGER, TimePerGuess INTEGER, TotalTrials INTEGER, TrialNumber INTEGER, TargetString VARCHAR(3), TargetLowHigh VARCHAR(4), TargetNote VARCHAR(2), PlayedNote VARCHAR(2), IsCorrect BOOLEAN)")

    cur.execute("CREATE TABLE final_score_log(Date TIMESTAMP, GameID INTEGER, TimePerGuess INTEGER, TotalTrials INTEGER, TotalCorrect INTEGER)")

    cur.close()
    con.close()

    # Checking that database exists using sqlite_master
    # res = cur.execute("SELECT name FROM sqlite_master")
    # res.fetchone()


def get_current_game_id():
    con = sqlite3.connect("score_database.db",
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()

    latest_id = cur.execute("SELECT MAX(GameID) FROM score_log").fetchone()[0]
    if latest_id is not None:
        curr_id = latest_id + 1
    else:
        curr_id = 1
    return curr_id


def insert_trial(game_id, time_per_guess, trials, trial_number, target_string, target_lowhigh, target_note, played_note, is_correct):

    insertQuery = "INSERT INTO score_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"

    con = sqlite3.connect("score_database.db",
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()

    cur.execute(insertQuery,
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

    con.commit()
    cur.close()
    con.close()


def insert_final_score(game_id, time_per_guess, trials, num_correct):
    insertQuery = "INSERT INTO final_score_log VALUES (?, ?, ?, ?, ?);"

    con = sqlite3.connect("score_database.db",
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()

    cur.execute(insertQuery,
                (datetime.datetime.now(),
                 game_id,
                 time_per_guess,
                 trials,
                 num_correct))

    con.commit()
    cur.close()
    con.close()


def get_best_score(time_per_guess, trials, num_correct):
    con = sqlite3.connect("score_database.db",
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

    cur = con.cursor()

    previous_best = cur.execute(f"SELECT MAX(TotalCorrect) FROM final_score_log\
                WHERE TimePerGuess = {time_per_guess} AND TotalTrials = {trials}").fetchall()[0][0]

    if previous_best is None:
        return "New high score!"
    elif num_correct > previous_best:
        return "New high score!"
    elif num_correct == previous_best:
        return "Matched previous best."
    else:
        return f"Previous best: {previous_best}/{trials}"


def get_top_incorrect(top_n = None):
    con = sqlite3.connect("score_database.db",
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    
    if top_n is None:
        limit_n = ""
    else:
        limit_n = f"LIMIT {top_n}"

    most_incorrect = cur.execute(f"SELECT TargetString, TargetLowHigh, TargetNote, COUNT(*) AS total_incorrect FROM\
                                score_log\
                                WHERE IsCorrect = 0\
                                GROUP BY TargetString, TargetLowHigh, TargetNote\
                                ORDER BY total_incorrect DESC\
                                {limit_n};"
                                 ).fetchall()

    joined_incorrect = []
    for i in most_incorrect:
        joined_incorrect.append("".join(str(i[0:3])).replace("'", "").replace(
            ",", "").replace("(", "").replace(")", "") + f": {str(i[3])} incorrect")

    top_incorrect = '\n'.join(joined_incorrect)

    return most_incorrect    
    print(f"Top {top_n} incorrect notes:\n{top_incorrect}")
    
def create_incorrect_bar_chart(top_n = None):
    incorrect_notes = get_top_incorrect(top_n)
        
    incorrect_notes_dict = {str(x[0:3]).replace("('", "").replace(")","").replace("'","").replace(",",""): int(x[3]) for x in incorrect_notes}
    
    notes = list(incorrect_notes_dict.keys())
    values = list(incorrect_notes_dict.values())
    
    fig, ax = plt.subplots(figsize=(16,9))
    
    ax.barh(notes, values, align='center')
    
    # Show top values
    ax.invert_yaxis()
    
    plt.xticks(range(0, max(values)))
    plt.margins(y = 0.01)
    
    ax.set_xlabel("# incorrect")
    ax.set_ylabel("Notes")

    return fig
      

def get_trial_time_combos():
    con = sqlite3.connect("score_database.db",
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()

    trial_time_combos = cur.execute("SELECT DISTINCT TotalTrials AS DT, TimePerGuess AS TPG\
                                    FROM final_score_log\
                                        ORDER BY DT DESC, TPG ASC"
                                    ).fetchall()
    return trial_time_combos

def get_highscores(trials, time_per_guess):
    con = sqlite3.connect("score_database.db",
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()

    highscores = cur.execute(f"SELECT * FROM final_score_log\
                                    WHERE TimePerGuess = {time_per_guess}\
                                        AND TotalTrials = {trials}\
                                            ORDER BY TotalCorrect DESC, GameID"
                                            ).fetchall()    
    return highscores
    



if not os.path.isfile("score_database.db"):
    create_database()
