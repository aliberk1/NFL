"""Presentation rules for observed player data."""

from collections import defaultdict


TEAM_NAMES = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LA": "Los Angeles Rams", "LAR": "Los Angeles Rams",
    "LAC": "Los Angeles Chargers", "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings", "NE": "New England Patriots", "NO": "New Orleans Saints",
    "NYG": "New York Giants", "NYJ": "New York Jets", "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers", "SEA": "Seattle Seahawks", "SF": "San Francisco 49ers",
    "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}

POSITION_NAMES = {
    "C": "Hücum merkezi", "G": "Hücum guardı", "T": "Hücum tackle'ı",
    "WR": "Pas yakalayıcı", "TE": "Tight end", "RB": "Koşu oyuncusu",
    "FB": "Fullback", "QB": "Oyun kurucu", "DE": "Savunma ucu",
    "DT": "Savunma tackle'ı", "NT": "Nose tackle", "OLB": "Dış linebacker",
    "ILB": "İç linebacker", "MLB": "Orta linebacker", "CB": "Köşe savunmacısı",
    "DB": "Arka alan savunmacısı", "FS": "Serbest safety",
    "SS": "Güçlü safety",
}

PLAYER_FIELDS = [
    ("draft_year", "Draft yılı", ""), ("birth_date", "Doğum tarihi", ""),
    ("college_name", "Üniversite", ""), ("college_conference", "Konferans", ""),
    ("draft_round", "Draft turu", ""), ("draft_pick_within_round", "Turdaki seçim", ""),
    ("draft_overall_pick", "Genel seçim sırası", ""),
]
COMBINE_FIELDS = [
    ("combine_position", "Combine pozisyonu", ""), ("combine_height", "Boy", "inç"),
    ("combine_weight", "Ağırlık", "lb"), ("hand_size", "El ölçüsü", "inç"),
    ("arm_length", "Kol uzunluğu", "inç"), ("wing_span", "Kol açıklığı", "inç"),
    ("ten_yd_split", "10 yard süresi", "sn"), ("forty", "40 yard süresi", "sn"),
    ("vertical", "Dikey sıçrama", "inç"), ("broad_jump", "Uzun atlama", "inç"),
    ("three_cone", "3 koni çeviklik testi", "sn"),
    ("short_shuttle", "Kısa mekik koşusu", "sn"),
    ("bench_reps", "Bench press", "tekrar"),
    ("ngs_athleticism_score", "Atletizm puanı", "puan"),
    ("ngs_college_production_score", "Kolej üretim puanı", "puan"),
    ("ngs_final_score", "Genel NGS puanı", "puan"),
]
CAREER_FIELDS = [
    ("career_offensive_snaps", "Hücum snap", "snap"),
    ("career_defensive_snaps", "Savunma snap", "snap"),
    ("career_special_teams_snaps", "Özel takım snap", "snap"),
    ("career_games_active", "Aktif maç", "maç"),
    ("career_games_started", "İlk 11 başladığı maç", "maç"),
    ("ap_all_pro_1st_team", "All-Pro 1. takım", "kez"),
    ("ap_all_pro_2nd_team", "All-Pro 2. takım", "kez"),
    ("pro_bowl_original_ballot", "Pro Bowl", "kez"),
]

ROLE_METRICS = {
    "Hücum hattı": ("pressure_allowed_rate", "Baskı verme oranı", "%"),
    "Pas yakalayıcı": ("receiving_yards", "Pas yakalama yardı", "yard"),
    "Koşu oyuncusu": ("rushing_yards", "Koşu yardı", "yard"),
    "Ön savunma": ("sacks", "Sack kredisi", "sack"),
    "Arka savunma": ("tackles", "Tackle", "tackle"),
    "Diğer": ("games", "Gözlenen maç", "maç"),
}


def team_label(abbr):
    return f"{TEAM_NAMES.get(abbr, abbr)} ({abbr})" if abbr else "Takım bilgisi yok"


def position_label(code):
    return f"{POSITION_NAMES.get(code, 'Pozisyon bilgisi yok')} ({code})" if code else "Pozisyon bilgisi yok"


def role_for_position(code):
    if code in {"C", "G", "T"}:
        return "Hücum hattı"
    if code in {"WR", "TE"}:
        return "Pas yakalayıcı"
    if code in {"RB", "FB"}:
        return "Koşu oyuncusu"
    if code in {"DE", "DT", "NT", "OLB", "ILB", "MLB"}:
        return "Ön savunma"
    if code in {"CB", "DB", "FS", "SS"}:
        return "Arka savunma"
    return "Diğer"


def formatted_fields(record, fields):
    if not record:
        return []
    result = []
    for key, label, unit in fields:
        value = record.get(key)
        if value is None or value == "":
            shown = "Bilgi yok"
        elif key == "combine_position":
            shown = position_label(value)
        elif isinstance(value, float):
            shown = f"{value:g}"
        else:
            shown = str(value)
        if unit and shown != "Bilgi yok":
            shown += f" {unit}"
        result.append({"Alan": label, "Değer": shown})
    return result


def comparison_groups(rows):
    """Aggregate team rows within the same selected season and season type."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[(role_for_position(row["nfl_position"]), row["nfl_id"])].append(row)
    result = defaultdict(list)
    for (role, player_id), parts in grouped.items():
        metric, _, unit = ROLE_METRICS[role]
        if metric == "pressure_allowed_rate":
            labeled = sum(p["pressure_labeled_plays"] for p in parts)
            value = (sum(p["pressure_allowed_rate"] * p["pressure_labeled_plays"]
                         for p in parts if p["pressure_allowed_rate"] is not None) / labeled
                     if labeled else None)
            if value is not None:
                value *= 100
            sample = labeled
        else:
            values = [p[metric] for p in parts if p.get(metric) is not None]
            value = sum(values) if values else None
            labels = {
                "receiving_yards": "receiving_labeled_plays",
                "rushing_yards": "rushing_labeled_plays",
                "tackles": "tackle_labeled_plays",
                "sacks": "sack_labeled_plays",
            }
            if metric in labels:
                sample = (sum(p[labels[metric]] for p in parts)
                          if all(labels[metric] in p for p in parts) else None)
            else:
                sample = sum(p["games"] for p in parts)
        result[role].append({
            "nfl_id": player_id, "Oyuncu": parts[0]["display_name"],
            "Pozisyon": position_label(parts[0]["nfl_position"]),
            "Değer": value, "Birim": unit,
            "Gözlenen maç": sum(p["games"] for p in parts),
            "Etiketli kayıt": sample,
            "Az veri": sample is None or sample < (3 if metric == "games" else 10),
        })
    return dict(result)
