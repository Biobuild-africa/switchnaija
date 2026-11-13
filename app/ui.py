"""BioBuild Africa look and feel for the Streamlit app.

Design tokens are taken from biobuildafrica.org: Raleway headings in deep green, Merriweather
body copy, DM Sans for navigation and labels, orange calls to action, white bordered cards.
"""

from __future__ import annotations

import streamlit as st

GREEN = "#1A4E2C"
GREEN_DEEP = "#003718"
ORANGE = "#DA7A2C"
YELLOW = "#FFD936"
TEXT = "#54595F"
MUTED = "#414941"
BORDER = "#BFC9BF"
TINT = "#F9F9FF"
TINT_GREEN = "#F6F8F5"
FOOTER_BG = "#1F2124"

LOGO = "https://biobuildafrica.org/wp-content/uploads/2026/06/BioBuild-Logo-1a-transparent-300x108.png"
LOGO_WHITE = "https://biobuildafrica.org/wp-content/uploads/2026/06/BioBuild-Logo-1-white-transparent-1024x368.png"
SITE = "https://biobuildafrica.org"

NAV = [("Home", ""), ("Energy Planner", "energy"), ("Battery Afterlife", "battery"), ("FloodSafe", "flood")]

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Merriweather:wght@300;400;700&family=Raleway:wght@500;600;700&display=swap');

/* Hide Streamlit chrome */
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stSidebar"], [data-testid="collapsedControl"], footer {{ display: none !important; }}
.stApp {{ background: #FFFFFF; }}
.block-container {{ padding-top: 0 !important; padding-bottom: 0 !important; max-width: 1240px; }}
.stMarkdown a, .bb-nav a, .bb-footer a, .bb-card a {{ text-decoration: none !important; }}
div.stButton button p, div.stDownloadButton button p {{ font-family: 'DM Sans', sans-serif !important; font-size: 15px; }}

html, body, [class*="css"], .stMarkdown, label, .stTextInput, .stSelectbox, .stNumberInput,
[data-testid="stWidgetLabel"] p {{ font-family: 'DM Sans', sans-serif !important; }}
.stMarkdown p, .stMarkdown li {{ font-family: 'Merriweather', serif; color: {TEXT}; font-size: 15px; line-height: 1.7; }}
h1, h2, h3, h4 {{ font-family: 'Raleway', sans-serif !important; color: {GREEN_DEEP} !important; font-weight: 700 !important; letter-spacing: -0.01em; }}
h1 {{ font-size: 52px !important; line-height: 1.12 !important; color: {GREEN} !important; }}
h2 {{ font-size: 36px !important; }}
h3 {{ font-size: 22px !important; }}

/* Top navigation */
.bb-nav {{ position: sticky; top: 0; z-index: 999; background: #fff; border-bottom: 1px solid #E3E3E3;
  display: flex; align-items: center; justify-content: space-between; padding: 18px 8px; margin: 0 -1rem 0 -1rem; }}
.bb-nav img {{ height: 44px; }}
.bb-nav .links a {{ font-family: 'DM Sans'; font-size: 16px; color: #000; text-decoration: none; margin: 0 16px; }}
.bb-nav .links a.active, .bb-nav .links a:hover {{ color: {ORANGE}; }}
.bb-cta {{ background: {GREEN}; color: #fff !important; padding: 12px 40px; border-radius: 4px;
  font-family: 'DM Sans'; font-size: 15px; text-decoration: none; }}

/* Hero */
.bb-hero {{ background: {TINT}; margin: 0 -100vw; padding: 72px 100vw 64px; border-bottom: 1px solid #E3E3E3; }}
.bb-hero .grid {{ display: flex; gap: 48px; align-items: center; }}
.bb-hero .grid > div {{ flex: 1 1 0; }}
.bb-hero img.art {{ width: 100%; border-radius: 10px; }}
.bb-hero p.lead {{ font-family: 'Merriweather', serif; color: {TEXT}; font-size: 17px; line-height: 1.7; max-width: 640px; }}
.bb-eyebrow {{ display: inline-block; background: #ECEEF0; color: {MUTED}; font-family: 'Raleway'; font-weight: 600;
  font-size: 12px; letter-spacing: .05em; padding: 4px 12px; border-radius: 999px; margin-bottom: 14px; }}
.bb-rule {{ width: 80px; height: 4px; background: #A0521D; border-radius: 2px; margin: 18px 0 30px; }}
.bb-btn {{ display: inline-block; background: {ORANGE}; color: #fff !important; padding: 14px 40px; border-radius: 6px;
  font-family: 'DM Sans'; font-weight: 500; text-decoration: none; margin-right: 16px; }}
.bb-btn-outline {{ display: inline-block; border: 2px solid {GREEN}; color: {GREEN} !important; padding: 12px 40px;
  border-radius: 6px; font-family: 'DM Sans'; font-weight: 500; text-decoration: none; }}

/* Cards */
.bb-card {{ background: #fff; border: 1px solid {BORDER}; border-radius: 8px; padding: 28px 28px 22px; min-height: 320px; display: flex; flex-direction: column; }}
.bb-card a {{ margin-top: auto; }}
.bb-card h4 {{ font-size: 19px !important; margin: 14px 0 10px; }}
.bb-card p {{ font-family: 'Merriweather', serif; color: {TEXT}; font-size: 14.5px; line-height: 1.7; margin: 0 0 14px; }}
.bb-card a {{ font-family: 'DM Sans'; font-weight: 500; color: {GREEN}; text-decoration: none; font-size: 14px; }}
.bb-icon {{ width: 40px; height: 40px; border-radius: 50%; background: {GREEN_DEEP}; color: #fff; display: flex;
  align-items: center; justify-content: center; font-size: 19px; }}
.bb-kpi {{ background: #fff; border: 1px solid {BORDER}; border-radius: 8px; padding: 20px 22px; }}
.bb-kpi .v {{ font-family: 'Raleway'; font-weight: 700; font-size: 30px; color: {GREEN_DEEP}; }}
.bb-kpi .l {{ font-family: 'DM Sans'; color: {MUTED}; font-size: 14px; }}
.bb-reco {{ background: {TINT_GREEN}; border-left: 4px solid {GREEN}; border-radius: 6px; padding: 18px 22px;
  font-family: 'Merriweather', serif; color: {MUTED}; font-size: 15.5px; line-height: 1.7; }}
.bb-step {{ font-family: 'Raleway'; font-weight: 600; font-size: 12px; letter-spacing: .05em; color: {MUTED};
  background: #ECEEF0; padding: 3px 12px; border-radius: 999px; display: inline-block; margin-bottom: 6px; }}

/* Streamlit widgets in brand colours */
div.stButton > button, div.stDownloadButton > button {{ background: {ORANGE}; color: #fff; border: 0; border-radius: 6px;
  padding: 0.7rem 2.4rem; font-family: 'DM Sans'; font-weight: 500; }}
div.stButton > button:hover, div.stDownloadButton > button:hover {{ background: #c4691f; color: #fff; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-color: {BORDER} !important; border-radius: 8px !important; }}
.stTabs [data-baseweb="tab"] {{ font-family: 'DM Sans'; font-size: 15px; }}
.stTabs [aria-selected="true"] {{ color: {ORANGE} !important; }}

/* Footer */
.bb-footer {{ background: {FOOTER_BG}; margin: 64px -100vw 0; padding: 56px 100vw 28px; color: #E3E3E3; }}
.bb-footer img {{ height: 64px; }}
.bb-footer p {{ font-family: 'DM Sans'; color: #E3E3E3; font-size: 15px; line-height: 1.7; max-width: 340px; }}
.bb-footer h5 {{ font-family: 'DM Sans'; color: #fff; font-weight: 500; font-size: 17px; }}
.bb-footer a {{ display: block; color: #E3E3E3; text-decoration: none; font-family: 'DM Sans'; margin: 10px 0; font-size: 15px; }}
.bb-footer a:hover {{ color: {ORANGE}; }}
.bb-footer .bottom {{ border-top: 1px solid #3a3d40; margin-top: 32px; padding-top: 18px; font-size: 13px; color: #9aa0a6; }}
.stApp {{ overflow-x: hidden; }}

/* Phones and small tablets */
@media (max-width: 760px) {{
  .block-container {{ padding-left: 1rem !important; padding-right: 1rem !important; }}
  .bb-nav {{ flex-wrap: wrap; padding: 12px 4px 0; margin: 0 -0.5rem; }}
  .bb-nav img {{ height: 34px; }}
  .bb-cta {{ padding: 8px 16px; font-size: 13px; }}
  .bb-nav .links {{ order: 3; width: 100%; display: flex; overflow-x: auto; white-space: nowrap; gap: 4px;
    padding: 10px 0 8px; margin-top: 10px; border-top: 1px solid #EFEFEF; scrollbar-width: none; }}
  .bb-nav .links::-webkit-scrollbar {{ display: none; }}
  .bb-nav .links a {{ margin: 0 14px 0 0; font-size: 14px; }}
  .bb-hero {{ padding: 32px 100vw 32px; }}
  .bb-hero .grid {{ flex-direction: column; gap: 20px; align-items: stretch; }}
  .bb-hero p.lead {{ font-size: 15px; }}
  h1 {{ font-size: 32px !important; line-height: 1.18 !important; }}
  h2 {{ font-size: 25px !important; }}
  h3 {{ font-size: 19px !important; }}
  .bb-btn, .bb-btn-outline {{ display: block; text-align: center; margin: 0 0 12px 0; padding: 13px 20px; }}
  .bb-card {{ min-height: 0; padding: 22px 20px 18px; }}
  .bb-kpi {{ padding: 14px 16px; }}
  .bb-kpi .v {{ font-size: 24px; }}
  .bb-reco {{ font-size: 14.5px; padding: 14px 16px; }}
  .bb-rule {{ margin: 12px 0 20px; }}
  div.stButton > button, div.stDownloadButton > button {{ width: 100%; }}
  .bb-footer {{ padding: 40px 100vw 24px; margin-top: 40px; }}
  .bb-footer > div:first-child {{ gap: 28px !important; }}
  .bb-footer img {{ height: 48px; }}
}}
</style>
"""


def setup() -> None:
    """Inject the BioBuild stylesheet (call once per run, after set_page_config)."""
    st.markdown(CSS, unsafe_allow_html=True)


def nav(active: str) -> None:
    links = "".join(
        f'<a href="/{slug}" target="_self" class="{"active" if slug == active else ""}">{label}</a>'
        for label, slug in NAV
    )
    st.markdown(
        f"""<div class="bb-nav">
              <a href="/" target="_self"><img src="{LOGO}" alt="BioBuild Africa"></a>
              <div class="links">{links}</div>
              <a class="bb-cta" href="{SITE}/contact/" target="_blank">Contact Us</a>
            </div>""",
        unsafe_allow_html=True,
    )


HERO_ART = "https://biobuildafrica.org/wp-content/uploads/2026/06/Image-1-scaled-1-2048x1143.jpg"


def hero(eyebrow: str, title: str, lead: str, buttons: list[tuple[str, str, bool]] | None = None,
         image: str | None = None) -> None:
    btns = "".join(
        f'<a class="{"bb-btn" if primary else "bb-btn-outline"}" href="{href}" target="_self">{label}</a>'
        for label, href, primary in (buttons or [])
    )
    st.markdown(
        f"""<div class="bb-hero"><div class="grid"><div><span class="bb-eyebrow">{eyebrow}</span>
            <h1>{title}</h1><p class="lead">{lead}</p><div style="margin-top:28px">{btns}</div></div>
            {f'<div><img class="art" src="{image}" alt=""></div>' if image else ''}</div></div>""",
        unsafe_allow_html=True,
    )


def section(title: str, step: str | None = None) -> None:
    pill = f'<span class="bb-step">{step}</span>' if step else ""
    st.markdown(f'{pill}<h2 style="margin:6px 0 0">{title}</h2><div class="bb-rule"></div>', unsafe_allow_html=True)


def card(icon: str, title: str, body: str, link_label: str | None = None, href: str | None = None) -> str:
    link = f'<a href="{href}" target="_self">{link_label} &rarr;</a>' if link_label else ""
    return (f'<div class="bb-card"><div class="bb-icon">{icon}</div><h4>{title}</h4>'
            f"<p>{body}</p>{link}</div>")


def kpi(value: str, label: str) -> str:
    return f'<div class="bb-kpi"><div class="v">{value}</div><div class="l">{label}</div></div>'


def footer() -> None:
    links = "".join(f'<a href="/{slug}" target="_self">{label}</a>' for label, slug in NAV)
    st.markdown(
        f"""<div class="bb-footer">
          <div style="display:flex;gap:80px;flex-wrap:wrap">
            <div><img src="{LOGO_WHITE}" alt="BioBuild Africa"><p>Advancing the frontier of agriculture and
              engineering across the African continent through research, innovation and industrial application.</p></div>
            <div><h5>SwitchNaija</h5>{links}</div>
            <div><h5>BioBuild Africa</h5><a href="{SITE}/about/" target="_blank">About</a>
              <a href="{SITE}/research/" target="_blank">Research</a><a href="{SITE}/contact/" target="_blank">Contact</a></div>
            <div><h5>Open data</h5><a href="https://re.jrc.ec.europa.eu/pvg_tools/en/" target="_blank">PVGIS (EU JRC)</a>
              <a href="https://power.larc.nasa.gov/" target="_blank">NASA POWER</a>
              <a href="https://nigerianstat.gov.ng/" target="_blank">NBS Nigeria</a>
              <a href="https://grid3.org/" target="_blank">GRID3</a></div>
          </div>
          <div class="bottom">© 2026 BioBuild Africa. SwitchNaija is free and open source (MIT). Estimates are for planning only.</div>
        </div>""",
        unsafe_allow_html=True,
    )
