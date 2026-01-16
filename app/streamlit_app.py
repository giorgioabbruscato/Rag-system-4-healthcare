import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
backend_host = os.getenv("BACKEND_HOST", "localhost")
BASE_URL = f"http://{backend_host}:8000"

st.set_page_config(page_title="Multimodal RAG", layout="wide")

st.sidebar.title("Settings")
model = st.sidebar.selectbox("Model", ["gpt-4o-mini", "llama3", "mistral"])
rag_type = st.sidebar.selectbox("RAG type", ["cases", "guidelines", "hybrid"])
st.sidebar.checkbox("Enable evaluation", key="enable_evaluation", value=False)

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Multimodal RAG (DICOM)")

with st.expander("Upload DICOM"):
    dicom = st.file_uploader("Carica un .dcm", type=["dcm"])
    if st.button("Upload") and dicom is not None:
        files = {"file": (dicom.name, dicom.getvalue(), "application/dicom")}
        data = {
            "model": model,
            "rag_type": rag_type,
            "test_splitter_chunk": "default",
            "summarize_type": "none",
        }
        r = requests.post(f"{BASE_URL}/upload-doc", files=files, data=data, timeout=300)
        if r.status_code == 200:
            st.success(r.json())
        else:
            st.error(r.text)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

q = st.chat_input("Domanda...")
if q:
    st.session_state.messages.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.markdown(q)

    payload = {
        "question": q,
        "model": model,
        "rag_type": rag_type,
        "evaluate": st.session_state.get("enable_evaluation", False),
        "session_id": st.session_state.session_id,
    }
    r = requests.post(f"{BASE_URL}/chat", json=payload, timeout=180)
    if r.status_code == 200:
        js = r.json()
        st.session_state.session_id = js.get("session_id", st.session_state.session_id)

        ans = js.get("answer", "")
        st.session_state.messages.append({"role": "assistant", "content": ans})
        with st.chat_message("assistant"):
            st.markdown(ans)

            src = js.get("sources") or []
            if src:
                with st.expander("Sources"):
                    st.json(src)

            ev = js.get("evaluation")
            if ev:
                st.info(ev.get("message") if isinstance(ev, dict) else ev)
    else:
        st.error(r.text)

col1, col2 = st.columns(2)
with col1:
    if st.button("Reset RAG"):
        rr = requests.post(f"{BASE_URL}/flush-rag", json={"model": model, "rag_type": rag_type}, timeout=60)
        st.write(rr.json() if rr.status_code == 200 else rr.text)

with col2:
    if st.button("Clear UI chat"):
        st.session_state.messages = []
        st.session_state.session_id = None
        st.rerun()
