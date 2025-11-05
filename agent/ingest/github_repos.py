"""Scrape job listings from GitHub repositories."""

import re
import logging
from typing import Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from agent.config import settings
from agent.storage.models import ATSType

logger = logging.getLogger(__name__)


class GitHubJobScraper:
    """Scraper for job listings from GitHub markdown repositories."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

    def scrape_repo(self, repo: str) -> list[dict]:
        """
        Scrape job listings from a GitHub repository.

        Args:
            repo: Repository in format "owner/repo"

        Returns:
            List of job dictionaries
        """
        # Try different branches
        branches = ["main", "master"]

        for branch in branches:
            try:
                url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
                logger.info(f"Fetching jobs from {repo} ({branch})")

                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                jobs = self._parse_markdown(response.text, repo)
                logger.info(f"Found {len(jobs)} jobs in {repo}")

                return jobs

            except Exception as e:
                logger.debug(f"Failed to fetch from {repo} ({branch}): {e}")
                continue

        logger.error(f"Error scraping {repo}: Could not find README.md in any branch")
        return []

    def _parse_markdown(self, markdown: str, repo: str) -> list[dict]:
        """
        Parse job listings from markdown table.

        Supports both pure markdown tables and HTML tables embedded in markdown.
        Expected format:
        | Company | Role | Location | Application/Link | Date Posted |
        """
        jobs = []

        # First try to parse as HTML table (handles SimplifyJobs format)
        html_jobs = self._parse_html_table(markdown, repo)
        if html_jobs:
            return html_jobs

        # Fall back to markdown table parsing
        lines = markdown.split("\n")

        # Find table rows
        in_table = False
        for line in lines:
            # Skip header and separator rows
            if "|" not in line:
                continue

            if "Company" in line or "---" in line:
                in_table = True
                continue

            if not in_table:
                continue

            # Parse table row
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            if len(cells) < 3:
                continue

            job = self._extract_job_from_row(cells, repo)
            if job:
                jobs.append(job)

        return jobs

    def _parse_html_table(self, markdown: str, repo: str) -> list[dict]:
        """
        Parse HTML tables embedded in markdown (e.g., SimplifyJobs format).

        Returns empty list if no HTML tables found.
        """
        try:
            soup = BeautifulSoup(markdown, 'html.parser')
            tables = soup.find_all('table')

            if not tables:
                return []

            jobs = []
            for table in tables:
                rows = table.find_all('tr')

                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 3:
                        continue

                    # Extract text from each cell
                    cell_texts = []
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        cell_texts.append(text)

                    # Skip header rows
                    if any(header in cell_texts[0].lower() for header in ['company', 'position', 'role']):
                        continue

                    job = self._extract_job_from_row(cell_texts, repo, html_cells=cells)
                    if job:
                        jobs.append(job)

            return jobs
        except Exception as e:
            logger.debug(f"Failed to parse HTML table: {e}")
            return []

    def _extract_job_from_row(self, cells: list[str], repo: str, html_cells: list = None) -> Optional[dict]:
        """Extract job information from table row cells.

        Args:
            cells: List of cell text content
            repo: Repository name
            html_cells: Optional list of BeautifulSoup cell objects (for extracting links)
        """
        try:
            # Common patterns for job listing tables
            # Format 1: | Company | Role | Location | Link | Date |
            # Format 2: | Company | Role | Location | Link |
            # Format 3: | Company | Position | Location | Application |

            company = cells[0].strip()
            title = cells[1].strip() if len(cells) > 1 else ""
            location = cells[2].strip() if len(cells) > 2 else ""

            # Extract URL from markdown link or plain URL
            url = None
            for cell in cells:
                # Try markdown link format first: [text](url)
                match = re.search(r'\[.*?\]\((https?://[^\)]+)\)', cell)
                if match:
                    url = match.group(1)
                    break

                # Try plain URL format (for HTML-parsed content)
                match = re.search(r'(https?://[^\s<>"\']+)', cell)
                if match:
                    url = match.group(1)
                    break

            # If no URL found in text, check HTML cells for links (SimplifyJobs format)
            if not url and html_cells:
                for cell in html_cells:
                    link = cell.find('a')
                    if link and link.get('href'):
                        href = link.get('href')
                        # Extract actual job URL (skip simplify.jobs tracking links)
                        if 'job-boards' in href or 'lever.co' in href or 'workday' in href or 'greenhouse.io' in href or 'ashby' in href:
                            url = href
                            break

            # Skip if no URL found
            if not url or not company or not title:
                return None

            # Detect ATS type from URL
            ats_type = self._detect_ats_type(url)

            # Detect remote work
            remote = any(
                keyword in location.lower()
                for keyword in ["remote", "anywhere", "worldwide"]
            )

            # Extract date if present
            posted_date = None
            if len(cells) > 4:
                posted_date = self._parse_date(cells[4])

            # Clean up markdown formatting
            company = self._clean_text(company)
            title = self._clean_text(title)
            location = self._clean_text(location)

            return {
                "title": title,
                "company": company,
                "location": location,
                "remote": remote,
                "url": url,
                "ats_type": ats_type,
                "source": f"github:{repo}",
                "posted_date": posted_date,
            }

        except Exception as e:
            logger.debug(f"Error parsing row: {e}")
            return None

    def _detect_ats_type(self, url: str) -> ATSType:
        """Detect ATS system from job URL."""
        url_lower = url.lower()

        if "greenhouse.io" in url_lower:
            return ATSType.GREENHOUSE
        elif "lever.co" in url_lower:
            return ATSType.LEVER
        elif "workday" in url_lower or "myworkday" in url_lower:
            return ATSType.WORKDAY
        elif "ashbyhq.com" in url_lower:
            return ATSType.ASHBY
        else:
            return ATSType.UNKNOWN

    def _clean_text(self, text: str) -> str:
        """Remove markdown formatting from text."""
        # Remove links [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Remove bold/italic markers
        text = re.sub(r'[*_]+', '', text)
        # Remove common special characters
        text = re.sub(r'[^\w\s\-.,&()]', '', text)
        return text.strip()

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime."""
        try:
            # Common date formats in job repos
            date_str = self._clean_text(date_str)

            # Try parsing common formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%b %d, %Y"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            return None
        except Exception:
            return None

    def scrape_all_repos(self) -> list[dict]:
        """Scrape all configured GitHub repositories."""
        all_jobs = []

        for repo in settings.github_repos:
            jobs = self.scrape_repo(repo)
            all_jobs.extend(jobs)

        logger.info(f"Total jobs scraped: {len(all_jobs)}")
        return all_jobs
