import re
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ncleg.gov"
TOC_URL = "https://www.ncleg.gov/Laws/GeneralStatutesTOC"
CHAPTER_PATTERN = r"Chapter_(\d+[A-Z]?)\.html"
SECTION_PATTERN = r"§§?\s*([\w\.-]+(?:\s*through\s*[\w\.-]+)?)[:\.]"
ARTICLE_PATTERN = r"Article\s+(\d+[A-Z]?)"

# CSS Classes for parsing statute HTML
CSS_CLASSES = {
    "chapter_title": "cs2E44D3A6",  # h3.cs2E44D3A6
    "subchapter_title": "cs2E86D3A6",  # h4.cs2E86D3A6
    "article_title": "cs2E44D3A6",  # p.cs2E44D3A6
    "article_part": "cs2E86D3A6",  # h6.cs2E86D3A6
    "section_title": "cs8E357F70",  # p.cs8E357F70
    "section_text": ["cs4817DA29", "cs10EB6B29"],  # p.cs4817DA29 and p.cs10EB6B29
}


@dataclass
class StatuteSection:
    """Represents a statute section with all its metadata."""

    chapter: str
    article: str
    article_number: Optional[str]
    section_number: Optional[str]
    text: str = ""

    def add_text(self, new_text: str) -> None:
        """Add text content to the section."""
        if self.text:
            self.text += "\n" + new_text
        else:
            self.text = new_text

    def to_dict(self) -> dict:
        """Convert to dictionary for DataFrame creation."""
        return {
            "chapter": self.chapter,
            "article_number": self.article_number,
            "article": self.article,
            "section_number": self.section_number,
            "text": self.text,
        }


@dataclass
class ParserState:
    """Manages the state of the statute parser."""

    chapter_title: str
    current_article: str = ""
    current_article_number: Optional[str] = None
    current_section: Optional[StatuteSection] = None
    pending_article_number: Optional[str] = None
    records: list[StatuteSection] = None

    def __post_init__(self):
        if self.records is None:
            self.records = []

    def is_article_number(self, text: str) -> bool:
        """Check if text is an article number (e.g., 'Article 1.')."""
        return (
            text.startswith("Article ") and text.endswith(".") and re.search(ARTICLE_PATTERN, text)
        )

    def is_section_title(self, classes: list) -> bool:
        """Check if element is a section title."""
        return CSS_CLASSES["section_title"] in classes

    def is_section_text(self, classes: list) -> bool:
        """Check if element is section text content."""
        return any(cls in classes for cls in CSS_CLASSES["section_text"])

    def is_article_title_part(self, classes: list, text: str) -> bool:
        """Check if element is an article title part (not starting with 'Article')."""
        return (
            CSS_CLASSES["article_title"] in classes
            and not text.startswith("Article ")
            and not text.startswith("§")
        )

    def is_standalone_article(self, classes: list, text: str) -> bool:
        """Check if element is a standalone article (both number and title in one)."""
        return (
            CSS_CLASSES["article_title"] in classes
            and text.startswith("Article ")
            and not text.endswith(".")
        )

    def save_current_section(self) -> None:
        """Save the current section if it exists and has content."""
        if self.current_section and self.current_section.text:
            self.records.append(self.current_section)

    def process_article_number(self, text: str) -> None:
        """Process an article number element."""
        self.pending_article_number = text
        article_match = re.search(ARTICLE_PATTERN, text)
        self.current_article_number = article_match.group(1) if article_match else None

    def process_article_title_part(self, text: str) -> None:
        """Process an article title part that follows an article number."""
        if self.pending_article_number:
            full_article = f"{self.pending_article_number} {text}".strip()
            self.current_article = extract_article_title(full_article)
            self.pending_article_number = None

    def process_standalone_article(self, text: str) -> None:
        """Process a standalone article that contains both number and title."""
        self.current_article = extract_article_title(text)
        article_match = re.search(ARTICLE_PATTERN, text)
        self.current_article_number = article_match.group(1) if article_match else None
        self.pending_article_number = None

    def start_new_section(self, text: str) -> None:
        """Start a new section, saving the previous one first."""
        self.save_current_section()

        # Extract section number
        section_match = re.search(SECTION_PATTERN, text)
        section_num = section_match.group(1) if section_match else None

        # Create new section
        self.current_section = StatuteSection(
            chapter=self.chapter_title,
            article=self.current_article,
            article_number=self.current_article_number,
            section_number=section_num,
            text=text,
        )

    def add_section_content(self, text: str) -> None:
        """Add content to the current section."""
        if self.current_section:
            self.current_section.add_text(text)

    def get_records_as_dicts(self) -> list[dict]:
        """Get all records as dictionaries for DataFrame creation."""
        return [record.to_dict() for record in self.records]


def extract_chapter_title(full_title: str) -> str:
    """
    Extract just the title portion from a full chapter title.

    Args:
        full_title: Full chapter title like "Chapter 1. Civil Procedure."

    Returns:
        Just the title portion like "Civil Procedure"
    """
    # Remove "Chapter X." prefix using regex
    # Pattern matches "Chapter" followed by space, number/letter combo, period, and optional space
    cleaned = re.sub(r"^Chapter\s+\d+[A-Z]?\.\s*", "", full_title, flags=re.IGNORECASE)

    # Remove trailing period if present
    cleaned = cleaned.rstrip(".")

    return cleaned.strip()


def extract_article_title(full_title: str) -> str:
    """
    Extract just the title portion from a full article title.

    Args:
        full_title: Full article title like "Article 1. General Provisions."

    Returns:
        Just the title portion like "General Provisions"
    """
    # Remove "Article X." prefix using regex
    # Pattern matches "Article" followed by space, number/letter combo, period, and optional space
    cleaned = re.sub(r"^Article\s+\d+[A-Z]?\.\s*", "", full_title, flags=re.IGNORECASE)

    # Remove trailing period if present
    cleaned = cleaned.rstrip(".")

    return cleaned.strip()


def get_chapter_links() -> list[dict[str, str]]:
    """
    Fetch chapter links and titles from the NC General Statutes Table of Contents.

    Returns:
        List of dictionaries containing chapter URL, number, and title.
    """
    try:
        response = requests.get(TOC_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        chapters = []
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if "/EnactedLegislation/Statutes/HTML/ByChapter/Chapter_" in href and href.endswith(
                ".html"
            ):
                if match := re.search(CHAPTER_PATTERN, href):
                    chapter_num = match.group(1)
                    chapters.append(
                        {
                            "url": urljoin(BASE_URL, href),
                            "chapter_num": chapter_num,
                            "title": text or f"Chapter {chapter_num}",
                        }
                    )

        # Sort by numeric part of chapter number
        chapters.sort(key=lambda c: int(re.search(r"(\d+)", c["chapter_num"]).group(1)))
        return chapters

    except requests.RequestException as e:
        print(f"Error fetching table of contents: {e}")
        return []


def parse_statute_html(html: str) -> list[dict]:
    """Parse statute chapter HTML using dataclass-based state machine.

    Args:
        html: Raw HTML content of a statute chapter page.

    Returns:
        List of dictionaries containing parsed statute sections with metadata.
    """
    soup = BeautifulSoup(html, "lxml")

    # Extract chapter title
    chapter_elements = soup.select(f"h3.{CSS_CLASSES['chapter_title']}")
    full_chapter_title = " ".join(elem.get_text(" ", strip=True) for elem in chapter_elements)
    chapter_title = extract_chapter_title(full_chapter_title)

    # Initialize parser state
    state = ParserState(chapter_title=chapter_title)

    # Get all relevant elements in document order
    selectors = [
        f"p.{CSS_CLASSES['article_title']}",
        f"p.{CSS_CLASSES['section_title']}",
        f"p.{CSS_CLASSES['section_text'][0]}",
        f"p.{CSS_CLASSES['section_text'][1]}",
    ]
    all_elements = soup.select(", ".join(selectors))

    # State machine loop using dataclass methods
    for element in all_elements:
        text = element.get_text(" ", strip=True)
        classes = element.get("class", [])

        if not text:
            continue

        # State: Found article number (e.g., "Article 1.")
        if state.is_article_number(text):
            state.process_article_number(text)

        # State: Found article title part (follows article number)
        elif state.pending_article_number and state.is_article_title_part(classes, text):
            state.process_article_title_part(text)

        # State: Found section title - start new section
        elif state.is_section_title(classes):
            state.start_new_section(text)

        # State: Found section content - append to current section
        elif state.is_section_text(classes):
            state.add_section_content(text)

        # State: Found standalone article (both number and title in one element)
        elif state.is_standalone_article(classes, text):
            state.process_standalone_article(text)

    # Save the final section
    state.save_current_section()

    return state.get_records_as_dicts()


def parse_chapter(chapter_info: dict[str, str]) -> list[dict]:
    """Parse a single chapter into sections."""
    try:
        response = requests.get(chapter_info["url"], timeout=30)
        response.raise_for_status()
        sections = parse_statute_html(response.content)

        # Add chapter metadata to each section
        for section in sections:
            section.update(
                {
                    "chapter_number": chapter_info["chapter_num"],
                    "chapter_title": section.get("chapter", chapter_info["title"]),
                    "source_url": chapter_info["url"],
                }
            )
        return sections

    except requests.RequestException as e:
        print(f"Error fetching chapter {chapter_info['chapter_num']}: {e}")
        return []
    except Exception as e:
        print(f"Error parsing chapter {chapter_info['chapter_num']}: {e}")
        return []


def find_start_index(chapters: list[dict], start_chapter: int) -> int | None:
    """Find the index of the starting chapter."""
    for i, chapter in enumerate(chapters):
        if chapter["chapter_num"] == str(start_chapter):
            return i
    return None


def parse_all_chapters(start_chapter: int = 1, max_chapters: int | None = None) -> pd.DataFrame:
    """Parse all chapters into a DataFrame."""
    chapters = get_chapter_links()

    start_index = find_start_index(chapters, start_chapter)
    if start_index is None:
        print(f"Chapter {start_chapter} not found!")
        return pd.DataFrame()

    # Determine which chapters to parse
    end_index = start_index + max_chapters if max_chapters else len(chapters)
    chapters_to_parse = chapters[start_index:end_index]

    all_sections = []
    for i, chapter in enumerate(chapters_to_parse, start_index + 1):
        print(f"Parsing {i}/{len(chapters)}: Chapter {chapter['chapter_num']}")
        sections = parse_chapter(chapter)
        all_sections.extend(sections)
        time.sleep(0.5)  # Rate limiting

    return pd.DataFrame(
        all_sections,
        columns=[
            "chapter_number",
            "chapter_title",
            "article_number",
            "article",
            "section_number",
            "text",
            "source_url",
        ],
    )


def main():
    """Main function to download and save NC General Statutes."""
    import argparse

    parser = argparse.ArgumentParser(description="Download NC General Statutes")
    parser.add_argument("--start", type=int, default=1, help="Starting chapter number (default: 1)")
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Maximum number of chapters to download (default: None)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="input/nc_general_statutes.csv",
        help="Output CSV file (default: input/nc_general_statutes.csv)",
    )

    args = parser.parse_args()

    print(
        f"Downloading NC General Statutes (starting from chapter {args.start}, max {args.max if args.max else 'all'} chapters)..."
    )
    df = parse_all_chapters(start_chapter=args.start, max_chapters=args.max)

    if df.empty:
        print("No data found.")
        return

    # Display summary
    print(f"\nFound {len(df)} statute sections")
    print("\nSample data:")
    print(
        df[["chapter_number", "chapter_title", "article_number", "article", "section_number"]].head(
            10
        )
    )

    # Save to CSV
    df.to_csv(args.output, index=False)
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
