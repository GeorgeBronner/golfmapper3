#!/usr/bin/env python3
"""
Golf Course Mapping Script
Maps actively used Garmin courses to golf_courses_loc_merged.db with confidence scoring (1-5)

Author: Generated for GolfMapper3 migration
Date: 2026-01-10
"""

import sqlite3
import json
import csv
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import re
from collections import Counter

try:
    import pandas as pd
    import numpy as np
    from rapidfuzz import fuzz
    from geopy.distance import geodesic
except ImportError as e:
    print(f"Missing required library: {e}")
    print("\nPlease install required dependencies:")
    print("  pip install pandas numpy rapidfuzz geopy")
    exit(1)


# ============================================================================
# Configuration
# ============================================================================

# Get project root (parent of scripts directory)
PROJECT_ROOT = Path(__file__).parent.parent
GARMIN_DB_PATH = PROJECT_ROOT / "backend/app/garmin.db"
GOLF_COURSES_DB_PATH = PROJECT_ROOT / "dbs/golf_mapper_sqlite.db"
OUTPUT_DIR = PROJECT_ROOT / "dbs"

# Scoring weights (must sum to 1.0)
# State and long distance are hard constraints, not weighted factors
# Priority: Distance > Name > City
WEIGHT_DISTANCE = 0.50
WEIGHT_NAME = 0.35
WEIGHT_CITY = 0.15

# Multi-course facility handling:
# When Garmin course name has "Club - Course" format, the name score is computed as:
#   name_score = (club_match * 0.30) + (course_match * 0.70)
# This ensures course-specific names are prioritized over club names when there are
# multiple courses at the same facility (e.g., "Bandon Dunes Golf Resort - Bandon Dunes"
# vs "Bandon Dunes Golf Resort - Pacific Dunes")

# Hard constraint thresholds
MAX_DISTANCE_METERS = 100000  # 100km - beyond this, confidence is forced to 1

# Confidence level thresholds
CONFIDENCE_THRESHOLDS = {
    5: 0.85,  # Almost certain
    4: 0.70,  # Highly likely
    3: 0.50,  # Possible
    2: 0.30,  # Weak
    1: 0.00,  # No match
}


# ============================================================================
# Data Normalization
# ============================================================================

def normalize_name(name: str) -> str:
    """Normalize course/club name for comparison by removing common golf terms."""
    if not name or pd.isna(name):
        return ""

    name = str(name).strip().lower()

    # Remove "the" prefix
    name = re.sub(r'^the\s+', '', name)

    # Normalize location terms first
    replacements = {
        r'\bsaint\b': 'st',
        r'\bst\.\b': 'st',
        r'\bmount\b': 'mt',
        r'\bmt\.\b': 'mt',
    }

    for pattern, replacement in replacements.items():
        name = re.sub(pattern, replacement, name)

    # Remove common golf-related terms (as suffixes/standalone)
    # More conservative - only remove when they're clearly generic, not part of the distinctive name
    # Remove trailing terms
    name = re.sub(r'\s+(golf\s+and\s+country\s+club|country\s+club|yacht\s+and\s+country\s+club|'
                  r'yacht\s+&\s+country\s+club|golf\s+club|golf\s+course|golf\s+trail|'
                  r'g\.c\.|c\.c\.|cc|gc|links)$', '', name)

    # Remove leading "rtj golf trail at" and similar organization prefixes
    name = re.sub(r'^(rtj\s+golf\s+trail\s+at|golf\s+trail\s+at)\s+', '', name)

    # Remove standalone common words
    name = re.sub(r'\s+(golf|course|club|trail)\s+', ' ', name)

    # Remove these words if they appear at the end after other removals
    name = re.sub(r'\s+(golf|course|club|trail)$', '', name)

    # Remove extra punctuation and whitespace
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()

    return name


def normalize_location(location: str) -> str:
    """Normalize city/state for comparison."""
    if not location or pd.isna(location):
        return ""
    return str(location).strip().lower()


def normalize_state(state: str) -> str:
    """Normalize state/province code."""
    if not state or pd.isna(state):
        return ""

    state = str(state).strip().upper()

    # Map state abbreviations to full names
    state_mapping = {
        # US States
        'AL': 'ALABAMA', 'AK': 'ALASKA', 'AZ': 'ARIZONA', 'AR': 'ARKANSAS',
        'CA': 'CALIFORNIA', 'CO': 'COLORADO', 'CT': 'CONNECTICUT', 'DE': 'DELAWARE',
        'FL': 'FLORIDA', 'GA': 'GEORGIA', 'HI': 'HAWAII', 'ID': 'IDAHO',
        'IL': 'ILLINOIS', 'IN': 'INDIANA', 'IA': 'IOWA', 'KS': 'KANSAS',
        'KY': 'KENTUCKY', 'LA': 'LOUISIANA', 'ME': 'MAINE', 'MD': 'MARYLAND',
        'MA': 'MASSACHUSETTS', 'MI': 'MICHIGAN', 'MN': 'MINNESOTA', 'MS': 'MISSISSIPPI',
        'MO': 'MISSOURI', 'MT': 'MONTANA', 'NE': 'NEBRASKA', 'NV': 'NEVADA',
        'NH': 'NEW HAMPSHIRE', 'NJ': 'NEW JERSEY', 'NM': 'NEW MEXICO', 'NY': 'NEW YORK',
        'NC': 'NORTH CAROLINA', 'ND': 'NORTH DAKOTA', 'OH': 'OHIO', 'OK': 'OKLAHOMA',
        'OR': 'OREGON', 'PA': 'PENNSYLVANIA', 'RI': 'RHODE ISLAND', 'SC': 'SOUTH CAROLINA',
        'SD': 'SOUTH DAKOTA', 'TN': 'TENNESSEE', 'TX': 'TEXAS', 'UT': 'UTAH',
        'VT': 'VERMONT', 'VA': 'VIRGINIA', 'WA': 'WASHINGTON', 'WV': 'WEST VIRGINIA',
        'WI': 'WISCONSIN', 'WY': 'WYOMING',
        # Canadian Provinces
        'AB': 'ALBERTA', 'BC': 'BRITISH COLUMBIA', 'MB': 'MANITOBA', 'NB': 'NEW BRUNSWICK',
        'NL': 'NEWFOUNDLAND AND LABRADOR', 'NS': 'NOVA SCOTIA', 'ON': 'ONTARIO',
        'PE': 'PRINCE EDWARD ISLAND', 'QC': 'QUEBEC', 'SK': 'SASKATCHEWAN',
    }

    return state_mapping.get(state, state)


def normalize_country(country: str) -> str:
    """Normalize country name."""
    if not country or pd.isna(country):
        return ""

    country = str(country).strip().lower()

    # Normalize common variations
    if country in ['usa', 'us', 'united states', 'united states of america']:
        return 'united states'
    elif country in ['canada', 'ca']:
        return 'canada'

    return country


# ============================================================================
# Scoring Functions
# ============================================================================

def calculate_distance_score(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate geographic distance score using Haversine formula.
    Returns score between 0.0 and 1.0.
    """
    # Check for missing coordinates
    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return 0.0

    try:
        distance_m = geodesic((lat1, lon1), (lat2, lon2)).meters

        # Score based on distance thresholds
        if distance_m < 100:
            return 1.0
        elif distance_m < 500:
            return 0.9
        elif distance_m < 1000:
            return 0.7
        elif distance_m < 5000:
            return 0.4
        elif distance_m < 10000:
            return 0.2
        else:
            return 0.0
    except Exception:
        return 0.0


def parse_garmin_course_name(full_name: str) -> Tuple[str, str]:
    """
    Parse a Garmin course name into (club_part, course_part).
    Garmin names often follow "Club Name - Course Name" format.

    Returns (club_part, course_part) where course_part is empty if no separator found.
    """
    if not full_name or pd.isna(full_name):
        return "", ""

    full_name = str(full_name).strip()

    # Check for common separators: " - ", " – ", " — " (different dash types)
    separators = [' - ', ' – ', ' — ']

    for sep in separators:
        if sep in full_name:
            parts = full_name.split(sep, 1)  # Split on first occurrence only
            return parts[0].strip(), parts[1].strip()

    # No separator found - treat entire name as club part
    return full_name, ""


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    Calculate name similarity using multiple fuzzy matching algorithms.
    Returns the best score between 0.0 and 1.0.
    """
    if not name1 or not name2:
        return 0.0

    # Normalize names
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    if not n1 or not n2:
        return 0.0

    # Try multiple algorithms and take the best
    scores = [
        fuzz.ratio(n1, n2) / 100.0,           # Levenshtein
        fuzz.token_sort_ratio(n1, n2) / 100.0, # Token sort (order-independent)
        fuzz.partial_ratio(n1, n2) / 100.0,    # Partial match
    ]

    return max(scores)


def calculate_city_match(city1: str, city2: str) -> float:
    """
    Calculate city match score.
    Returns 1.0 for exact match, 0.8 for fuzzy match, 0.0 otherwise.
    """
    if not city1 or not city2:
        return 0.0

    c1 = normalize_location(city1)
    c2 = normalize_location(city2)

    if not c1 or not c2:
        return 0.0

    # Exact match
    if c1 == c2:
        return 1.0

    # Fuzzy match (handle typos)
    similarity = fuzz.ratio(c1, c2) / 100.0
    if similarity >= 0.85:
        return 0.8

    return 0.0


def calculate_state_match(state1: str, state2: str) -> Tuple[float, bool]:
    """
    Calculate state/province match score.
    Returns (score, both_have_state_data).

    - score: 1.0 for match, 0.0 for mismatch or missing data
    - both_have_state_data: True if both courses have state data, False otherwise
    """
    # Check if both have state data
    if not state1 or not state2 or pd.isna(state1) or pd.isna(state2):
        return 0.0, False

    s1 = normalize_state(state1)
    s2 = normalize_state(state2)

    if not s1 or not s2:
        return 0.0, False

    # Both have state data - check if they match
    match = 1.0 if s1 == s2 else 0.0
    return match, True


def calculate_composite_score(distance_score: float, name_score: float,
                              city_score: float) -> float:
    """
    Calculate weighted composite score.
    State matching is a hard constraint, not a weighted factor.
    Returns score between 0.0 and 1.0.
    """
    composite = (
        distance_score * WEIGHT_DISTANCE +
        name_score * WEIGHT_NAME +
        city_score * WEIGHT_CITY
    )

    return composite


def assign_confidence_level(composite_score: float, has_coordinates: bool,
                           distance_meters: Optional[float], state_match: bool,
                           both_have_state_data: bool, is_us_course: bool) -> int:
    """
    Assign confidence level (1-5) based on composite score and hard constraints.

    Hard constraints (force confidence to 1):
    - Distance > 100km (when coordinates available)
    - States explicitly don't match (only for US courses with state data)

    Max confidence is capped at 4 if coordinates are missing (can't verify distance).
    """
    # Hard constraint: State mismatch only matters for US courses
    if is_us_course and both_have_state_data and not state_match:
        return 1

    # Hard constraint: If we have distance and it's > 100km, confidence is 1
    if distance_meters is not None and distance_meters > MAX_DISTANCE_METERS:
        return 1

    # Cap confidence based on coordinate availability
    # Missing coordinates means we can't verify distance, so max confidence is 4
    max_confidence = 5 if has_coordinates else 4

    for level in sorted(CONFIDENCE_THRESHOLDS.keys(), reverse=True):
        if level > max_confidence:
            continue
        if composite_score >= CONFIDENCE_THRESHOLDS[level]:
            return level

    return 1


# ============================================================================
# Database Loading
# ============================================================================

def load_actively_used_garmin_courses(garmin_db_path: Path, use_new_table_only: bool = False) -> pd.DataFrame:
    """
    Load Garmin courses that are actively used by users.

    Args:
        garmin_db_path: Path to Garmin database
        use_new_table_only: If True, only read from new_user_courses table.
                           If False, combine both user_courses and new_user_courses.
    """
    print("Loading actively used Garmin courses...")
    if use_new_table_only:
        print("  [Using new_user_courses table only]")

    conn = sqlite3.connect(garmin_db_path)

    # Get unique course IDs from user tables
    if use_new_table_only:
        # Only query new_user_courses
        query = """
        SELECT DISTINCT course_id
        FROM new_user_courses
        """
    else:
        # Query both tables and combine
        query = """
        SELECT DISTINCT garmin_id as course_id
        FROM user_courses
        WHERE garmin_id IS NOT NULL
        UNION
        SELECT DISTINCT course_id
        FROM new_user_courses
        """

    used_course_ids = pd.read_sql_query(query, conn)
    course_ids_list = used_course_ids['course_id'].tolist()

    print(f"  Found {len(course_ids_list)} unique Garmin courses in use")

    # Load course data for used courses
    placeholders = ','.join('?' * len(course_ids_list))
    courses_query = f"""
    SELECT
        id,
        g_course as course_name,
        g_address as address,
        g_city as city,
        g_state as state,
        g_country as country,
        g_latitude as latitude,
        g_longitude as longitude
    FROM courses
    WHERE id IN ({placeholders})
    """

    courses_df = pd.read_sql_query(courses_query, conn, params=course_ids_list)

    # Count usage per course
    if use_new_table_only:
        # Only count from new_user_courses
        usage_query = """
        SELECT course_id, COUNT(*) as times_played
        FROM new_user_courses
        GROUP BY course_id
        """
    else:
        # Count from both tables
        usage_query = """
        SELECT garmin_id as course_id, COUNT(*) as times_played
        FROM user_courses
        WHERE garmin_id IS NOT NULL
        GROUP BY garmin_id
        UNION ALL
        SELECT course_id, COUNT(*) as times_played
        FROM new_user_courses
        GROUP BY course_id
        """

    usage_df = pd.read_sql_query(usage_query, conn)
    usage_counts = usage_df.groupby('course_id')['times_played'].sum().to_dict()

    courses_df['times_played'] = courses_df['id'].map(usage_counts).fillna(0).astype(int)

    # Extract years from new_user_courses (only available in new table)
    if use_new_table_only:
        # Get all years for each course as a list
        years_query = """
        SELECT course_id, year
        FROM new_user_courses
        WHERE year IS NOT NULL
        ORDER BY course_id, year
        """
        years_df = pd.read_sql_query(years_query, conn)

        # Group years by course_id into lists
        years_by_course = years_df.groupby('course_id')['year'].apply(list).to_dict()
        courses_df['years_played'] = courses_df['id'].map(years_by_course).fillna('').apply(
            lambda x: sorted(set(x)) if isinstance(x, list) else []
        )
    else:
        # When using both tables, we don't have year data from user_courses
        courses_df['years_played'] = [[] for _ in range(len(courses_df))]

    conn.close()

    print(f"  Loaded {len(courses_df)} Garmin courses")

    return courses_df


def load_golf_courses_data(golf_courses_db_path: Path) -> pd.DataFrame:
    """
    Load all courses from golf_courses_loc_merged.db with location data.
    """
    print("Loading golf_courses_loc_merged.db data...")

    conn = sqlite3.connect(golf_courses_db_path)

    query = """
    SELECT
        id,
        club_name,
        course_name,
        address,
        city,
        state,
        country,
        latitude,
        longitude
    FROM courses
    """

    courses_df = pd.read_sql_query(query, conn)
    conn.close()

    print(f"  Loaded {len(courses_df)} golf courses")
    print(f"  Courses with coordinates: {courses_df['latitude'].notna().sum()}")

    return courses_df


# ============================================================================
# Matching Algorithm
# ============================================================================

def find_matches(garmin_course: pd.Series, golf_courses_df: pd.DataFrame,
                 top_n: int = 3) -> List[Dict]:
    """
    Find top N matches for a Garmin course in golf_courses_loc_merged.db.
    Returns list of match dictionaries sorted by score.

    Enhanced to handle multi-course facilities by parsing "Club - Course" format
    and prioritizing course-specific name matches when candidates share a club.
    """
    # Pre-filter by country and state to reduce comparisons
    candidates = golf_courses_df.copy()

    # Check if this is a US course
    is_us_course = False
    if pd.notna(garmin_course['country']):
        garmin_country = normalize_country(garmin_course['country'])
        is_us_course = garmin_country == 'united states'

        # Filter by country if available
        candidates = candidates[
            candidates['country'].apply(lambda x: normalize_country(x) == garmin_country)
        ]

    # Filter by state ONLY for US courses
    if is_us_course and pd.notna(garmin_course['state']):
        garmin_state = normalize_state(garmin_course['state'])
        candidates = candidates[
            candidates['state'].apply(lambda x: normalize_state(x) == garmin_state)
        ]

    if len(candidates) == 0:
        # No candidates in same state/country, use all courses
        candidates = golf_courses_df.copy()

    # Parse Garmin course name into club and course parts
    garmin_club_part, garmin_course_part = parse_garmin_course_name(garmin_course['course_name'])
    has_garmin_course_specific = bool(garmin_course_part)

    # Calculate scores for all candidates
    matches = []

    for _, golf_course in candidates.iterrows():
        # Calculate individual scores
        distance_score = calculate_distance_score(
            garmin_course['latitude'], garmin_course['longitude'],
            golf_course['latitude'], golf_course['longitude']
        )

        # Enhanced name matching with club/course awareness
        if has_garmin_course_specific:
            # Garmin has "Club - Course" format
            # Match club part against golf club_name
            club_match_score = calculate_name_similarity(
                garmin_club_part, golf_course['club_name']
            )

            # Match course-specific part against golf course_name
            course_specific_score = calculate_name_similarity(
                garmin_course_part, golf_course['course_name']
            )

            # When Garmin has course-specific info, prioritize it heavily
            # Weight: 30% club match + 70% course-specific match
            name_score = (club_match_score * 0.3) + (course_specific_score * 0.7)

            # Store individual scores for debugging
            club_score = club_match_score
            course_score = course_specific_score
        else:
            # Garmin doesn't have "Club - Course" format
            # Use traditional max-of-both approach
            name_score_club = calculate_name_similarity(
                garmin_course['course_name'], golf_course['club_name']
            )
            name_score_course = calculate_name_similarity(
                garmin_course['course_name'], golf_course['course_name']
            )
            name_score = max(name_score_club, name_score_course)
            club_score = name_score_club
            course_score = name_score_course

        city_score = calculate_city_match(
            garmin_course['city'], golf_course['city']
        )

        state_score, both_have_state_data = calculate_state_match(
            garmin_course['state'], golf_course['state']
        )

        # Calculate composite score (state is a hard constraint, not weighted)
        composite = calculate_composite_score(
            distance_score, name_score, city_score
        )

        # Check if both courses have coordinates
        has_coordinates = (
            pd.notna(garmin_course['latitude']) and
            pd.notna(garmin_course['longitude']) and
            pd.notna(golf_course['latitude']) and
            pd.notna(golf_course['longitude'])
        )

        # Calculate actual distance for reporting
        distance_meters = None
        if has_coordinates:
            try:
                distance_meters = geodesic(
                    (garmin_course['latitude'], garmin_course['longitude']),
                    (golf_course['latitude'], golf_course['longitude'])
                ).meters
            except Exception:
                distance_meters = None

        matches.append({
            'golf_courses_id': golf_course['id'],
            'golf_club_name': golf_course['club_name'],
            'golf_course_name': golf_course['course_name'],
            'golf_city': golf_course['city'],
            'golf_state': golf_course['state'],
            'golf_country': golf_course['country'],
            'golf_latitude': golf_course['latitude'],
            'golf_longitude': golf_course['longitude'],
            'distance_meters': distance_meters,
            'name_similarity_score': name_score,
            'club_match_score': club_score,
            'course_specific_match_score': course_score,
            'city_match': city_score > 0,
            'state_match': state_score > 0,
            'both_have_state_data': both_have_state_data,
            'composite_score': composite,
            'has_coordinates': has_coordinates,
            'is_us_course': is_us_course,
        })

    # Filter out matches that violate hard constraints
    valid_matches = []
    for match in matches:
        # Check hard constraints
        # State mismatch only matters for US courses
        violates_state_constraint = (
            match['is_us_course'] and
            match['both_have_state_data'] and
            not match['state_match']
        )

        # Distance constraint: Only check if coordinates are available
        violates_distance_constraint = False
        if match['distance_meters'] is not None:
            # If we can calculate distance, enforce the 100km limit
            violates_distance_constraint = match['distance_meters'] > MAX_DISTANCE_METERS

        # Only include matches that don't violate hard constraints
        if not violates_state_constraint and not violates_distance_constraint:
            valid_matches.append(match)

    # Sort by composite score (descending)
    valid_matches.sort(key=lambda x: x['composite_score'], reverse=True)

    # Return top N matches
    return valid_matches[:top_n]


def map_all_courses(garmin_df: pd.DataFrame, golf_courses_df: pd.DataFrame) -> List[Dict]:
    """
    Map all Garmin courses to golf_courses_loc_merged.db.
    Returns list of mapping dictionaries.
    """
    print("\nMatching courses...")

    mappings = []
    total = len(garmin_df)

    for idx, garmin_course in garmin_df.iterrows():
        # Find top 3 matches
        matches = find_matches(garmin_course, golf_courses_df, top_n=3)

        if not matches:
            # No matches found
            mapping = {
                'garmin_id': garmin_course['id'],
                'garmin_course_name': garmin_course['course_name'],
                'garmin_city': garmin_course['city'],
                'garmin_state': garmin_course['state'],
                'garmin_country': garmin_course['country'],
                'garmin_latitude': garmin_course['latitude'],
                'garmin_longitude': garmin_course['longitude'],
                'times_played': garmin_course['times_played'],
                'years_played': garmin_course['years_played'],
                'golf_courses_id': None,
                'golf_club_name': None,
                'golf_course_name': None,
                'golf_city': None,
                'golf_state': None,
                'golf_country': None,
                'golf_latitude': None,
                'golf_longitude': None,
                'distance_meters': None,
                'name_similarity_score': 0.0,
                'composite_score': 0.0,
                'confidence_level': 1,
                'missing_coordinates': False,  # No match, so N/A
                'second_best_golf_id': None,
                'second_best_club_name': None,
                'second_best_course_name': None,
                'second_best_score': None,
                'third_best_golf_id': None,
                'third_best_club_name': None,
                'third_best_course_name': None,
                'third_best_score': None,
            }

            # Log no match found
            print(f"  [{idx + 1}/{total}] '{garmin_course['course_name']}' ({garmin_course['city']}, {garmin_course['state']}) -> NO MATCH")
        else:
            # Best match
            best_match = matches[0]
            confidence = assign_confidence_level(
                best_match['composite_score'],
                best_match['has_coordinates'],
                best_match['distance_meters'],
                best_match['state_match'],
                best_match['both_have_state_data'],
                best_match['is_us_course']
            )

            mapping = {
                'garmin_id': garmin_course['id'],
                'garmin_course_name': garmin_course['course_name'],
                'garmin_city': garmin_course['city'],
                'garmin_state': garmin_course['state'],
                'garmin_country': garmin_course['country'],
                'garmin_latitude': garmin_course['latitude'],
                'garmin_longitude': garmin_course['longitude'],
                'times_played': garmin_course['times_played'],
                'years_played': garmin_course['years_played'],
                'golf_courses_id': best_match['golf_courses_id'],
                'golf_club_name': best_match['golf_club_name'],
                'golf_course_name': best_match['golf_course_name'],
                'golf_city': best_match['golf_city'],
                'golf_state': best_match['golf_state'],
                'golf_country': best_match['golf_country'],
                'golf_latitude': best_match['golf_latitude'],
                'golf_longitude': best_match['golf_longitude'],
                'distance_meters': best_match['distance_meters'],
                'name_similarity_score': best_match['name_similarity_score'],
                'composite_score': best_match['composite_score'],
                'confidence_level': confidence,
                'missing_coordinates': not best_match['has_coordinates'],
                'second_best_golf_id': matches[1]['golf_courses_id'] if len(matches) > 1 else None,
                'second_best_club_name': matches[1]['golf_club_name'] if len(matches) > 1 else None,
                'second_best_course_name': matches[1]['golf_course_name'] if len(matches) > 1 else None,
                'second_best_score': matches[1]['composite_score'] if len(matches) > 1 else None,
                'third_best_golf_id': matches[2]['golf_courses_id'] if len(matches) > 2 else None,
                'third_best_club_name': matches[2]['golf_club_name'] if len(matches) > 2 else None,
                'third_best_course_name': matches[2]['golf_course_name'] if len(matches) > 2 else None,
                'third_best_score': matches[2]['composite_score'] if len(matches) > 2 else None,
            }

            # Log match result
            dist_str = f"{best_match['distance_meters']:.0f}m" if pd.notna(best_match['distance_meters']) else "N/A"
            missing_coords_note = " [MISSING COORDS]" if not best_match['has_coordinates'] else ""

            # Format golf course display: show both club_name and course_name
            club_name = best_match['golf_club_name'] if pd.notna(best_match['golf_club_name']) else ""
            course_name = best_match['golf_course_name'] if pd.notna(best_match['golf_course_name']) else ""

            if club_name and course_name:
                golf_display = f"{club_name} - {course_name}"
            elif club_name:
                golf_display = club_name
            elif course_name:
                golf_display = course_name
            else:
                golf_display = "Unknown"

            # Add club/course score breakdown for debugging multi-course facilities
            garmin_club_part, garmin_course_part = parse_garmin_course_name(garmin_course['course_name'])
            if garmin_course_part:
                # Show individual club and course scores
                score_details = (f"Club:{best_match['club_match_score']:.2f}, "
                               f"Course:{best_match['course_specific_match_score']:.2f}")
            else:
                score_details = f"Name:{best_match['name_similarity_score']:.3f}"

            print(f"  [{idx + 1}/{total}] '{garmin_course['course_name']}' -> '{golf_display}' "
                  f"(Conf: {confidence}, Score: {best_match['composite_score']:.3f}, "
                  f"{score_details}, Dist: {dist_str}){missing_coords_note}")

        mappings.append(mapping)

    print(f"\n  Completed: {total}/{total} courses matched")

    return mappings


# ============================================================================
# Output Generation
# ============================================================================

def generate_csv_output(mappings: List[Dict], output_path: Path):
    """Generate CSV output file."""
    print(f"\nGenerating CSV output: {output_path}")

    df = pd.DataFrame(mappings)
    df.to_csv(output_path, index=False)

    print(f"  CSV file created: {len(df)} rows")


def generate_json_output(mappings: List[Dict], output_path: Path):
    """Generate JSON output file."""
    print(f"\nGenerating JSON output: {output_path}")

    # Calculate statistics
    confidence_dist = Counter(m['confidence_level'] for m in mappings)

    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_garmin_courses': len(mappings),
            'total_matches': len([m for m in mappings if m['golf_courses_id'] is not None]),
            'confidence_distribution': {
                str(i): confidence_dist.get(i, 0) for i in range(1, 6)
            }
        },
        'mappings': []
    }

    for m in mappings:
        # Extract years_played - handle both list and string cases
        years_played = m['years_played']
        if isinstance(years_played, str):
            years_played = []
        elif not isinstance(years_played, list):
            years_played = []

        mapping_obj = {
            'garmin': {
                'id': int(m['garmin_id']) if pd.notna(m['garmin_id']) else None,
                'course_name': m['garmin_course_name'],
                'city': m['garmin_city'],
                'state': m['garmin_state'],
                'country': m['garmin_country'],
                'latitude': float(m['garmin_latitude']) if pd.notna(m['garmin_latitude']) else None,
                'longitude': float(m['garmin_longitude']) if pd.notna(m['garmin_longitude']) else None,
                'years_played': years_played,
            },
            'golf_courses': {
                'id': int(m['golf_courses_id']) if pd.notna(m['golf_courses_id']) else None,
                'club_name': m['golf_club_name'],
                'course_name': m['golf_course_name'],
                'city': m['golf_city'],
                'state': m['golf_state'],
                'country': m['golf_country'],
                'latitude': float(m['golf_latitude']) if pd.notna(m['golf_latitude']) else None,
                'longitude': float(m['golf_longitude']) if pd.notna(m['golf_longitude']) else None,
            },
            'match_quality': {
                'confidence_level': int(m['confidence_level']),
                'composite_score': float(m['composite_score']),
                'name_similarity': float(m['name_similarity_score']),
                'distance_meters': float(m['distance_meters']) if pd.notna(m['distance_meters']) else None,
                'missing_coordinates': bool(m['missing_coordinates']),
            },
            'alternatives': [],
            'usage': {
                'times_played': int(m['times_played']),
            }
        }

        # Add alternatives
        if pd.notna(m['second_best_golf_id']):
            mapping_obj['alternatives'].append({
                'golf_courses_id': int(m['second_best_golf_id']),
                'club_name': m['second_best_club_name'],
                'course_name': m['second_best_course_name'],
                'score': float(m['second_best_score'])
            })

        if pd.notna(m['third_best_golf_id']):
            mapping_obj['alternatives'].append({
                'golf_courses_id': int(m['third_best_golf_id']),
                'club_name': m['third_best_club_name'],
                'course_name': m['third_best_course_name'],
                'score': float(m['third_best_score'])
            })

        output['mappings'].append(mapping_obj)

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"  JSON file created: {len(output['mappings'])} mappings")


def generate_summary_report(mappings: List[Dict], output_path: Path):
    """Generate markdown summary report."""
    print(f"\nGenerating summary report: {output_path}")

    df = pd.DataFrame(mappings)
    confidence_dist = df['confidence_level'].value_counts().sort_index()

    # Calculate statistics by confidence level
    stats_by_conf = []
    for conf_level in range(5, 0, -1):
        conf_df = df[df['confidence_level'] == conf_level]
        if len(conf_df) > 0:
            avg_distance = conf_df['distance_meters'].mean()
            avg_name_sim = conf_df['name_similarity_score'].mean()
            stats_by_conf.append({
                'level': conf_level,
                'count': len(conf_df),
                'avg_distance': avg_distance,
                'avg_name_sim': avg_name_sim,
            })

    # Generate report
    missing_coords_count = len(df[df['missing_coordinates'] == True])

    lines = [
        "# Golf Course Mapping Summary Report",
        f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"\n## Overview\n",
        f"- **Total Garmin courses mapped**: {len(mappings)}",
        f"- **Courses with matches**: {len(df[df['golf_courses_id'].notna()])} ({len(df[df['golf_courses_id'].notna()]) / len(df) * 100:.1f}%)",
        f"- **Courses without matches**: {len(df[df['golf_courses_id'].isna()])} ({len(df[df['golf_courses_id'].isna()]) / len(df) * 100:.1f}%)",
        f"- **Matches with missing coordinates**: {missing_coords_count} ({missing_coords_count / len(df) * 100:.1f}%)",
        "\n## Confidence Level Distribution\n",
        "| Confidence | Count | Percentage | Avg Distance (m) | Avg Name Similarity |",
        "|-----------|-------|------------|------------------|---------------------|",
    ]

    for stat in stats_by_conf:
        pct = stat['count'] / len(df) * 100
        dist_str = f"{stat['avg_distance']:.0f}" if not pd.isna(stat['avg_distance']) else "N/A"
        lines.append(
            f"| {stat['level']} | {stat['count']} | {pct:.1f}% | {dist_str} | {stat['avg_name_sim']:.3f} |"
        )

    # High confidence matches (ready for migration)
    high_conf = df[df['confidence_level'] >= 4]
    lines.extend([
        f"\n## High-Confidence Matches (Confidence 4-5)\n",
        f"**{len(high_conf)} courses** ({len(high_conf) / len(df) * 100:.1f}%) are ready for migration with high confidence.\n",
        "### Sample High-Confidence Matches\n",
    ])

    for _, row in high_conf.head(10).iterrows():
        dist_str = f"{row['distance_meters']:.0f}m" if pd.notna(row['distance_meters']) else "N/A"
        lines.append(
            f"- **{row['garmin_course_name']}** -> **{row['golf_course_name']}** "
            f"(Confidence: {row['confidence_level']}, Score: {row['composite_score']:.3f}, Distance: {dist_str})"
        )

    # Medium confidence (need review)
    medium_conf = df[df['confidence_level'] == 3]
    if len(medium_conf) > 0:
        lines.extend([
            f"\n## Medium-Confidence Matches (Confidence 3)\n",
            f"**{len(medium_conf)} courses** ({len(medium_conf) / len(df) * 100:.1f}%) may need manual review.\n",
            "### Courses Needing Review\n",
        ])

        for _, row in medium_conf.head(20).iterrows():
            dist_str = f"{row['distance_meters']:.0f}m" if pd.notna(row['distance_meters']) else "N/A"
            lines.append(
                f"- **{row['garmin_course_name']}** ({row['garmin_city']}, {row['garmin_state']}) -> "
                f"**{row['golf_course_name']}** ({row['golf_city']}, {row['golf_state']}) "
                f"(Score: {row['composite_score']:.3f}, Distance: {dist_str})"
            )

    # Low confidence and no matches
    low_conf = df[df['confidence_level'] <= 2]
    if len(low_conf) > 0:
        lines.extend([
            f"\n## Low-Confidence Matches & No Matches (Confidence 1-2)\n",
            f"**{len(low_conf)} courses** ({len(low_conf) / len(df) * 100:.1f}%) require manual review or may not exist in golf_courses_loc_merged.db.\n",
            "### Unmatched or Poorly Matched Courses\n",
        ])

        for _, row in low_conf.iterrows():
            if pd.notna(row['golf_courses_id']):
                dist_str = f"{row['distance_meters']:.0f}m" if pd.notna(row['distance_meters']) else "N/A"
                lines.append(
                    f"- **{row['garmin_course_name']}** ({row['garmin_city']}, {row['garmin_state']}) -> "
                    f"**{row['golf_course_name']}** ({row['golf_city']}, {row['golf_state']}) "
                    f"(Score: {row['composite_score']:.3f}, Distance: {dist_str})"
                )
            else:
                lines.append(
                    f"- **{row['garmin_course_name']}** ({row['garmin_city']}, {row['garmin_state']}) -> "
                    f"**NO MATCH FOUND**"
                )

    # Write report
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"  Summary report created")


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Main execution function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Map Garmin courses to golf_courses_loc_merged.db with confidence scoring',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--limit', '-n',
        type=int,
        default=None,
        metavar='N',
        help='Process only the first N courses (useful for testing)'
    )
    parser.add_argument(
        '--new-only',
        action='store_true',
        help='Only read user data from new_user_courses table (exclude legacy user_courses table)'
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Golf Course Mapping: Garmin -> golf_courses_loc_merged.db")
    print("=" * 70)

    # Validate input files
    if not GARMIN_DB_PATH.exists():
        print(f"ERROR: Garmin database not found: {GARMIN_DB_PATH}")
        return

    if not GOLF_COURSES_DB_PATH.exists():
        print(f"ERROR: Golf courses database not found: {GOLF_COURSES_DB_PATH}")
        return

    # Create output directory if needed
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    garmin_df = load_actively_used_garmin_courses(GARMIN_DB_PATH, use_new_table_only=args.new_only)
    golf_courses_df = load_golf_courses_data(GOLF_COURSES_DB_PATH)

    # Apply limit if specified
    if args.limit is not None:
        original_count = len(garmin_df)
        garmin_df = garmin_df.head(args.limit)
        print(f"\n** LIMIT APPLIED: Processing first {len(garmin_df)} of {original_count} courses **\n")

    # Match courses
    mappings = map_all_courses(garmin_df, golf_courses_df)

    # Generate outputs
    csv_path = OUTPUT_DIR / "garmin_to_golf_courses_mapping.csv"
    json_path = OUTPUT_DIR / "garmin_to_golf_courses_mapping.json"
    summary_path = OUTPUT_DIR / "mapping_summary.md"

    generate_csv_output(mappings, csv_path)
    generate_json_output(mappings, json_path)
    generate_summary_report(mappings, summary_path)

    # Print summary
    print("\n" + "=" * 70)
    print("MAPPING COMPLETE")
    print("=" * 70)

    if args.new_only:
        print("\n** Using new_user_courses table only **")

    if args.limit is not None:
        print(f"\n** LIMITED RUN: Processed {len(mappings)} of {original_count} total courses **")

    print(f"\nOutput files created in: {OUTPUT_DIR}")
    print(f"  - {csv_path.name}")
    print(f"  - {json_path.name}")
    print(f"  - {summary_path.name}")

    # Print confidence distribution
    df = pd.DataFrame(mappings)
    print("\nConfidence Distribution:")
    for conf in range(5, 0, -1):
        count = len(df[df['confidence_level'] == conf])
        pct = count / len(df) * 100
        print(f"  Confidence {conf}: {count} courses ({pct:.1f}%)")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
