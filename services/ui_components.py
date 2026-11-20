"""Reusable styled UI components."""
import streamlit as st


# Letterboxd-inspired rating colors: orange, red, then its signature green.
_RATING_STOPS = (
    (0.0, (255, 159, 28)),
    (0.42, (239, 68, 68)),
    (1.0, (0, 224, 84)),
)


def _color_for_rating(value: float, max_rating: float = 10.0) -> str:
    """Return a smoothly interpolated accent for a rating on 0–max_rating."""
    if value <= 0:
        return "#8792a2"  # unrated

    min_rating = 1.0 if max_rating >= 10.0 else 0.5
    span = max(max_rating - min_rating, 1.0)
    position = min(1.0, max(0.0, (value - min_rating) / span))
    for (start, start_rgb), (end, end_rgb) in zip(_RATING_STOPS, _RATING_STOPS[1:]):
        if position <= end:
            segment = (position - start) / (end - start)
            rgb = tuple(round(a + (b - a) * segment) for a, b in zip(start_rgb, end_rgb))
            return "#" + "".join(f"{channel:02x}" for channel in rgb)
    return "#00e054"


def _rating_gradient() -> str:
    """Return the full orange-to-green gradient used by the rating scale."""
    stops = ", ".join(
        "#" + "".join(f"{channel:02x}" for channel in rgb) + f" {position * 100:.0f}%"
        for position, rgb in _RATING_STOPS
    )
    return f"linear-gradient(90deg, {stops})"


def _numeric_rating(value) -> float:
    """Convert a slider option or selected label to its numeric rating."""
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        cleaned = value.replace("/ 10", "").replace("/10", "").replace("★", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    return 0.0


def _inject_slider_style(css_key: str, options: list) -> None:
    """Inject scoped CSS that reacts to the slider's live ARIA value."""
    # The select_slider widget itself uses ``_inner_{key}``; Streamlit puts
    # that key on the DOM wrapper containing the BaseWeb slider.
    css_key = f"_inner_{css_key}"
    max_rating = max((_numeric_rating(option) for option in options), default=10.0)
    if max_rating <= 0:
        max_rating = 10.0

    state_rules = []
    for index, option in enumerate(options):
        rating = min(max_rating, max(0.0, _numeric_rating(option)))
        color = _color_for_rating(rating, max_rating=max_rating)
        fill_percent = (index / (len(options) - 1) * 100.0) if len(options) > 1 else 0.0

        progress_mask = (
            "linear-gradient(90deg, transparent "
            f"{fill_percent:.2f}%, #d9dce2 {fill_percent:.2f}%)"
        )
        track_background = f"{progress_mask}, {_rating_gradient()}"

        live_value = (
            f'[class*="st-key-{css_key}"]:has('
            f'[role="slider"][aria-valuenow="{index}"])'
        )
        state_rules.append(f"""
        {live_value} [data-baseweb="slider"] > div:first-child > div:first-child {{
            background: {track_background} !important;
        }}
        {live_value} [role="slider"] {{
            background: {color} !important;
        }}
        """)
    live_state_styles = "\n".join(state_rules)

    st.markdown(f"""
    <style>
    /* — Styled rating slider: {css_key} — */
    [class*="st-key-{css_key}"] {{
        width: 100%;
    }}
    [class*="st-key-{css_key}"] [data-baseweb="slider"] {{
        width: 100% !important;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }}
    [class*="st-key-{css_key}"] [data-baseweb="slider"] > div:first-child {{
        width: 100% !important;
    }}
    /* Streamlit renders the rail as the first child of the slider track row. */
    [class*="st-key-{css_key}"] [data-baseweb="slider"] > div:first-child > div:first-child {{
        height: 11px !important;
        border-radius: 999px !important;
        background: #d9dce2 !important;
        box-shadow: inset 0 1px 2px rgba(0,0,0,.16);
    }}
    /* Thumb */
    [class*="st-key-{css_key}"] [data-baseweb="slider"] [role="slider"] {{
        width: 26px !important;
        height: 26px !important;
        background: #8792a2 !important;
        border: 3px solid #fff !important;
        border-radius: 50% !important;
        box-shadow: 0 2px 9px rgba(0,0,0,.28);
    }}
    /* :has() reads aria-valuenow as it changes in the browser, without waiting
       for Streamlit to rerun this Python component after each drag. */
    {live_state_styles}
    [class*="st-key-{css_key}"] [data-testid="stSliderTickBar"] {{
        margin-top: 6px;
    }}
    /* Tick labels */
    [class*="st-key-{css_key}"] [data-testid^="stSliderTickBar"] {{
        font-size: 0.78rem !important;
        font-family: 'Space Grotesk', 'DM Sans', sans-serif !important;
        color: #9aa4b2 !important;
        opacity: 0.8;
    }}
    </style>
    """, unsafe_allow_html=True)


def styled_rating_slider(
    label: str,
    options: list,
    value,
    key: str,
    format_func=None,
) -> object:
    """Render a ``st.select_slider`` for star-ratings with dynamic colour.

    Returns the selected value (same as ``st.select_slider``).
    """
    # Wrap in a keyed container so we can target the CSS
    slider_kwargs: dict = dict(label=label, options=options, value=value, key=f"_inner_{key}")
    if format_func is not None:
        slider_kwargs["format_func"] = format_func
    with st.container(key=key):
        result = st.select_slider(**slider_kwargs)

    _inject_slider_style(key, options)
    return result

