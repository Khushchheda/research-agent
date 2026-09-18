import os
from urllib.parse import quote, urlparse
from urllib.robotparser import RobotFileParser

import requests
import streamlit as st
from bs4 import BeautifulSoup

USER_AGENT = "ResearchAgent/1.0 (+https://github.com/Khushchheda/research-agent)"
REQUEST_HEADERS = {"User-Agent": USER_AGENT}
WIKIPEDIA_SEARCH_URL = "https://en.wikipedia.org/w/rest.php/v1/search/page"


def search_web(query):
    response = requests.get(
        WIKIPEDIA_SEARCH_URL,
        params={"q": query, "limit": 5},
        headers=REQUEST_HEADERS,
        timeout=10,
    )
    response.raise_for_status()

    return [
        "https://en.wikipedia.org/wiki/"
        + quote(result["key"].replace(" ", "_"))
        for result in response.json().get("pages", [])
    ]


def can_fetch(url):
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

    try:
        response = requests.get(
            robots_url,
            headers=REQUEST_HEADERS,
            timeout=10,
        )

        if response.status_code == 404:
            return True, ""

        response.raise_for_status()
        robots = RobotFileParser()
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
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = [
            paragraph.get_text(" ", strip=True)
            for paragraph in soup.find_all("p")
        ]
        content = "\n\n".join(
            paragraph for paragraph in paragraphs if len(paragraph) > 40
        )
        return content[:5000] or "Error: no readable paragraphs found"
    except requests.RequestException as error:
        return f"Error: {error}"


def get_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    except FileNotFoundError:
        return os.getenv("GEMINI_API_KEY")


def get_model_name():
    try:
        return (
            st.secrets.get("GEMINI_MODEL")
            or os.getenv("GEMINI_MODEL")
            or "gemini-2.5-flash"
        )
    except FileNotFoundError:
        return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def generate_report(question, research_notes):
    api_key = get_api_key()

    if not api_key:
        return None

    source_text = "\n\n".join(
        f"SOURCE: {note['url']}\n{note['content'][:3500]}"
        for note in research_notes
        if not note["content"].startswith(("Error:", "Skipped:"))
    )

    if not source_text:
        return None

    prompt = (
        "You are a careful research assistant. Answer only from the provided "
        "sources. Cite claims using the source URLs. If the sources are "
        "insufficient, say so. Return Markdown with the headings Short answer, "
        "Key findings, and Limitations.\n\n"
        f"Question: {question}\n\n{source_text}"
    )
    response = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + get_model_name()
        + ":generateContent",
        headers={
            **REQUEST_HEADERS,
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        json={
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": {"temperature": 0.2},
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


def calculate_confidence(research_notes):
    valid_sources = sum(
        not note["content"].startswith(("Error:", "Skipped:"))
        and len(note["content"]) > 500
        for note in research_notes
    )

    if valid_sources >= 3:
        return "High (3 or more usable sources)"
    if valid_sources == 2:
        return "Medium (2 usable sources)"
    return "Low (fewer than 2 usable sources)"


st.title("Research Agent")
st.caption("Search sources, extract evidence, and generate a cited report.")
question = st.text_input("What would you like to research?")

if st.button("Research"):
    if not question.strip():
        st.warning("Enter a research question first.")
        st.stop()

    with st.spinner("Searching and reading sources..."):
        try:
            urls = search_web(question)
        except requests.RequestException as error:
            st.error(f"Search failed: {error}")
            st.stop()

        research_notes = [
            {"url": url, "content": read_url(url)}
            for url in urls
        ]

    report = None
    if get_api_key():
        with st.spinner("Generating the research report..."):
            try:
                report = generate_report(question, research_notes)
            except Exception as error:
                st.warning(f"The model report could not be generated: {error}")
    else:
        st.info(
            "No GEMINI_API_KEY is configured. Showing source excerpts instead "
            "of a generated report."
        )

    if report:
        st.subheader("Research report")
        st.markdown(report)
    else:
        st.subheader("Source excerpts")
        for note in research_notes:
            with st.expander(note["url"]):
                if note["content"].startswith(("Error:", "Skipped:")):
                    st.warning(note["content"])
                else:
                    st.write(note["content"])

    st.subheader("Confidence")
    st.write(calculate_confidence(research_notes))

    st.subheader("Sources")
    for note in research_notes:
        st.markdown(f"- [{note['url']}]({note['url']})")