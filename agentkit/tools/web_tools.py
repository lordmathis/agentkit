import asyncio
import logging
import re
import time

import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS
from markdownify import markdownify as md

from agentkit.tools.toolset_handler import ToolSetHandler, tool

logger = logging.getLogger(__name__)


class WebTools(ToolSetHandler):
    def __init__(self, max_results: int = 10, rate_limit: float | None = 1.0, **kwargs):
        """Initialize WebTools with HTTP client and DuckDuckGo search capabilities.

        Args:
            max_results: Maximum number of search results to return (default: 10)
            rate_limit: Maximum queries per second for web search. Set to None to disable (default: 1.0)
            **kwargs: Additional keyword arguments passed to the DDGS client
        """
        super().__init__(name="web_tools")
        self._client = None
        self.max_results = max_results
        self.rate_limit = rate_limit
        self._min_interval = 1.0 / rate_limit if rate_limit else 0.0
        self._last_request_time = 0.0
        self._ddgs = None
        self._ddgs_kwargs = kwargs
    
    async def initialize(self):
        """Set up HTTP client and DDGS client"""
        await super().initialize()
        self._client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AgentKit/1.0)"
            }
        )
        self._ddgs = DDGS(**self._ddgs_kwargs)
    
    async def cleanup(self):
        """Clean up HTTP client"""
        if self._client:
            await self._client.aclose()
    
    @tool(
        description="Fetch a web page and convert it to markdown format",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch"
                },
                "include_links": {
                    "type": "boolean",
                    "description": "Whether to include links in the markdown output",
                    "default": True
                },
                "include_images": {
                    "type": "boolean",
                    "description": "Whether to include image references in the markdown output",
                    "default": False
                }
            },
            "required": ["url"]
        }
    )
    async def fetch_page(
        self, 
        url: str, 
        include_links: bool = True,
        include_images: bool = False
    ) -> str:
        """Fetch a web page and convert HTML to clean markdown"""
        try:
            logger.info(f"Fetching URL: {url}")
            response = await self._client.get(url)
            response.raise_for_status()
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            # Remove comments
            for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
                comment.extract()
            
            # Get the main content (try to find article/main tags first)
            main_content = (
                soup.find('article') or 
                soup.find('main') or 
                soup.find('div', class_=lambda c: c and 'content' in c.lower()) or
                soup.body or 
                soup
            )
            
            # Convert to markdown
            markdown_text = md(
                str(main_content),
                heading_style="ATX",
                bullets="-",
                strip=['a'] if not include_links else [],
                escape_asterisks=False,
                escape_underscores=False,
            )
            
            # Clean up the markdown
            markdown_text = self._clean_markdown(markdown_text)
            
            # Optionally remove images
            if not include_images:
                markdown_text = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_text)
            
            result = f"# Content from {url}\n\n{markdown_text}"
            
            logger.info(f"Successfully fetched and converted {url} ({len(markdown_text)} characters)")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            return f"Error fetching URL: {str(e)}"
        except Exception as e:
            logger.error(f"Error processing {url}: {e}", exc_info=True)
            return f"Error processing page: {str(e)}"
    
    @tool(
        description="Fetch multiple web pages and return their content as markdown",
        parameters={
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to fetch"
                }
            },
            "required": ["urls"]
        }
    )
    async def fetch_multiple_pages(self, urls: list[str]) -> dict:
        """Fetch multiple pages concurrently"""
        results = {}
        tasks = [self.fetch_page(url) for url in urls]
        
        # Fetch all pages concurrently
        contents = await asyncio.gather(*tasks, return_exceptions=True)
        
        for url, content in zip(urls, contents):
            if isinstance(content, Exception):
                results[url] = f"Error: {str(content)}"
            else:
                results[url] = content
        
        return results
    
    @tool(
        description="Performs a DuckDuckGo web search based on your query (think a Google search) then returns the top search results.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to perform."
                }
            },
            "required": ["query"]
        }
    )
    async def web_search(self, query: str) -> str:
        """Perform a DuckDuckGo web search and return formatted results"""
        try:
            # Enforce rate limiting
            await self._enforce_rate_limit()

            logger.info(f"Performing web search for: {query}")

            # Run synchronous DDGS call in executor to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self._ddgs.text(query, max_results=self.max_results)
            )

            if not results or len(results) == 0:
                return "No results found! Try a less restrictive/shorter query."

            # Format results as markdown
            postprocessed_results = [
                f"[{result['title']}]({result['href']})\n{result['body']}"
                for result in results
            ]

            result_text = "## Search Results\n\n" + "\n\n".join(postprocessed_results)
            logger.info(f"Search completed with {len(results)} results")

            return result_text

        except Exception as e:
            logger.error(f"Error performing web search: {e}", exc_info=True)
            return f"Error performing search: {str(e)}"

    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests"""
        # No rate limit enforced
        if not self.rate_limit:
            return

        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _clean_markdown(self, text: str) -> str:
        """Clean up markdown text"""
        # Remove excessive newlines (more than 2)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove leading/trailing whitespace from each line
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)

        # Remove empty list items
        text = re.sub(r'\n[-*+]\s*\n', '\n', text)

        return text.strip()