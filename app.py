
import streamlit as st
from rag_pipeline import ask_question

st.set_page_config(page_title="CodeSyntax AI", page_icon="🤖", layout="wide")

# ---- HEADER ----
st.title("🤖 CodeSyntax AI")
st.caption("Your Python Documentation + Debugging Assistant")

# ---- SIDEBAR ----
with st.sidebar:
    st.header("⚙️ Controls")

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []

    st.markdown("---")
    st.markdown("### About")
    st.write("RAG-powered Python assistant using multiple sources.")

# ---- CHAT HISTORY ----
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---- INPUT ----
prompt = st.chat_input("Ask anything about Python...")

if prompt:

    # USER MESSAGE
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI RESPONSE
    result = ask_question(prompt)
    answer = result["answer"]

    with st.chat_message("assistant"):
        st.markdown(answer)

        # ---- SOURCES ----
        sources = result.get("source_documents") or result.get("sources") or []

        if sources:
            with st.expander("📚 Sources", expanded=False):

                seen = set()

                for i, doc in enumerate(sources):

                    if hasattr(doc, "page_content"):
                        source = doc.metadata.get("source", "Unknown")
                        url = doc.metadata.get("url", "")

                        if source in seen:
                            continue
                        seen.add(source)

                        st.markdown(f"**{len(seen)}. {source}**")

                        if url:
                            st.markdown(f"[🔗 Open Source]({url})")

                    else:
                        preview = str(doc)[:150]
                        if preview in seen:
                            continue
                        seen.add(preview)

                        st.code(preview)

    st.session_state.messages.append({"role": "assistant", "content": answer})