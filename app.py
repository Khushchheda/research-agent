import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

USER_AGENT = "ResearchAgent/1.0 (+https://github.com/Khushchheda/research-agent)"
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT
}

st.title("🔎 Research Agent")

question = st.text_input(
    "Enter your research question"
)

def search_web(query):

    return [
        "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "https://www.ibm.com/topics/artificial-intelligence",
        "https://www.britannica.com/technology/artificial-intelligence"
    ]

def can_fetch(url):

    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

    try:
        response = requests.get(
            robots_url,
            headers=REQUEST_HEADERS,
            timeout=10
        )

        if response.status_code == 404:
            return True, ""

        response.raise_for_status()

        robots = RobotFileParser()
        robots.set_url(robots_url)
        robots.parse(response.text.splitlines())

        if robots.can_fetch(USER_AGENT, url):
            return True, ""

        return False, f"Blocked by {robots_url}"

    except requests.RequestException as error:
        return False, f"Could not read {robots_url}: {error}"


def read_url(url):

    allowed, reason = can_fetch(url)

    if not allowed:
        return f"Skipped: {reason}"

    try:

        response = requests.get(
            url,
            headers=REQUEST_HEADERS,
            timeout=10
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        return soup.get_text()[:2000]

    except Exception as e:

        return f"Error: {e}"
    
def calculate_confidence(research_notes):

    valid_sources = 0

    for note in research_notes:

        content = note["content"]

        if (
            not content.startswith(("Error:", "Skipped:"))
            and len(content) > 500
        ):
            valid_sources += 1

    if valid_sources >= 3:
        return "High (90%)"

    elif valid_sources == 2:
        return "Medium (70%)"

    else:
        return "Low (40%)"

if st.button("Research"):
    urls = search_web(question)

    research_notes = []

    for url in urls:

        content = read_url(url)

        research_notes.append(
            {
                "url": url,
                "content": content
            }
        )

    combined_text = ""

    for note in research_notes:

        combined_text += (
            note["content"][:1000]
            + "\n\n"
        )

    st.subheader("Answer")

    st.write(
        combined_text[:1500]
    )

    confidence = calculate_confidence(
        research_notes
    )

    st.subheader("Confidence")

    st.write(confidence)

    st.subheader("Sources")

    for note in research_notes:

        st.write(
            note["url"]
        )