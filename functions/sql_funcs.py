# Database
import datetime
import os.path
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt

DATABASE_PATH = Path(__file__).resolve().parents[1] / "databases" / "score_database.db"


def _connect():
    # Centralized sqlite connection settings used by all DB operations.
    return sqlite3.connect(
        DATABASE_PATH,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    )


def create_database():
    with _connect() as con:
        cur = con.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS score_log("
            "Date TIMESTAMP, GameID INTEGER, TimePerGuess INTEGER, TotalTrials INTEGER, "
            "TrialNumber INTEGER, TargetString VARCHAR(3), TargetLowHigh VARCHAR(4), "
            "TargetNote VARCHAR(2), PlayedNote VARCHAR(8), IsCorrect BOOLEAN)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS final_score_log("
            "Date TIMESTAMP, GameID INTEGER, TimePerGuess INTEGER, "
            "TotalTrials INTEGER, TotalCorrect INTEGER)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_score_log_game "
            "ON score_log(GameID, TrialNumber)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_final_score_combo "
            "ON final_score_log(TotalTrials, TimePerGuess, TotalCorrect)"
        )


def get_current_game_id():
    with _connect() as con:
        cur = con.cursor()
        latest_id = cur.execute("SELECT MAX(GameID) FROM score_log").fetchone()[0]
    return latest_id + 1 if latest_id is not None else 1


def insert_trial(
    game_id,
    time_per_guess,
    trials,
    trial_number,
    target_string,
    target_lowhigh,
    target_note,
    played_note,
    is_correct,
):
    insert_query = "INSERT INTO score_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
    with _connect() as con:
        con.execute(
            insert_query,
            (
                datetime.datetime.now(),
                game_id,
                time_per_guess,
                trials,
                trial_number,
                target_string,
                target_lowhigh,
                target_note,
                played_note,
                is_correct,
            ),
        )


def insert_trials_bulk(trials_to_insert):
    # Batch write trial rows to reduce per-trial transaction overhead.
    insert_query = "INSERT INTO score_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
    with _connect() as con:
        con.executemany(insert_query, trials_to_insert)


def insert_final_score(game_id, time_per_guess, trials, num_correct):
    insert_query = "INSERT INTO final_score_log VALUES (?, ?, ?, ?, ?);"
    with _connect() as con:
        con.execute(
            insert_query,
            (
                datetime.datetime.now(),
                game_id,
                time_per_guess,
                trials,
                num_correct,
            ),
        )


def get_best_score(time_per_guess, trials, num_correct):
    with _connect() as con:
        cur = con.cursor()
        previous_best = cur.execute(
            "SELECT MAX(TotalCorrect) FROM final_score_log "
            "WHERE TimePerGuess = ? AND TotalTrials = ?",
            (time_per_guess, trials),
        ).fetchone()[0]

    if previous_best is None:
        return "New high score!"
    if num_correct > previous_best:
        return "New high score!"
    if num_correct == previous_best:
        return "Matched previous best."
    return f"Previous best: {previous_best}/{trials}"


def get_top_incorrect(top_n=None):
    base_query = (
        "SELECT TargetString, TargetLowHigh, TargetNote, COUNT(*) AS total_incorrect "
        "FROM score_log "
        "WHERE IsCorrect = 0 "
        "GROUP BY TargetString, TargetLowHigh, TargetNote "
        "ORDER BY total_incorrect DESC"
    )
    params = ()
    if top_n is not None:
        base_query += " LIMIT ?"
        params = (int(top_n),)

    with _connect() as con:
        cur = con.cursor()
        return cur.execute(base_query, params).fetchall()


def create_incorrect_bar_chart(top_n=None):
    # Build a chart-friendly view with an explicit empty-state figure.
    incorrect_notes = get_top_incorrect(top_n)
    fig, ax = plt.subplots(figsize=(16, 9))

    if not incorrect_notes:
        ax.text(0.5, 0.5, "No incorrect notes logged yet.", ha="center", va="center")
        ax.set_axis_off()
        return fig

    incorrect_notes_dict = {
        f"{x[0]} {x[1]} {x[2]}": int(x[3])
        for x in incorrect_notes
    }

    notes = list(incorrect_notes_dict.keys())
    values = list(incorrect_notes_dict.values())

    ax.barh(notes, values, align="center")
    ax.invert_yaxis()
    ax.set_xticks(range(0, max(values) + 1))
    plt.margins(y=0.01)
    ax.set_xlabel("# incorrect")
    ax.set_ylabel("Notes")
    return fig


def get_trial_time_combos():
    with _connect() as con:
        cur = con.cursor()
        return cur.execute(
            "SELECT DISTINCT TotalTrials AS DT, TimePerGuess AS TPG "
            "FROM final_score_log "
            "ORDER BY DT DESC, TPG ASC"
        ).fetchall()


def get_highscores(trials, time_per_guess):
    with _connect() as con:
        cur = con.cursor()
        return cur.execute(
            "SELECT * FROM final_score_log "
            "WHERE TimePerGuess = ? AND TotalTrials = ? "
            "ORDER BY TotalCorrect DESC, GameID",
            (time_per_guess, trials),
        ).fetchall()


if not os.path.isfile(DATABASE_PATH):
    create_database()
