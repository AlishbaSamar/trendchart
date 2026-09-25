"""
auth.py - a simple password login.

The password is NOT in the code. It comes from an environment variable:

    APP_PASSWORD=your-password

  - on your PC:          set it before starting the app (see README)
  - on Streamlit Cloud:  App settings -> Secrets ->  APP_PASSWORD = "your-password"
                         (Streamlit turns secrets into environment variables)

After signing in, the browser keeps a small cookie for 24 hours so a page
reload doesn't ask again. The cookie holds only the expiry time and a
signature made with the password, so it can't be faked without knowing the
password - and changing the password signs everyone out.
"""

import hashlib
import hmac
import os
import time

import streamlit as st

COOKIE = "trendcharts_session"
SESSION_SECONDS = 24 * 60 * 60


def configured_password():
    """The password from the environment (or Streamlit secrets), or None if not set up."""
    value = os.environ.get("APP_PASSWORD")
    if value:
        return value
    try:
        return st.secrets.get("APP_PASSWORD")
    except Exception:  # no secrets file at all
        return None


def _signature(expires, password):
    return hmac.new(password.encode(), str(expires).encode(), hashlib.sha256).hexdigest()


def _valid_token(token, password):
    """Token format: '<expiry timestamp>.<signature>'"""
    try:
        expires_text, signature = token.split(".", 1)
        expires = int(expires_text)
    except (AttributeError, ValueError):
        return False
    return expires > time.time() and hmac.compare_digest(signature, _signature(expires, password))


def _set_cookie(value, max_age):
    """Cookies can only be written by the browser, so we send it a tiny script."""
    st.html(
        f"<script>document.cookie = '{COOKIE}={value}; path=/; max-age={max_age}; SameSite=Strict'"
        f" + (location.protocol === 'https:' ? '; Secure' : '');</script>",
        unsafe_allow_javascript=True,
    )


def is_signed_in():
    password = configured_password()
    if not password:
        return False
    state = st.session_state
    if state.get("signed_in_until", 0) > time.time():
        return True
    if state.get("signed_out"):
        return False  # the old cookie is still in this page's memory - ignore it
    # A fresh page load: check the cookie from an earlier sign-in.
    token = st.context.cookies.get(COOKIE)
    if token and _valid_token(token, password):
        state.signed_in_until = int(token.split(".", 1)[0])
        return True
    return False


def remember_sign_in():
    """Call on every page run after signing in; writes the cookie once."""
    state = st.session_state
    if state.pop("write_cookie", False):
        expires = state.signed_in_until
        _set_cookie(f"{expires}.{_signature(expires, configured_password())}", SESSION_SECONDS)


def sign_out():
    st.session_state.pop("signed_in_until", None)
    st.session_state.signed_out = True
    st.session_state.clear_cookie = True


def forget_cookie_if_signed_out():
    if st.session_state.pop("clear_cookie", False):
        _set_cookie("", 0)


def login_page(side_image=None):
    """Draw the sign-in page. Signs in and reruns on the right password."""
    st.markdown("""<style>
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display: none;}
        .block-container {padding-top: 4rem; max-width: 100%;}
    </style>""", unsafe_allow_html=True)
    forget_cookie_if_signed_out()

    left, right = st.columns([1, 1.25], gap="large", vertical_alignment="center")
    with left:
        st.write("")
        st.markdown("<h1 style='text-align:center;margin-bottom:0'>Welcome</h1>"
                    "<p style='text-align:center;color:#6B7280'>Sign in to Trend Charts</p>",
                    unsafe_allow_html=True)

        password = configured_password()
        if not password:
            st.error("Login is not set up yet. Add an **APP_PASSWORD** environment variable "
                     "(on Streamlit Cloud: App settings → Secrets), then reload this page.")
            st.stop()

        with st.form("login", border=False):
            typed = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign in", type="primary", width="stretch")
        if submitted:
            if hmac.compare_digest(typed.encode(), password.encode()):
                st.session_state.signed_in_until = int(time.time()) + SESSION_SECONDS
                st.session_state.write_cookie = True
                st.session_state.pop("signed_out", None)
                st.rerun()
            time.sleep(1)  # slows down password guessing
            st.error("Wrong password. Please try again.")

        st.markdown("<p style='text-align:center;color:#9CA3AF;font-size:0.85rem;margin-top:1.5rem'>"
                    "Secure access · you stay signed in for 24 hours on this browser</p>",
                    unsafe_allow_html=True)
    with right:
        if side_image:
            st.image(side_image, width="stretch")
    st.stop()
