import os
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

Tavily_api = TavilyClient(
    api_key=os.getenv("tavily")
)

def tavily_function(query):

    api_call = Tavily_api.search(
        query=query,
        max_results=5
    )

    results = []

    for i, a in enumerate(api_call["results"], 1):

        title = a.get("title", "Unknown")
        url = a.get("url", "")
        content = a.get("content", "").strip()

        if len(content) > 300:
            content = content[:300].rsplit(" ", 1)[0] + "..."

        results.append(
            f"{i}. **{title}**\n"
            f"   {url}\n"
            f"   {content}"
        )

    return "\n\n".join(results)