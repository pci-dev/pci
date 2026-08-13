from typing import Any

import requests
import time
import unicodedata
from datetime import datetime
from gluon.html import PRE
from gluon.contrib.appconfig import AppConfig  # type: ignore

myconf = AppConfig()
contact = myconf.take("contacts.managers")

BASE_URL = "https://api.openalex.org"
YEARS_BACK = 4
CURRENT_YEAR = datetime.now().year
MIN_YEAR = CURRENT_YEAR - YEARS_BACK


def get_json(url, params=None, sleep=0.1):
    """Send a GET request to OpenAlex and return the JSON response."""
    if params is None:
        params = {}

    # Copy the dictionary so that the caller's object is not modified.
    params = params.copy()
    params["mailto"] = contact

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        time.sleep(sleep)
        return response.json()

    except requests.RequestException as error:
        print(f"API error: {error}")
        return {}


def short_openalex_id(openalex_url):
    """Extract an OpenAlex entity ID, such as A1234, from its URL."""
    if not openalex_url:
        return None

    return openalex_url.rstrip("/").split("/")[-1]


def normalize_person_name(name):
    """
    Normalize a person's name for comparisons.

    The comparison is:
    - case-insensitive;
    - accent-insensitive;
    - insensitive to repeated spaces;
    - insensitive to dots, commas and hyphens.
    """
    if not name:
        return ""

    normalized = unicodedata.normalize("NFKD", name)
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )

    for character in ".,-_":
        normalized = normalized.replace(character, " ")

    return " ".join(normalized.casefold().split())


def search_authors_by_name(name, limit=5):
    """
    Search OpenAlex author profiles matching a name.

    Several profiles are retained because one name may correspond to
    multiple OpenAlex authors.
    """
    url = f"{BASE_URL}/authors"

    data = get_json(url, {"search": name, "per-page": limit})

    results = []

    for author in data.get("results", []):
        results.append(
            {
                "id": short_openalex_id(author.get("id")),
                "name": author.get("display_name"),
                "works_count": author.get("works_count"),
                "orcid": author.get("orcid"),
            }
        )

    return results


def get_recent_works_by_author(author_id):
    """Retrieve all works by an OpenAlex author during the analysis period."""
    url = f"{BASE_URL}/works"

    params = {
        "filter": (
            f"authorships.author.id:{author_id},publication_year:>{MIN_YEAR - 1}"
        ),
        "per-page": 200,
        "cursor": "*",
        "select": "id,doi,title,publication_year,authorships",
    }

    works = []

    while True:
        data = get_json(url, params)

        if not data:
            break

        works.extend(data.get("results", []))

        next_cursor = data.get("meta", {}).get("next_cursor")

        if not next_cursor:
            break

        params["cursor"] = next_cursor

    return works


def extract_author_ids_from_work(work):
    """Return all OpenAlex author IDs associated with a work."""
    author_ids = set()

    for authorship in work.get("authorships", []):
        author = authorship.get("author", {})
        author_id = short_openalex_id(author.get("id"))

        if author_id:
            author_ids.add(author_id)

    return author_ids


def work_url(work):
    """Return the DOI URL when available, otherwise the OpenAlex URL."""
    if work.get("doi"):
        return work["doi"]

    return work.get("id")


def build_profile_dictionary(names):
    """Search OpenAlex profiles for every person in a list."""
    return {name: search_authors_by_name(name) for name in names}


def flatten_profiles(profile_dictionary):
    """
    Create a dictionary indexed by OpenAlex author ID.

    The searched name and the name matched by OpenAlex are both retained.
    """
    return {
        profile["id"]: {
            "searched_name": searched_name,
            "matched_name": profile["name"],
            "orcid": profile["orcid"],
            "works_count": profile["works_count"],
        }
        for searched_name, profiles in profile_dictionary.items()
        for profile in profiles
        if profile.get("id")
    }


def get_works_for_profiles(flat_profiles):
    """Retrieve recent works for every retained OpenAlex profile."""
    works_by_profile = {}

    for profile_id, profile_info in flat_profiles.items():
        searched_name = profile_info["searched_name"]
        matched_name = profile_info["matched_name"]

        print(
            f"Retrieving works for {searched_name} "
            f"(matched as {matched_name}, {profile_id})..."
        )

        works_by_profile[profile_id] = get_recent_works_by_author(profile_id)

    return works_by_profile


def detect_list_overlaps(
    authors: list[str], comparison_names: list[str], comparison_role: list[str]
) -> list[Any]:
    """Detect names explicitly present in both AUTHORS and another input list.

    Returns a list of dictionaries describing each overlap.
    """
    comparison_names_by_normalized_name = {
        normalize_person_name(name): name for name in comparison_names
    }

    overlaps: list[Any] = []

    for author_name in authors:
        normalized_author_name = normalize_person_name(author_name)

        if normalized_author_name in comparison_names_by_normalized_name:
            overlaps.append(
                {
                    "author_name": author_name,
                    "comparison_name": (
                        comparison_names_by_normalized_name[normalized_author_name]
                    ),
                    "role": comparison_role,
                },
            )

    return overlaps


def profiles_overlap(candidate_author_ids, comparison_id):
    """
    Return True when a comparison profile is one of the candidate OpenAlex
    profiles retained for the author.
    """
    return comparison_id in candidate_author_ids


def names_refer_to_same_person(author_name, comparison_name):
    """Compare two input names after normalization."""
    return normalize_person_name(author_name) == normalize_person_name(comparison_name)


def check_coauthorships(
    author_name,
    candidate_author_ids,
    comparison_role,
    comparison_profiles,
    comparison_works,
    all_author_ids,
):
    """
    Check whether an author has co-published with members of one group.

    A comparison is skipped when the author and the comparison person are
    the same person, based on either:
    - their normalized searched names;
    - an OpenAlex profile ID shared by both.
    """
    matches = []
    skipped_self_comparisons = []

    for comparison_id, works in comparison_works.items():
        comparison_info = comparison_profiles[comparison_id]
        comparison_searched_name = comparison_info["searched_name"]

        same_input_name = names_refer_to_same_person(
            author_name, comparison_searched_name
        )

        same_openalex_profile = profiles_overlap(candidate_author_ids, comparison_id)

        if same_input_name or same_openalex_profile:
            skipped_self_comparisons.append(
                {
                    "role": comparison_role,
                    "comparison_id": comparison_id,
                    "comparison_name": comparison_info["matched_name"],
                    "searched_comparison_name": comparison_searched_name,
                    "detected_by_name": same_input_name,
                    "detected_by_openalex_id": same_openalex_profile,
                }
            )

            # Do not compare an author with their own publications.
            continue

        for work in works:
            work_author_ids = extract_author_ids_from_work(work)
            common_ids = candidate_author_ids.intersection(work_author_ids)

            if not common_ids:
                continue

            matched_author_names = [
                all_author_ids[author_id]["matched_name"]
                for author_id in common_ids
                if author_id in all_author_ids
            ]

            matches.append(
                {
                    "role": comparison_role,
                    "comparison_id": comparison_id,
                    "comparison_name": comparison_info["matched_name"],
                    "searched_comparison_name": comparison_searched_name,
                    "matched_author_names": matched_author_names,
                    "work": work,
                }
            )

    return matches, skipped_self_comparisons


def print_self_comparison_alert(author_name, skipped_comparison):
    """Print an alert when an author would be compared with themselves."""
    detection_methods = []

    if skipped_comparison["detected_by_name"]:
        detection_methods.append("same normalized input name")

    if skipped_comparison["detected_by_openalex_id"]:
        detection_methods.append("shared OpenAlex profile ID")

    print()
    print("!" * 80)
    print("ALERT: AUTHOR ALSO PRESENT IN A COMPARISON LIST")
    print(f"Author: {author_name}")
    print(f"List: {skipped_comparison['role']}")
    print(f"Name in comparison list: {skipped_comparison['searched_comparison_name']}")
    print(f"OpenAlex profile matched as: {skipped_comparison['comparison_name']}")
    print(f"OpenAlex ID: {skipped_comparison['comparison_id']}")
    print(f"Detected by: {', '.join(detection_methods)}")
    print("Self-coauthorship analysis skipped for this pair.")
    print("Analysis with all other people continues normally.")
    print("!" * 80)


# -------------------------------------------------------------------------
# 1. Detect explicit overlaps between the input lists
# -------------------------------------------------------------------------


def query_semantic_api(
    authors: list[str], recommenders: list[str], sugg_reviewers: list[str]
) -> str:
    recommender_list_overlaps = detect_list_overlaps(
        authors, recommenders, "recommender"
    )

    reviewer_list_overlaps = detect_list_overlaps(
        authors, sugg_reviewers, "suggested reviewer"
    )

    all_list_overlaps = recommender_list_overlaps + reviewer_list_overlaps

    res = ""

    if all_list_overlaps:
        res += "\n" + "!" * 80 + "\n"
        res += "ALERT: IDENTICAL NAMES FOUND IN THE INPUT LISTS\n"

        for overlap in all_list_overlaps:
            res += f"- Author '{overlap['author_name']}' is also listed as {overlap['role']} under the name '{overlap['comparison_name']}'.\n"

        res += "Self-comparisons will be skipped, but all other comparisons will still be performed.\n"
        res += "!" * 80 + "\n"

    # -------------------------------------------------------------------------
    # 2. Search for candidate OpenAlex profiles
    # -------------------------------------------------------------------------

    author_profiles = build_profile_dictionary(authors)
    recommender_profiles = build_profile_dictionary(recommenders)
    reviewer_profiles = build_profile_dictionary(sugg_reviewers)

    # -------------------------------------------------------------------------
    # 3. Flatten candidate profiles by OpenAlex ID
    # -------------------------------------------------------------------------

    all_author_ids = flatten_profiles(author_profiles)
    all_recommender_ids = flatten_profiles(recommender_profiles)
    all_reviewer_ids = flatten_profiles(reviewer_profiles)

    # -------------------------------------------------------------------------
    # 4. Retrieve recent works of recommenders and suggested reviewers
    # -------------------------------------------------------------------------

    print("\nRetrieving recommender publications...")
    recommender_works = get_works_for_profiles(all_recommender_ids)

    print("\nRetrieving suggested-reviewer publications...")
    reviewer_works = get_works_for_profiles(all_reviewer_ids)

    # -------------------------------------------------------------------------
    # 5. Detect co-publications with both groups
    # -------------------------------------------------------------------------

    res += f"\nAnalysis period: {MIN_YEAR}–{CURRENT_YEAR}\n"

    for author_name in authors:
        res += "=" * 80 + "\n"
        res += f"Author: {author_name}\n"

        candidate_profiles = author_profiles.get(author_name, [])

        candidate_author_ids = {
            profile["id"] for profile in candidate_profiles if profile.get("id")
        }

        if not candidate_author_ids:
            res += "No OpenAlex profile found.\n"
            continue

        recommender_matches, skipped_recommender_self_comparisons = check_coauthorships(
            author_name=author_name,
            candidate_author_ids=candidate_author_ids,
            comparison_role="recommender",
            comparison_profiles=all_recommender_ids,
            comparison_works=recommender_works,
            all_author_ids=all_author_ids,
        )

        reviewer_matches, skipped_reviewer_self_comparisons = check_coauthorships(
            author_name=author_name,
            candidate_author_ids=candidate_author_ids,
            comparison_role="suggested reviewer",
            comparison_profiles=all_reviewer_ids,
            comparison_works=reviewer_works,
            all_author_ids=all_author_ids,
        )

        skipped_self_comparisons = (
            skipped_recommender_self_comparisons + skipped_reviewer_self_comparisons
        )

        # Display an alert for each self-comparison that was skipped.
        for skipped_comparison in skipped_self_comparisons:
            print_self_comparison_alert(author_name, skipped_comparison)

        all_matches = recommender_matches + reviewer_matches

        if all_matches:
            for match in all_matches:
                work = match["work"]

                res += "\n"
                res += f"Co-publication found with {match['role']}: {match['comparison_name']}\n"
                res += f"{match['role'].capitalize()} searched as: {match['searched_comparison_name']}\n"

                res += (
                    "Matched author profile(s): "
                    + ", ".join(match["matched_author_names"])
                    + "\n"
                )
                res += f"Year: {work.get('publication_year')}\n"
                res += f"Title: {work.get('title')}\n"
                res += f"URL: {work_url(work)}\n"

        else:
            candidate_names = [
                profile["name"] for profile in candidate_profiles if profile.get("name")
            ]

            if skipped_self_comparisons:
                res += "\n"
                res += "No co-publication found with the other recommenders or suggested reviewers.\n"
            else:
                res += "No co-publication found with any recommender or suggested reviewer.\n"

            res += (
                "OpenAlex candidate profiles checked: "
                + ", ".join(candidate_names)
                + "\n"
            )

    return PRE(res)
