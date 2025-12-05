import pandas as pd
import requests
import time

# -------------------------
# Your OMDb API key (you provided)
OMDB_API_KEY = "9021e573"
# -------------------------

# IMDb dataset URLs (official)
BASICS_URL = "https://datasets.imdbws.com/title.basics.tsv.gz"
RATINGS_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
CREW_URL = "https://datasets.imdbws.com/title.crew.tsv.gz"
NAMES_URL = "https://datasets.imdbws.com/name.basics.tsv.gz"
PRINCIPALS_URL = "https://datasets.imdbws.com/title.principals.tsv.gz"


def download_datasets():
    print("📥 Downloading IMDb datasets (basics, ratings, crew, names, principals)...")
    basics = pd.read_csv(BASICS_URL, sep="\t", dtype=str, compression="gzip")
    ratings = pd.read_csv(RATINGS_URL, sep="\t", dtype=str, compression="gzip")
    crew = pd.read_csv(CREW_URL, sep="\t", dtype=str, compression="gzip")
    names = pd.read_csv(NAMES_URL, sep="\t", dtype=str, compression="gzip")
    principals = pd.read_csv(PRINCIPALS_URL, sep="\t", dtype=str, compression="gzip")
    print("✔ IMDb datasets downloaded.")
    return basics, ratings, crew, names, principals


def build_top_250(basics: pd.DataFrame, ratings: pd.DataFrame):
    print("🔍 Filtering to movies and building Top 250 based on rating + votes...")

    # Keep only titleType == movie
    movies = basics[basics["titleType"] == "movie"].copy()

    # Merge with ratings
    merged = movies.merge(ratings, on="tconst", how="inner")

    # Convert rating and votes to numeric for sorting
    merged["averageRating"] = pd.to_numeric(merged["averageRating"], errors="coerce")
    merged["numVotes"] = pd.to_numeric(merged["numVotes"], errors="coerce")

    # Sort by rating (desc), then votes (desc)
    merged = merged.sort_values(by=["averageRating", "numVotes"], ascending=False)

    # Take top 250
    top250 = merged.head(250).copy()
    print(f"✔ Top 250 assembled (rows = {len(top250)}).")
    return top250


def map_directors(top250: pd.DataFrame, crew: pd.DataFrame, names: pd.DataFrame):
    print("🎬 Mapping directors from crew + name datasets...")

    # Merge directors column from crew
    crew_small = crew[["tconst", "directors"]].copy()
    top = top250.merge(crew_small, on="tconst", how="left")

    # Prepare names map
    names_map = names.set_index("nconst")["primaryName"].to_dict()

    def director_names(directors_field):
        if pd.isna(directors_field):
            return "N/A"
        ids = directors_field.split(",")
        return ", ".join(names_map.get(i, "N/A") for i in ids)

    top["Director"] = top["directors"].apply(director_names)
    top.drop(columns=["directors"], inplace=True, errors="ignore")
    return top


def map_top_actors(top250: pd.DataFrame, principals: pd.DataFrame, names: pd.DataFrame, top_n=3):
    print(f"🎭 Mapping top {top_n} actors using principals + names datasets...")

    # Filter principals to only those entries that are in our top250 set
    principals_small = principals[principals["tconst"].isin(top250["tconst"])].copy()

    # Convert ordering to numeric for correct sorting (some values may be missing)
    principals_small["ordering"] = pd.to_numeric(principals_small.get("ordering", None), errors="coerce")

    # Keep actor/actress entries primarily (but include other categories if needed)
    # We'll consider categories 'actor' and 'actress' first, fallback to any if none found.
    actors_mask = principals_small["category"].isin(["actor", "actress"])
    actors_only = principals_small[actors_mask].copy()

    # Group by tconst, order by ordering, pick top N actor nconsts
    top_actors = {}
    names_map = names.set_index("nconst")["primaryName"].to_dict()

    for tconst, group in actors_only.groupby("tconst"):
        group_sorted = group.sort_values(by="ordering", na_position="last")
        nconsts = group_sorted["nconst"].dropna().tolist()[:top_n]
        actor_names = [names_map.get(n, "N/A") for n in nconsts]
        top_actors[tconst] = ", ".join(actor_names) if actor_names else "N/A"

    # For any movie missing actors from actors_only (maybe none), fallback to principals (any category)
    for tconst, group in principals_small.groupby("tconst"):
        if tconst in top_actors:
            continue
        group_sorted = group.sort_values(by="ordering", na_position="last")
        nconsts = group_sorted["nconst"].dropna().tolist()[:top_n]
        actor_names = [names_map.get(n, "N/A") for n in nconsts]
        top_actors[tconst] = ", ".join(actor_names) if actor_names else "N/A"

    # Map into DataFrame column aligned with top250 index
    top250["Main_Actors"] = top250["tconst"].apply(lambda x: top_actors.get(x, "N/A"))
    return top250


def add_runtime_and_clean(top250: pd.DataFrame):
    print("⏱ Adding runtime (from basics) and cleaning columns...")

    # runtimeMinutes is already in basics and should be present in top250
    # Some entries may have '\N' or NaN; we handle that
    top250["runtimeMinutes"] = top250.get("runtimeMinutes", pd.NA)
    top250["Runtime"] = top250["runtimeMinutes"].replace("\\N", pd.NA)
    # If runtime is numeric string, keep, else N/A
    top250["Runtime"] = pd.to_numeric(top250["Runtime"], errors="coerce")
    top250["Runtime"] = top250["Runtime"].apply(lambda x: f"{int(x)} min" if pd.notna(x) else "N/A")

    return top250


def fetch_plot_and_poster(top250: pd.DataFrame, api_key: str, sleep_between=0.25):
    print("🛰 Fetching Plot and Poster URL from OMDb API (this uses your API key)...")
    base = "http://www.omdbapi.com/"
    plots = []
    posters = []

    for idx, row in top250.iterrows():
        imdb_id = row["tconst"]  # IMDb ID like tt0111161
        params = {"i": imdb_id, "apikey": api_key, "plot": "short", "r": "json"}
        try:
            resp = requests.get(base, params=params, timeout=10)
            data = resp.json()
            plot = data.get("Plot", "N/A") if data.get("Response", "True") != "False" else "N/A"
            poster = data.get("Poster", "N/A") if data.get("Response", "True") != "False" else "N/A"
        except Exception as e:
            plot = "N/A"
            poster = "N/A"
        plots.append(plot)
        posters.append(poster)
        time.sleep(sleep_between)  # be polite

    top250["Plot"] = plots
    top250["Poster_URL"] = posters
    return top250


def finalize_and_save(top250: pd.DataFrame):
    # Select and rename columns for final output
    final = top250.rename(columns={
        "tconst": "IMDb_ID",
        "primaryTitle": "Title",
        "startYear": "Year",
        "genres": "Genre",
        "averageRating": "IMDb_Rating",
        "numVotes": "Votes"
    })

    # Keep desired columns and their order
    final = final[[
        "IMDb_ID", "Title", "Year", "Genre", "IMDb_Rating", "Votes",
        "Director", "Main_Actors", "Runtime", "Plot", "Poster_URL"
    ]]

    # Save CSV
    final.to_csv("IMDb_Top_250_With_Details.csv", index=False)
    print("\n🎉 DONE — Saved file: IMDb_Top_250_With_Details.csv")
    return final


def main():
    basics, ratings, crew, names, principals = download_datasets()
    top250 = build_top_250(basics, ratings)

    # top250 currently contains the basic columns from 'basics' merged with ratings
    # Merge runtime (runtimeMinutes) from basics (it's already present because we used basics)
    # Map directors
    top250 = map_directors(top250, crew, names)

    # Map main actors (top 3)
    top250 = map_top_actors(top250, principals, names, top_n=3)

    # Add runtime and clean
    top250 = add_runtime_and_clean(top250)

    # Fetch plot and poster from OMDb
    top250 = fetch_plot_and_poster(top250, OMDB_API_KEY, sleep_between=0.25)

    # Finalize and save
    final_df = finalize_and_save(top250)
    print("\nAll done. Total rows:", len(final_df))


if __name__ == "__main__":
    main()
