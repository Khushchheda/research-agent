import os
import re
from urllib.parse import quote, urlparse
from urllib.robotparser import RobotFileParser

import requests
import streamlit as st
from bs4 import BeautifulSoup
from google import genai

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


def get_configured_model():
    try:
        return st.secrets.get("GEMINI_MODEL") or os.getenv("GEMINI_MODEL")
    except FileNotFoundError:
        return os.getenv("GEMINI_MODEL")


def get_model_name(client):
    models = [
        model
        for model in client.models.list()
        if "generateContent" in model.supported_actions
    ]
    configured_model = get_configured_model()

    if configured_model:
        configured_name = configured_model.removeprefix("models/")
        if not configured_name.startswith("gemini-2.5-"):
            for model in models:
                if model.name.removeprefix("models/") == configured_name:
                    return model.name.removeprefix("models/")

    preferred_models = (
        "gemini-3.6-flash",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
    )
    available_names = {
        model.name.removeprefix("models/")
        for model in models
    }

    for preference in preferred_models:
        if preference in available_names:
            return preference

    for model in models:
        if "flash" in model.name.lower():
            return model.name.removeprefix("models/")

    for model in models:
        if "pro" in model.name.lower():
            return model.name.removeprefix("models/")

    raise RuntimeError("The Gemini API key has no model that supports generateContent.")


def generate_report(question, research_notes):
    api_key = get_api_key()

    if not api_key:
        return None

    usable_notes = [
        note
        for note in research_notes
        if not note["content"].startswith(("Error:", "Skipped:"))
    ]
    source_labels = {
        note["url"]: f"[{index}]"
        for index, note in enumerate(usable_notes, start=1)
    }
    source_text = "\n\n".join(
        f"SOURCE [{index}]: {note['url']}\n{note['content'][:3500]}"
        for index, note in enumerate(usable_notes, start=1)
    )

    if not source_text:
        return None

    prompt = (
        "You are a careful research assistant. Answer only from the provided "
        "sources. Cite claims with numbered references such as [1] or [2]. "
        "Do not write full URLs inside the report. Include a numbered Sources "
        "section at the end that maps each number to its URL. If the sources "
        "are insufficient, say so. Return Markdown with the headings Short "
        "answer, Key findings, and Limitations.\n\n"
        f"Question: {question}\n\n{source_text}"
    )
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=get_model_name(client),
        contents=prompt,
        config={"temperature": 0.2},
    )
    report = re.split(
        r"(?im)^#{1,6}\s+sources\s*$",
        response.text,
        maxsplit=1,
    )[0].rstrip()
    for url, label in source_labels.items():
        report = report.replace(f"[{url}]", label).replace(url, label)

    report += "\n\n## Sources\n"
    report += "\n".join(
        f"{label} {url}" for url, label in source_labels.items()
    )

    return report


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