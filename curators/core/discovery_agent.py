"""
Discovery Agent - Phase B: Autonomous Source Analysis

Uses LLM to analyze data sources and determine optimal extraction strategies.
"""

import httpx
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from rich.console import Console
from datetime import datetime

from core.memory import TieredMemoryManager

console = Console()


class DiscoveryAgent:
    """
    Analyzes data sources autonomously using LLM.

    Instead of manually inspecting HTML/APIs, this agent:
    - Fetches the source
    - Uses LLM to understand structure
    - Determines optimal extraction strategy
    - Generates structured discovery report
    """

    def __init__(self, llm, memory: TieredMemoryManager):
        """
        Initialize discovery agent.

        Args:
            llm: Language model for analysis
            memory: Memory manager for storing findings
        """
        self.llm = llm
        self.memory = memory
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; CuratorBot/1.0)"
            }
        )

    async def analyze_source(self, url: str) -> Dict[str, Any]:
        """
        Analyze a data source and generate discovery report.

        Args:
            url: URL to analyze

        Returns:
            Structured discovery report
        """
        console.print(f"[cyan]Analyzing source: {url}[/cyan]\n")

        # 1. Fetch the source
        console.print("[dim]Fetching source...[/dim]")
        content = await self._fetch_source(url)
        console.print(f"[dim]Fetched {len(content)} bytes[/dim]\n")

        # 2. Determine content type
        content_type = await self._determine_content_type(content)
        console.print(f"[dim]Content type: {content_type}[/dim]")

        # 3. Extract sample data for LLM analysis
        sample = await self._extract_sample(content, content_type)

        # 4. Analyze with LLM
        console.print("[dim]Analyzing with LLM...[/dim]")
        analysis = await self._llm_analyze(url, sample, content_type)

        # 5. Build discovery report
        report = {
            "url": url,
            "analyzed_at": datetime.now().isoformat(),
            "content_type": content_type,
            "analysis": analysis,
            "sample_data": sample[:2000] if len(sample) > 2000 else sample  # Truncate for storage
        }

        # 6. Store in memory (importance 0.7 - strategic)
        report_text = f"Discovery report for {url}: {analysis.get('source_type', 'unknown')} using {analysis.get('extraction_strategy', 'unknown')}"
        self.memory.add(
            content=report_text,
            category="strategy",  # Strategic importance 0.7
            metadata={
                "source_url": url,
                "analysis": analysis
            }
        )

        console.print("[green]✅ Analysis complete[/green]\n")

        return report

    async def _fetch_source(self, url: str) -> str:
        """Fetch content from URL."""
        response = await self.http_client.get(url)
        response.raise_for_status()
        return response.text

    async def _determine_content_type(self, content: str) -> str:
        """Determine if content is HTML, JSON, XML, etc."""
        content_clean = content.strip()

        if content_clean.startswith("{") or content_clean.startswith("["):
            return "json"
        elif content_clean.startswith("<!DOCTYPE") or content_clean.startswith("<html"):
            return "html"
        elif content_clean.startswith("<?xml"):
            return "xml"
        else:
            return "unknown"

    async def _extract_sample(self, content: str, content_type: str) -> str:
        """Extract a representative sample for LLM analysis."""

        if content_type == "html":
            # Parse HTML and extract meaningful structure
            soup = BeautifulSoup(content, "html.parser")

            # Get page title
            title = soup.find("title")
            title_text = title.get_text() if title else "No title"

            # Find potential product listings
            articles = soup.find_all("article", limit=3)
            divs = soup.find_all("div", class_=lambda x: x and "product" in x.lower(), limit=3)

            sample_html = f"<title>{title_text}</title>\n\n"

            if articles:
                sample_html += "<!-- Sample article elements -->\n"
                for article in articles[:2]:
                    sample_html += str(article)[:500] + "\n...\n\n"

            if divs:
                sample_html += "<!-- Sample product divs -->\n"
                for div in divs[:2]:
                    sample_html += str(div)[:500] + "\n...\n\n"

            return sample_html

        elif content_type == "json":
            # Return first 2000 chars of JSON
            return content[:2000]

        else:
            return content[:2000]

    async def _llm_analyze(self, url: str, sample: str, content_type: str) -> Dict[str, Any]:
        """
        Use LLM to analyze the sample and determine extraction strategy.

        This is where the magic happens - LLM understands the structure.
        """

        prompt = f"""Analyze this data source and provide a structured extraction strategy.

SOURCE URL: {url}
CONTENT TYPE: {content_type}

SAMPLE DATA:
{sample}

Please analyze and provide a JSON response with:
1. source_type: "web_page", "api", or "feed"
2. technology: What platform/framework (e.g., "bigcommerce", "shopify", "custom")
3. structure: What kind of data (e.g., "product_listing", "catalog", "api_response")
4. data_available: Object with boolean fields for what data is present:
   - products
   - prices
   - images
   - descriptions
   - categories
   - stock_status
5. extraction_strategy: "html_scraping", "json_parsing", or "api_calls"
6. selectors: If HTML, provide CSS selectors for key elements:
   - product_container: Main container for each product
   - name: Product name element
   - price: Price element
   - image: Image element
   - url: Link to product page
7. pagination: Object with:
   - available: boolean
   - pattern: URL pattern if available (e.g., "?page={{n}}")
   - max_estimate: Estimated number of pages
8. recommendations: Array of string recommendations for extraction

Respond ONLY with valid JSON, no explanatory text.
"""

        # Invoke LLM
        response = await self.llm.ainvoke(prompt)

        # Extract JSON from response
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Try to parse as JSON
        import json
        try:
            # Sometimes LLM wraps JSON in markdown code blocks
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_text = response_text.strip()

            analysis = json.loads(json_text)
            return analysis

        except json.JSONDecodeError as e:
            console.print(f"[yellow]Warning: Could not parse LLM response as JSON: {e}[/yellow]")
            console.print(f"[dim]Response: {response_text[:500]}[/dim]")

            # Return a basic structure
            return {
                "source_type": "web_page",
                "technology": "unknown",
                "structure": "product_listing",
                "data_available": {
                    "products": True,
                    "prices": True,
                    "images": True
                },
                "extraction_strategy": "html_scraping",
                "selectors": {},
                "pagination": {"available": False},
                "recommendations": ["Manual inspection needed"],
                "error": f"LLM response parsing failed: {str(e)}"
            }

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
