import streamlit as st
import requests
import os
import time

st.title("Upload Syllabus and Chat with AI")

BACKEND_URL = os.getenv("BACKEND_URL", "http://fastapi:8000")

# ---- session state ----
st.session_state.setdefault("document_id", None)
st.session_state.setdefault("faq_id", None)
st.session_state.setdefault("faq_page", 1)

st.session_state.setdefault("faq_job_id", None)
st.session_state.setdefault("faq_target_page", None)
st.session_state.setdefault("faq_generating", False)

# store last known total_pages to avoid None problems
st.session_state.setdefault("faq_total_pages", 1)

PAGE_SIZE = 5
MAX_PAGES = 5

# -----------------------
st.header("1) Upload materials")
uploaded_file = st.file_uploader("Choose a file", type=["txt", "pdf", "csv", "xlsx", "docx"])

if st.button("Upload") and uploaded_file is not None:
    with st.status("Uploading file...", expanded=True) as status:
        status.write(f"File: {uploaded_file.name}")
        files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}

        try:
            resp = requests.post(f"{BACKEND_URL}/upload", files=files, timeout=60)
        except Exception as e:
            status.update(label="Upload failed", state="error")
            st.error(e)
            st.stop()

        if resp.status_code == 200:
            data = resp.json()
            st.session_state.document_id = data["document_id"]

            # reset FAQ state
            st.session_state.faq_id = None
            st.session_state.faq_page = 1
            st.session_state.faq_job_id = None
            st.session_state.faq_target_page = None
            st.session_state.faq_generating = False
            st.session_state.faq_total_pages = 1

            status.update(label="Upload complete", state="complete")
            st.success(f"Uploaded: {data['filename']}")
        else:
            status.update(label="Upload failed", state="error")
            st.error(resp.text)

st.divider()
st.header("2) Build FAQ")

if st.session_state.document_id:
    if st.button("Build FAQ from this document"):
        with st.status("Building FAQ (AI)...", expanded=True) as status:
            status.write("Generating first 5 questions...")
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/documents/{st.session_state.document_id}/build_faq",
                    timeout=180,
                )
            except Exception as e:
                status.update(label="Build failed", state="error")
                st.error(e)
                st.stop()

            if resp.status_code == 200:
                data = resp.json()
                st.session_state.faq_id = data["faq_id"]
                st.session_state.faq_page = 1

                # reset generation state
                st.session_state.faq_job_id = None
                st.session_state.faq_target_page = None
                st.session_state.faq_generating = False
                st.session_state.faq_total_pages = 1

                status.update(label="FAQ ready", state="complete")
                st.success(f"FAQ built. Items: {data['count']}")
            else:
                status.update(label="Build failed", state="error")
                st.error(resp.text)
else:
    st.info("Upload a file first to get document_id.")

# -----------------------
# FAQ viewer + paginator
# -----------------------
if st.session_state.faq_id:
    faq_id = st.session_state.faq_id
    page = st.session_state.faq_page

    # load current page
    with st.status("Loading FAQ page...", expanded=False) as status:
        status.write(f"FAQ id: {faq_id}")
        status.write(f"Requested page: {page}")

        try:
            resp = requests.get(
                f"{BACKEND_URL}/faq/{faq_id}",
                params={"page": page, "page_size": PAGE_SIZE},
                timeout=30,
            )
        except Exception as e:
            status.update(label="Failed to load FAQ", state="error")
            st.error(f"FAQ request failed: {e}")
            st.stop()

        if resp.status_code != 200:
            status.update(label="Failed to load FAQ", state="error")
            st.error(resp.text)
            st.stop()

        faq = resp.json()
        total_pages = int(faq.get("total_pages") or 1)
        st.session_state.faq_total_pages = total_pages

        # clamp ONLY if NOT generating (important)
        if (not st.session_state.faq_generating) and page > total_pages:
            st.session_state.faq_page = total_pages
            status.update(label="Adjusted page number", state="complete")
            st.rerun()

        status.write(f"Total pages currently available: {total_pages}")
        status.update(label="FAQ loaded", state="complete")

    st.subheader("FAQ")

    if not faq.get("items"):
        st.info("No items on this page yet.")
    else:
        for item in faq["items"]:
            st.markdown(f"**Q:** {item['q']}")
            st.write(item["a"])
            st.write("---")

    # ---- pagination controls at the bottom ----
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        prev_disabled = st.session_state.faq_page <= 1
        if st.button("⬅️ Prev", disabled=prev_disabled):
            st.session_state.faq_page -= 1
            st.rerun()

    with col2:
        # show "target" page when generating next
        if st.session_state.faq_generating and st.session_state.faq_target_page:
            label = f"Page <b>{st.session_state.faq_page}</b> (generating page <b>{st.session_state.faq_target_page}</b>...)"
        else:
            label = f"Page <b>{st.session_state.faq_page}</b> of <b>{total_pages}</b>"

        st.markdown(
            f"<div style='text-align:center; padding-top: 0.4rem;'>{label}</div>",
            unsafe_allow_html=True,
        )

    with col3:
        can_go_next = st.session_state.faq_page < total_pages
        can_extend = (st.session_state.faq_page == total_pages) and (total_pages < MAX_PAGES)
        next_disabled = st.session_state.faq_generating or not (can_go_next or can_extend)

        if st.button("Next ➡️", disabled=next_disabled):
            if can_go_next:
                st.session_state.faq_page += 1
                st.rerun()

            # start generating next page async
            st.session_state.faq_generating = True
            st.session_state.faq_target_page = st.session_state.faq_page + 1

            try:
                ext = requests.post(
                    f"{BACKEND_URL}/faq/{faq_id}/extend_async",
                    timeout=30,
                )
            except Exception as e:
                st.session_state.faq_generating = False
                st.session_state.faq_target_page = None
                st.error(f"Failed to start generation: {e}")
                st.stop()

            if ext.status_code != 200:
                st.session_state.faq_generating = False
                st.session_state.faq_target_page = None
                st.error(ext.text)
                st.stop()

            st.session_state.faq_job_id = ext.json()["job_id"]
            st.rerun()

    # ---- generation status box (non-blocking) ----
    if st.session_state.faq_generating and st.session_state.faq_job_id:
        with st.container(border=True):
            st.info(
                f"Generating page {st.session_state.faq_target_page}… "
                f"you can navigate to previous pages while this runs."
            )

            colA, colB, colC = st.columns([1, 1, 2])
            manual = colA.button("🔄 Refresh status")
            cancel = colB.button("✖ Cancel")

            if cancel:
                # purely UI-cancel (job still runs server-side)
                st.session_state.faq_generating = False
                st.session_state.faq_job_id = None
                st.session_state.faq_target_page = None
                st.warning("Cancelled (UI only). The server job may still finish in background.")
                st.rerun()

            if manual:
                try:
                    js = requests.get(f"{BACKEND_URL}/jobs/{st.session_state.faq_job_id}", timeout=10)
                except Exception as e:
                    st.error(f"Failed to read job status: {e}")
                    st.stop()

                if js.status_code != 200:
                    st.error("Failed to read job status")
                else:
                    job = js.json()
                    if job["status"] == "done":
                        added = int(job.get("added") or 0)

                        st.session_state.faq_generating = False
                        st.session_state.faq_job_id = None

                        if added > 0:
                            st.session_state.faq_page = st.session_state.faq_target_page
                            st.session_state.faq_target_page = None
                            st.rerun()
                        else:
                            st.session_state.faq_target_page = None
                            st.warning("No new questions were added (duplicates / model issue).")

                    elif job["status"] == "error":
                        st.session_state.faq_generating = False
                        st.session_state.faq_job_id = None
                        st.session_state.faq_target_page = None
                        st.error(f"Generation failed: {job.get('error')}")

            # optional auto-refresh hint (no infinite rerun loop)
            colC.caption("Tip: click “Refresh status” to update when generation finishes.")

st.divider()
st.header("3) Chat with materials")

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if st.session_state.document_id:
    # render history
    for m in st.session_state.chat_messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    user_msg = st.chat_input("Ask about course topics (definitions, compare, apply, examples...)")
    if user_msg:
        st.session_state.chat_messages.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.write(user_msg)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/chat",
                        json={"document_id": st.session_state.document_id, "question": user_msg},
                        timeout=120,
                    )
                except Exception as e:
                    st.error(f"Chat request failed: {e}")
                    st.stop()

                if resp.status_code == 200:
                    data = resp.json()
                    answer = data["answer"]
                    st.write(answer)

                    # optional: show sources in expander
                    if data.get("matched_snippet"):
                        with st.expander("Show matched excerpt"):
                            st.code(data["matched_snippet"])

                    st.session_state.chat_messages.append({"role": "assistant", "content": answer})
                else:
                    st.error(resp.text)

    if st.button("Clear chat"):
        st.session_state.chat_messages = []
        st.rerun()
else:
    st.info("Upload a file first.")
