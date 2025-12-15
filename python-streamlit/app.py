import streamlit as st
import requests
import os

st.title("Upload Syllabus and Chat with AI")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if "document_id" not in st.session_state:
    st.session_state.document_id = None
if "faq_id" not in st.session_state:
    st.session_state.faq_id = None

st.header("1) Upload materials")
uploaded_file = st.file_uploader("Choose a file", type=['txt', 'pdf', 'png', 'jpg', 'csv', 'xlsx'])

if st.button("Upload") and uploaded_file is not None:
    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
    resp = requests.post(f"{BACKEND_URL}/upload", files=files)
    if resp.status_code == 200:
        data = resp.json()
        st.session_state.document_id = data["document_id"]
        st.success(f"Uploaded: {data['filename']}")
        st.write("document_id:", st.session_state.document_id)
    else:
        st.error(resp.text)

st.divider()
st.header("2) Build FAQ")

if st.session_state.document_id:
    if st.button("Build FAQ from this document"):
        resp = requests.post(f"{BACKEND_URL}/documents/{st.session_state.document_id}/build_faq")
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.faq_id = data["faq_id"]
            st.success(f"FAQ built. Items: {data['count']}")
        else:
            st.error(resp.text)
else:
    st.info("Upload a file first to get document_id.")

if st.session_state.faq_id:
    resp = requests.get(f"{BACKEND_URL}/faq/{st.session_state.faq_id}")
    if resp.status_code == 200:
        faq = resp.json()
        st.subheader("FAQ")
        for item in faq["items"]:
            st.markdown(f"**Q:** {item['q']}")
            st.write(item["a"])
            st.write("---")

st.divider()
st.header("3) Chat with materials")

if st.session_state.document_id:
    question = st.text_input("Ask a question")
    if st.button("Ask") and question.strip():
        resp = requests.post(f"{BACKEND_URL}/chat", json={
            "document_id": st.session_state.document_id,
            "question": question
        })
        if resp.status_code == 200:
            data = resp.json()
            st.subheader("Answer")
            st.write(data["answer"])
            if data.get("matched_snippet"):
                st.caption("Matched snippet:")
                st.code(data["matched_snippet"])
        else:
            st.error(resp.text)
else:
    st.info("Upload a file first.")
