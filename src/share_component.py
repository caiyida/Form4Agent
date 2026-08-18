import base64

import streamlit as st


_SHARE_FILE = st.components.v2.component(
    "form4_file_share",
    html="""
<div class="share-row">
  <button type="button" data-app="WeChat" aria-label="Share PDF to WeChat">
    <span class="wechat">微</span><span>WeChat</span>
  </button>
  <button type="button" data-app="WhatsApp" aria-label="Share PDF to WhatsApp">
    <span class="whatsapp">☎</span><span>WhatsApp</span>
  </button>
</div>
<div class="message" role="status"></div>
""",
    css="""
.share-row { display: flex; flex-wrap: wrap; gap: .5rem; }
button {
  align-items: center; background: var(--st-secondary-background-color);
  border: 1px solid color-mix(in srgb, var(--st-text-color) 18%, transparent);
  border-radius: var(--st-button-radius, .5rem); color: var(--st-text-color);
  cursor: pointer; display: inline-flex; font: inherit; gap: .45rem;
  min-height: 2.5rem; padding: .45rem .8rem;
}
button:hover { border-color: var(--st-primary-color); }
.wechat, .whatsapp {
  align-items: center; border-radius: 50%; color: white; display: inline-flex;
  font-size: .8rem; height: 1.45rem; justify-content: center; width: 1.45rem;
}
.wechat { background: #07c160; }
.whatsapp { background: #25d366; }
.message { color: var(--st-text-color); font-size: .8rem; margin-top: .35rem; }
""",
    js="""
export default function(component) {
  const { data, parentElement } = component
  const message = parentElement.querySelector('.message')
  const bytes = Uint8Array.from(atob(data.base64), c => c.charCodeAt(0))
  const file = new File([bytes], data.filename, { type: 'application/pdf' })

  parentElement.querySelectorAll('button').forEach(button => {
    button.onclick = async () => {
      const app = button.dataset.app
      try {
        if (!navigator.share || !navigator.canShare?.({ files: [file] })) {
          message.textContent = 'File sharing is not supported in this browser. Use Download.'
          return
        }
        await navigator.share({ files: [file], title: data.filename })
        message.textContent = `Choose ${app} in the share sheet.`
      } catch (error) {
        if (error?.name !== 'AbortError') {
          message.textContent = 'Sharing could not start. Use Download.'
        }
      }
    }
  })
}
""",
)


def share_pdf(content, filename="Form4-final-signed.pdf", key="form4-share"):
    """Offer OS-level file sharing without sending the PDF to another server."""

    return _SHARE_FILE(
        key=key,
        data={
            "base64": base64.b64encode(content).decode("ascii"),
            "filename": filename,
        },
        height="content",
    )
