import streamlit as st
import requests
from bs4 import BeautifulSoup

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

def read_url(url):

    try:

        response = requests.get(
            url,
            timeout=10
        )

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
            "Error" not in content
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