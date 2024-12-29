import argparse
import hashlib
import sqlite3
from enum import StrEnum
from pathlib import Path
from typing import Optional, Tuple

from scholarly import Publication, scholarly


class CitationStyles(StrEnum):
    BIBTEX = "bibtex"


def setup_argparse():
    parser = argparse.ArgumentParser(
        prog="citescholar",
        description="Get citations from Google Scholar and optionally save to SQLite3 database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m citescholar -t "Machine Learning" -c apa
    python -m citescholar -t "Neural Networks" --no-save
    python -m citescholar -t "Deep Learning" -s citations.db
        """,
    )

    # Required title argument
    parser.add_argument(
        "-t",
        "--title",
        required=True,
        help="Title of the paper to search for",
        type=str,
    )

    # Optional citation style
    parser.add_argument(
        "-c",
        "--citation-style",
        default="bibtex",
        choices=["bibtex"],
        help="Citation style (default: bibtex)",
    )

    # Database options group
    db_group = parser.add_mutually_exclusive_group()

    db_group.add_argument(
        "--no-save", action="store_true", help="Do not save the citation to database"
    )

    db_group.add_argument(
        "-s",
        "--sqlite3",
        help="SQLite3 database file path",
        type=str,
        default="citations.db",
    )

    return parser


def setup_database(db_name="citations.sqlite"):
    """
    Set up SQLite database with citations table if it doesn't exist.

    Args:
        db_name (str): Name of database file, defaults to citations.sqlite

    Returns:
        sqlite3.Connection: Database connection object
    """
    db_path = Path(db_name)

    # Create database connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table if it doesn't exist
    create_table_sql = """
   CREATE TABLE IF NOT EXISTS citations (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       title TEXT NOT NULL,
       citation TEXT NOT NULL,
       citation_hash TEXT NOT NULL UNIQUE,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   """

    cursor.execute(create_table_sql)
    conn.commit()

    return conn


def generate_citation_hash(title: str, citation: str) -> str:
    """
    Generate a unique hash for a citation based on title and citation text.

    Args:
        title (str): Paper title
        citation (str): Citation text

    Returns:
        str: SHA-256 hash of the citation
    """
    hash_content = f"{title}{citation}".encode("utf-8")
    return hashlib.sha256(hash_content).hexdigest()


def get_paper_from_title(
    title: str, citation_style: CitationStyles = CitationStyles.BIBTEX
) -> Optional[Tuple[str, str]]:
    """
    Search for a paper on Google Scholar and interactively confirm the correct one.

    Args:
        title (str): Title to search for
        citation_style (CitationStyles): Citation style for the output

    Returns:
        Optional[Tuple[str, str]]: Tuple of (title, bibtex) if paper is found and confirmed,
                                  None if no paper is found or search is cancelled
    """
    try:
        # Get search query generator
        search_query = scholarly.search_pubs(title)

        while True:
            try:
                # Get next paper from search results
                paper: Publication = next(search_query)

                paper = scholarly.fill(paper)

                if paper is False:
                    print("Paper could not be filled successfully")
                    return None

                # Print paper details
                print("\nFound paper:")
                scholarly.pprint(paper)
                bibtex = scholarly.bibtex(paper)
                print("\nBibTeX citation:")
                print(bibtex)

                # Ask for confirmation
                response = (
                    input("\nIs this the correct paper? ([y]/n): ").lower().strip()
                )

                if response == "y" or response == "":
                    return paper["bib"]["title"], bibtex

                elif response != "n":
                    print("Invalid input. Please enter 'y' or 'n'.")
                    continue

                # If 'n', loop continues to next paper

            except StopIteration:
                print("\nNo more papers found matching the search criteria.")
                return None

    except Exception as e:
        print(f"An error occurred while searching: {e}")
        return None


def add_citation_to_db(conn: sqlite3.Connection, title: str, citation: str) -> bool:
    """
    Add a citation to the database if it doesn't exist.

    Args:
        conn: Database connection
        title: Paper title
        citation: BibTeX citation

    Returns:
        bool: True if citation was added, False if it already exists
    """
    try:
        cursor = conn.cursor()
        citation_hash = generate_citation_hash(title, citation)

        # Check if citation already exists
        cursor.execute(
            "SELECT id FROM citations WHERE citation_hash = ?", (citation_hash,)
        )
        if cursor.fetchone():
            print("This citation already exists in the database.")
            return False

        # Insert new citation
        cursor.execute(
            """
            INSERT INTO citations (title, citation, citation_hash)
            VALUES (?, ?, ?)
        """,
            (title, citation, citation_hash),
        )

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        return False


def main():
    parser = setup_argparse()
    args = parser.parse_args()

    # Example usage of the arguments
    print(f"Paper title: {args.title}")
    print(f"Citation style: {args.citation_style}")
    print(f"Save to database: {not args.no_save}")
    if not args.no_save:
        print(f"Database file: {args.sqlite3}")

    try:
        conn = setup_database()
        print("Database setup successful!")
        res = get_paper_from_title(args.title)

        if res is None:
            print("No result bye.")
            return

        if add_citation_to_db(conn, res[0], res[1]):
            print("Citation successfully added to database.")

        conn.close()
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
