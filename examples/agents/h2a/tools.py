import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md


async def get_yahoo_finance_markdown() -> str:
    """
    Download content from Yahoo Finance homepage and return it as markdown string.

    Returns:
        str: Markdown formatted content from Yahoo Finance
    """
    url = "https://finance.yahoo.com/"

    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    headers = {"User-Agent": user_agent}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            main_container = soup.find(class_="mainContainer")

            if not main_container:
                return "Error: mainContainer not found on the page"

            for element in main_container(["script", "style", "noscript", "meta", "head"]):
                element.decompose()

            markdown_content = md(
                str(main_container),
                heading_style="ATX",
                bullets="-",
                strip=["script", "style", "meta", "head", "title"],
                autolinks=True,
                escape_misc=False,
                wrap=True,
                wrap_width=80,
            )

            return markdown_content

    except httpx.RequestError as e:
        return f"Error fetching content: {e}"
    except httpx.HTTPStatusError as e:
        return f"HTTP error: {e.response.status_code}"
    except Exception as e:
        return f"Error processing content: {e}"
