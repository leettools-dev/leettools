import os

from firecrawl import FirecrawlApp

api_key = os.getenv("FIRECRAWL_API_KEY", None)
if not api_key:
    raise ValueError("FIRECRAWL_API_KEY environment variable not set")

api_url = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev")
app = FirecrawlApp(api_key=api_key, api_url=api_url)
result = app.search(query="What is firecrawl?")

for x, y in result.items():
    print(x)
    print(f"Type of y is {type(y)}")
    if isinstance(y, list):
        for z in y:
            print(f"Type of z is {type(z)}: {z}")
    elif isinstance(y, dict):
        for z, w in y.items():
            print(f"Type of w is {type(w)}: {w}")
    else:
        print(f"{y}")


print("\n\n\n=========================================")
print("Scraping a URL")

url = "https://example.com/"

content = app.scrape_url(url)
print(f"Type of content is {type(content)}")

if isinstance(content, dict):
    for x, y in content.items():
        print(f"key: {x}, Type of value y is {type(y)}")
        if isinstance(y, list):
            for z in y:
                print(f"\tType of z is {type(z)}: {z}")
        elif isinstance(y, dict):
            for z, w in y.items():
                print(f"\tkey {z} Type of w is {type(w)}: {w}")
        else:
            print(f"\tvalue: {y}")
else:
    print(f"{content}")
