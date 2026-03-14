"""
Persistent stats for Tetris and Dr. Mario.

Uses the Badgeware State API to save/load between sessions.
"""


class Stats:
    def __init__(self):
        self.high_score = 0
        self.dr_high = 0
        self.dr_best_level = 0
        self.total_lines = 0
        self.total_games = 0
        self.total_time_ms = 0
        self.best_combo = 0
        self.best_b2b = 0
        self.session_combo = 0
        self.session_b2b = 0
        self.session_start = 0
        self.theme_name = "classic"

    def load(self):
        """Load stats from persistent storage."""
        s = {
            "high_score": 0, "dr_high": 0, "dr_best_level": 0,
            "total_lines": 0, "total_games": 0, "total_time_ms": 0,
            "best_combo": 0, "best_b2b": 0, "theme_name": "classic",
        }
        State.load("tetris", s)
        self.high_score = s.get("high_score", 0)
        self.dr_high = s.get("dr_high", 0)
        self.dr_best_level = s.get("dr_best_level", 0)
        self.total_lines = s.get("total_lines", 0)
        self.total_games = s.get("total_games", 0)
        self.total_time_ms = s.get("total_time_ms", 0)
        self.best_combo = s.get("best_combo", 0)
        self.best_b2b = s.get("best_b2b", 0)
        self.theme_name = s.get("theme_name", "classic")

    def save(self):
        """Persist stats to storage."""
        State.save("tetris", {
            "high_score": self.high_score, "dr_high": self.dr_high,
            "dr_best_level": self.dr_best_level,
            "total_lines": self.total_lines, "total_games": self.total_games,
            "total_time_ms": self.total_time_ms,
            "best_combo": self.best_combo, "best_b2b": self.best_b2b,
            "theme_name": self.theme_name,
        })

    def start_game(self):
        """Called at the start of every game."""
        self.session_combo = 0
        self.session_b2b = 0
        self.session_start = badge.ticks
        self.total_games += 1

    def end_tetris(self, score, lines):
        """Record end of a Tetris game."""
        self.total_time_ms += badge.ticks - self.session_start
        self.total_lines += lines
        if score > self.high_score:
            self.high_score = score
        if self.session_combo > self.best_combo:
            self.best_combo = self.session_combo
        if self.session_b2b > self.best_b2b:
            self.best_b2b = self.session_b2b
        self.save()

    def end_dr(self, score, level):
        """Record end of a Dr. Mario game."""
        self.total_time_ms += badge.ticks - self.session_start
        if score > self.dr_high:
            self.dr_high = score
        if level > self.dr_best_level:
            self.dr_best_level = level
        self.save()

    def play_time_str(self):
        """Format total play time as a human-readable string."""
        s = self.total_time_ms // 1000
        if s < 60:
            return "{}s".format(s)
        m = s // 60
        s = s % 60
        if m < 60:
            return "{}m{}s".format(m, s)
        return "{}h{}m".format(m // 60, m % 60)
