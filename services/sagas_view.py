"""Visual gallery for completed and in-progress film sagas."""
import html
import altair as alt
import pandas as pd
import streamlit as st
from services.tmbd_service import search_movies, get_tmdb_api_key
from services.translations import t, localized as tr
from services.sagas_service import (
    compute_sagas_progress,
    scan_and_cache_tmdb_collections,
    refresh_curated_saga,
    add_film_to_curated_saga,
)


def _esc(value):
    return html.escape(str(value), quote=True)


def _safe_accent(color):
    text = str(color or "").strip()
    if text.startswith("#") and len(text) in (4, 7) and all(c in "0123456789abcdefABCDEF" for c in text[1:]):
        return text
    return "#40bcf4"


def _format_runtime(minutes):
    if not minutes or minutes <= 0:
        return ""
    hours, rem = divmod(int(minutes), 60)
    if hours and rem:
        return f"{hours}h {rem}m"
    if hours:
        return f"{hours}h"
    return f"{rem} min"


def _rating_tier(avg_rating):
    if avg_rating is None:
        return "tier-none"
    if avg_rating >= 8.0:
        return "tier-high"
    if avg_rating >= 6.0:
        return "tier-mid"
    return "tier-low"


def _monogram(name):
    words = [w for w in str(name or "").replace(":", " ").split() if w and w[0].isalnum()]
    if not words:
        return "SG"
    return "".join(w[0].upper() for w in words[:3])


def _category_label(category):
    if category == "universe":
        return tr("Universe", "Universo")
    if category == "thematic":
        return tr("Thematic", "Ciclo tematico")
    return "Saga"


def _poster_html(saga, pill_text, is_complete=False):
    url = saga.get("poster_url_resolved")
    accent = _safe_accent(saga.get("badge_color"))
    pill_cls = "saga-poster-pill complete" if is_complete else "saga-poster-pill"
    pill = f'<span class="{pill_cls}">{_esc(pill_text)}</span>'
    if isinstance(url, str) and url.startswith(("http://", "https://")):
        alt_text = _esc(saga.get("poster_film_title") or saga.get("name") or "Poster")
        inner = f'<img src="{_esc(url)}" alt="{alt_text}" loading="lazy">'
    else:
        sub = saga.get("year_span") or f"{saga.get('total_films', 0)} film"
        inner = (
            f'<div class="saga-poster-fallback" style="--saga-accent:{accent};">'
            f'<div class="saga-poster-monogram">{_esc(_monogram(saga.get("name")))}</div>'
            f'<div class="saga-poster-sub">{_esc(sub)}</div>'
            f'</div>'
        )
    return f'<div class="saga-poster-frame">{inner}{pill}</div>'


def _spotlight_card_html(eyebrow, title, value, meta, accent, poster_url=None, monogram="SG"):
    accent_safe = _safe_accent(accent)
    if isinstance(poster_url, str) and poster_url.startswith(("http://", "https://")):
        poster_inner = f'<img src="{_esc(poster_url)}" alt="{_esc(title)}" loading="lazy">'
    else:
        poster_inner = _esc(monogram)
    return (
        f'<div class="saga-spotlight" style="--spot-accent:{accent_safe};">'
        f'<div class="saga-spot-poster">{poster_inner}</div>'
        f'<div class="saga-spot-body">'
        f'<div class="saga-spot-eyebrow">{_esc(eyebrow)}</div>'
        f'<div class="saga-spot-title" title="{_esc(title)}">{_esc(title)}</div>'
        f'<div class="saga-spot-value">{_esc(value)}</div>'
        f'<div class="saga-spot-meta">{_esc(meta)}</div>'
        f'</div></div>'
    )


def _rating_pills_html(saga):
    avg_u = saga.get("avg_user_rating")
    tier = _rating_tier(avg_u)
    if avg_u is not None:
        user_pill = f'<span class="saga-star-pill {tier}">★ {avg_u:.2f} / 10 ({saga["ratings_count"]})</span>'
    else:
        user_pill = f'<span class="saga-star-pill tier-none">★ {tr("Unrated", "Senza voto")}</span>'
    parts = [user_pill]
    if saga.get("avg_tmdb_rating") is not None:
        parts.append(f'<span class="saga-tmdb-pill">TMDb {saga["avg_tmdb_rating"]:.1f}/10</span>')
    if saga.get("taste_gap") is not None:
        parts.append(f'<span class="saga-gap-pill">{tr("Gap", "Scarto")} {saga["taste_gap"]:+.1f}</span>')
    return f'<div class="saga-rating-row">{"".join(parts)}</div>'


def _card_face_html(saga, mode):
    is_complete = mode == "completed"
    pill_text = "100%" if is_complete else f"{int(round(saga['progress_pct']))}%"
    poster_block = _poster_html(saga, pill_text, is_complete=is_complete)

    meta_pills = [f'<span class="saga-type-pill">{_esc(_category_label(saga.get("category")))}</span>']
    if saga.get("year_span"):
        meta_pills.append(f'<span class="saga-year-pill">{_esc(saga["year_span"])}</span>')
    if is_complete:
        meta_pills.append(f'<span class="saga-rec-pill rec-done">🏆 {tr("Completed", "Completata")}</span>')
    elif saga["watched_count"] > 0 and saga.get("avg_user_rating") is not None and saga["avg_user_rating"] >= 8.0:
        meta_pills.append(f'<span class="saga-rec-pill rec-hot">🔥 {tr("Must finish", "Da recuperare")}</span>')
    elif saga["watched_count"] > 0 and saga["remaining_count"] == 1:
        meta_pills.append(f'<span class="saga-rec-pill rec-close">🏁 {tr("1 film left", "Quasi finita")}</span>')
    elif saga["watched_count"] > 0:
        meta_pills.append(f'<span class="saga-rec-pill rec-mid">🎬 {tr("In progress", "In corso")}</span>')
    else:
        meta_pills.append(f'<span class="saga-rec-pill rec-new">✨ {tr("Not started", "Da iniziare")}</span>')

    body_parts = [
        f'<div class="saga-meta-row">{"".join(meta_pills)}</div>',
        f'<div class="saga-title">{_esc(saga["name"])}</div>',
    ]

    if is_complete:
        runtime_str = _format_runtime(saga.get("total_runtime_min"))
        sub_bits = [tr("{n} chapters completed", "{n} capitoli completati").format(n=saga["released_films"])]
        if runtime_str:
            sub_bits.append(runtime_str)
        if saga.get("upcoming_count"):
            sub_bits.append(tr("{n} upcoming", "{n} in arrivo").format(n=saga["upcoming_count"]))
        body_parts.append(f'<div class="saga-sub-meta">{" · ".join(_esc(b) for b in sub_bits)}</div>')
    else:
        pct = min(100.0, max(0.0, float(saga["progress_pct"])))
        body_parts.append(
            f'<div class="saga-progress-track"><div class="saga-progress-fill" style="width:{pct:.1f}%;"></div></div>'
        )
        if saga["watched_count"] == 0:
            prog_bits = [f'0 / {saga["released_films"]} {tr("films to watch", "film da vedere")}']
        else:
            prog_bits = [
                f'{saga["watched_count"]}/{saga["released_films"]} {tr("watched", "visti")}',
                tr("{n} remaining", "Mancano {n}").format(n=saga["remaining_count"]),
            ]
        if saga.get("upcoming_count"):
            prog_bits.append(tr("{n} upcoming", "{n} in arrivo").format(n=saga["upcoming_count"]))
        body_parts.append(f'<div class="saga-progress-caption">{" · ".join(_esc(b) for b in prog_bits)}</div>')

    body_parts.append(_rating_pills_html(saga))

    best = saga.get("best_film")
    if best:
        yr = f" ({best['year']})" if best.get("year") else ""
        tie = f" (+{best['tie_count'] - 1} {tr('tied', 'a pari merito')})" if best.get("tie_count", 1) > 1 else ""
        fav_label = tr("Favorite", "Preferito") if is_complete else tr("Best so far", "Preferito finora")
        body_parts.append(
            f'<div class="saga-highlight-line">❤️ <b>{_esc(fav_label)}:</b> {_esc(best["title"])}{_esc(yr)} · '
            f'<span class="saga-inline-star">{best["rating"]:g} / 10 ★</span>{_esc(tie)}</div>'
        )

    if not is_complete and saga.get("next_to_watch"):
        nxt = saga["next_to_watch"]
        yr = f" ({nxt['year']})" if nxt.get("year") else ""
        tmdb_bit = f" · TMDb {nxt['tmdb_rating']:.1f}" if pd.notna(nxt.get("tmdb_rating")) and float(nxt['tmdb_rating']) > 0 else ""
        body_parts.append(
            f'<div class="saga-highlight-line">▶️ <b>{tr("Next chapter", "Prossimo da vedere")}:</b> '
            f'{_esc(nxt["title"])}{_esc(yr)}{_esc(tmdb_bit)}</div>'
        )

    dirs = saga.get("directors", [])
    if dirs:
        shown = ", ".join(dirs[:3])
        extra = f" +{len(dirs) - 3}" if len(dirs) > 3 else ""
        body_parts.append(f'<div class="saga-directors-line">🎬 {_esc(shown + extra)}</div>')
    else:
        body_parts.append(
            f'<div class="saga-directors-line">🎬 {_esc(tr("Directors shown after logging or refreshing", "Registi disponibili dopo la visione"))}</div>'
        )

    return f'<div class="saga-card-face">{poster_block}<div class="saga-card-body">{"".join(body_parts)}</div></div>'


def _detail_html(saga):
    sections = []
    if saga.get("description"):
        sections.append(f'<p class="saga-detail-desc">{_esc(saga["description"])}</p>')

    avg_u = f'{saga["avg_user_rating"]:.2f} / 10 ★' if saga.get("avg_user_rating") is not None else "—"
    avg_t = f'{saga["avg_tmdb_rating"]:.2f} / 10 ({saga["tmdb_ratings_count"]}/{saga["released_films"]})' if saga.get("avg_tmdb_rating") is not None else "—"
    gap = f'{saga["taste_gap"]:+.2f} / 10' if saga.get("taste_gap") is not None else "—"
    stats = [
        (tr("Your mean", "Media tua"), avg_u),
        ("TMDb", avg_t),
        (tr("Taste gap", "Scarto voti"), gap),
    ]
    runtime_str = _format_runtime(saga.get("total_runtime_min"))
    if runtime_str:
        stats.append((tr("Watched runtime", "Durata vista"), runtime_str))
    if saga.get("physical_count"):
        stats.append((tr("Owned", "Copie fisiche"), str(saga["physical_count"])))

    stat_pills = "".join(
        f'<div class="saga-detail-stat"><span>{_esc(lbl)}</span><b>{_esc(val)}</b></div>'
        for lbl, val in stats
    )
    sections.append(f'<div class="saga-detail-stats">{stat_pills}</div>')

    best_films = saga.get("best_films", [])
    worst = saga.get("worst_film")
    if best_films:
        fav_titles = ", ".join(
            f"{f['title']} ({f['year']})" if f.get("year") else f["title"]
            for f in best_films[:3]
        )
        if len(best_films) > 3:
            fav_titles += f" (+{len(best_films) - 3})"
        sections.append(
            f'<div class="saga-highlight-line">🏆 <b>{tr("Top rated chapter(s)", "Capitolo preferito")}:</b> '
            f'{_esc(fav_titles)} · <span class="saga-inline-star">{best_films[0]["rating"]:g} / 10 ★</span></div>'
        )
    if worst:
        w_yr = f" ({worst['year']})" if worst.get("year") else ""
        sections.append(
            f'<div class="saga-highlight-line">📉 <b>{tr("Lowest rated", "Voto più basso")}:</b> '
            f'{_esc(worst["title"])}{_esc(w_yr)} · <b>{worst["rating"]:g} / 10 ★</b></div>'
        )

    dir_counts = saga.get("director_counts", [])
    if dir_counts:
        dir_badges = "".join(
            f'<span class="director-badge">{_esc(name)}{f" ({cnt})" if cnt > 1 else ""}</span>'
            for name, cnt in dir_counts
        )
        sections.append(f'<div class="saga-detail-section-label">{_esc(tr("Directors", "Registi"))}</div><div>{dir_badges}</div>')

    genres = saga.get("genres", [])
    if genres:
        genre_badges = "".join(f'<span class="genre-badge">{_esc(g)}</span>' for g in genres)
        sections.append(f'<div style="margin-top:.35rem;">{genre_badges}</div>')

    best_rating_val = saga["best_film"]["rating"] if saga.get("best_film") else None
    rows_html = []
    for idx, film in enumerate(saga["all_films"], start=1):
        watched = bool(film.get("watched"))
        rel_state = film.get("release_state", "released")
        is_fav = (
            watched
            and best_rating_val is not None
            and pd.notna(film.get("user_rating"))
            and float(film["user_rating"]) == best_rating_val
        )
        row_classes = ["saga-chapter-row"]
        if watched:
            row_classes.append("is-watched")
        elif rel_state != "released":
            row_classes.append("is-upcoming")
        else:
            row_classes.append("is-missing")
        if is_fav:
            row_classes.append("is-favorite")

        p_path = film.get("poster_path")
        if p_path:
            thumb = f'<img class="saga-chapter-thumb" src="{_esc("https://image.tmdb.org/t/p/w154" + str(p_path))}" alt="" loading="lazy">'
        else:
            thumb = f'<div class="saga-chapter-thumb-fallback">{idx}</div>'

        yr_str = f" ({film['year']})" if film.get("year") else ""
        fav_icon = " ❤️" if is_fav else ""
        phys_icon = " 💿" if film.get("has_physical") else ""
        sub_bits = []
        if film.get("phase"):
            sub_bits.append(str(film["phase"]))
        if film.get("directors"):
            sub_bits.append(", ".join(film["directors"][:2]))
        sub_html = f'<div class="saga-chapter-sub">{_esc(" · ".join(sub_bits))}</div>' if sub_bits else ""

        if watched and pd.notna(film.get("user_rating")):
            status_badge = f'<span class="saga-chapter-rating">★ {float(film["user_rating"]):g} / 10</span>'
        elif watched:
            status_badge = f'<span class="saga-chapter-rating">✓ {tr("Watched", "Visto")}</span>'
        elif rel_state == "upcoming":
            status_badge = f'<span class="saga-chapter-upcoming">{tr("Upcoming", "In arrivo")}</span>'
        elif rel_state == "unknown":
            status_badge = f'<span class="saga-chapter-upcoming">{tr("To verify", "Da verificare")}</span>'
        else:
            status_badge = f'<span class="saga-chapter-todo">{tr("To watch", "Da vedere")}</span>'

        tmdb_val = film.get("tmdb_rating")
        tmdb_html = (
            f'<div class="saga-chapter-tmdb">TMDb {float(tmdb_val):.1f}</div>'
            if pd.notna(tmdb_val) and float(tmdb_val) > 0
            else ""
        )

        rows_html.append(
            f'<div class="{" ".join(row_classes)}">'
            f'{thumb}'
            f'<div class="saga-chapter-info">'
            f'<div class="saga-chapter-title">{idx}. {_esc(film["title"])}{_esc(yr_str)}{fav_icon}{phys_icon}</div>'
            f'{sub_html}'
            f'</div>'
            f'<div class="saga-chapter-status">{status_badge}{tmdb_html}</div>'
            f'</div>'
        )

    sections.append(
        f'<div class="saga-detail-section-label">{_esc(tr("Chapters", "Capitoli"))} ({len(saga["all_films"])})</div>'
        f'<div class="saga-chapters-list">{"".join(rows_html)}</div>'
    )
    return "".join(sections)


def _render_curated_actions(saga, mode):
    prefix = f"{mode}_{saga['id']}"
    if st.button(tr("Refresh known films in this saga", "Aggiorna i film noti di questa saga"), key=f"refresh_{prefix}"):
        progress = st.progress(0.0)
        try:
            report = refresh_curated_saga(saga["id"], lambda n, total: progress.progress(n / total))
        except Exception as exc:
            st.error(str(exc))
        else:
            st.session_state["saga_refresh_result"] = tr(
                "Updated {updated} films; {failed} could not be matched/refreshed.",
                "Aggiornati {updated} film; {failed} non abbinati/aggiornati.",
            ).format(**report)
            st.rerun()

    st.caption(tr(
        "Add a missing film from TMDb (updates the saga catalog; does not mark the film as watched).",
        "Aggiungi un film mancante da TMDb (aggiorna il catalogo della saga senza segnarlo come visto).",
    ))
    c_search, c_btn = st.columns([3, 1])
    search_query = c_search.text_input(
        tr("Film title on TMDb", "Titolo del film su TMDb"),
        key=f"saga_search_{prefix}",
        label_visibility="collapsed",
        placeholder=tr("Search TMDb film to add…", "Cerca su TMDb un film da aggiungere…"),
    )
    if c_btn.button(tr("Search TMDb", "Cerca su TMDb"), key=f"saga_search_btn_{prefix}", use_container_width=True):
        if not get_tmdb_api_key():
            st.warning(tr("Configure your TMDb key in Settings.", "Configura la chiave TMDb nelle Impostazioni."))
        else:
            st.session_state[f"saga_matches_{prefix}"] = search_movies(search_query)

    matches = st.session_state.get(f"saga_matches_{prefix}")
    if matches == []:
        st.info(tr("No results. Try another title.", "Nessun risultato. Prova un altro titolo."))
    if matches:
        movie_id = st.selectbox(
            tr("Select the film", "Seleziona il film"),
            [m["id"] for m in matches],
            format_func=lambda value: next(f"{m['title']} ({m['year']})" for m in matches if m["id"] == value),
            key=f"saga_select_{prefix}",
        )
        phase = st.text_input(tr("Phase / chapter (optional)", "Fase / capitolo (facoltativo)"), key=f"saga_phase_{prefix}")
        if st.button(tr("Add to saga catalog", "Aggiungi al catalogo della saga"), key=f"saga_add_btn_{prefix}"):
            try:
                added = add_film_to_curated_saga(saga["id"], movie_id, phase)
            except Exception as exc:
                st.error(str(exc))
            else:
                st.session_state["saga_refresh_result"] = (
                    tr("Film added to saga.", "Film aggiunto alla saga.")
                    if added
                    else tr("This film is already in the saga.", "Il film è già presente nella saga.")
                )
                st.rerun()


def _render_saga_card(saga, mode):
    with st.container(border=True):
        st.markdown(_card_face_html(saga, mode), unsafe_allow_html=True)
        with st.expander(tr("Details, directors & chapters", "Dettagli, registi e capitoli")):
            st.markdown(_detail_html(saga), unsafe_allow_html=True)
            if saga["unknown_release_count"]:
                st.warning(tr(
                    "Completion refers only to known released films. Verify unknown release dates by refreshing metadata.",
                    "Il completamento considera solo i film con uscita nota. Aggiorna i metadati per verificare le uscite incerte.",
                ))
            source = tr("TMDb collection", "Collezione TMDb") if saga.get("source") == "tmdb" else tr("Curated list", "Lista curata")
            st.caption(
                source
                + " · "
                + tr("Last metadata refresh: ", "Ultimo aggiornamento metadati: ")
                + (saga.get("updated_at") or tr("not yet refreshed", "non ancora aggiornati"))
            )
            if saga.get("source") == "curated":
                _render_curated_actions(saga, mode)


def _render_saga_grid(sagas, mode):
    for idx in range(0, len(sagas), 2):
        cols = st.columns(2)
        for offset, saga in enumerate(sagas[idx: idx + 2]):
            with cols[offset]:
                _render_saga_card(saga, mode)


def _matches_filters(saga, query, category):
    if category != "all" and saga.get("category") != category:
        return False
    q = query.strip().casefold()
    if not q:
        return True
    if q in saga["name"].casefold():
        return True
    if any(q in f["title"].casefold() for f in saga["all_films"]):
        return True
    return any(q in d.casefold() for d in saga.get("directors", []))


def _toggle_completed_chart_order():
    st.session_state["sagas_completed_chart_flop"] = not bool(
        st.session_state.get("sagas_completed_chart_flop", False)
    )


def _select_completed_chart_sagas(rated, limit=10, show_flop=False):
    """Return the top or bottom (flop) rated completed sagas, trimmed to `limit`."""
    cap = max(1, int(limit or 10))
    if show_flop:
        ordered = sorted(rated, key=lambda x: (x["avg_user_rating"], -x["ratings_count"], x["name"]))
    else:
        ordered = sorted(rated, key=lambda x: (-x["avg_user_rating"], -x["ratings_count"], x["name"]))
    return ordered[:cap]


def _render_completed_section(completed):
    if not completed:
        st.info(t("sagas_no_completed"))
        return

    rated = [s for s in completed if s.get("avg_user_rating") is not None]
    best_saga = max(
        rated or completed,
        key=lambda s: (s.get("avg_user_rating") or -1, s["ratings_count"], s["released_films"]),
    )
    longest = max(completed, key=lambda s: (s["released_films"], s.get("total_runtime_min", 0)))

    best_fav = best_saga.get("best_film")
    best_meta = (
        tr("Favorite: {title} ({r:g}/10 ★)", "Preferito: {title} ({r:g}/10 ★)").format(
            title=best_fav["title"], r=best_fav["rating"]
        )
        if best_fav
        else tr("{n} chapters watched", "{n} capitoli visti").format(n=best_saga["released_films"])
    )
    if rated:
        overall_mean = sum(s["avg_user_rating"] for s in rated) / len(rated)
        mean_val = f"{overall_mean:.2f} / 10 ★"
        mean_meta = tr("Across {n} rated completed sagas", "Su {n} saghe completate votate").format(n=len(rated))
        mean_title = best_saga["name"] if len(rated) == 1 else tr("Average across your completed sagas", "Media delle saghe completate")
    else:
        mean_val = "—"
        mean_meta = tr("Add ratings to unlock saga rankings", "Aggiungi voti ai film per vedere le medie")
        mean_title = tr("No ratings yet", "Nessun voto ancora")

    longest_rt = _format_runtime(longest.get("total_runtime_min"))
    longest_meta = (
        f"{longest_rt} · " + (f"{longest['avg_user_rating']:.2f} / 10 ★" if longest.get("avg_user_rating") is not None else tr("Unrated", "Senza voto"))
        if longest_rt
        else tr("Completed at 100%", "Completata al 100%")
    )

    spotlights = "".join([
        _spotlight_card_html(
            tr("Top completed saga", "Miglior saga completata"),
            best_saga["name"],
            f"{best_saga['avg_user_rating']:.2f} / 10 ★" if best_saga.get("avg_user_rating") is not None else f"{best_saga['released_films']} film",
            best_meta,
            "#00e676",
            poster_url=best_saga.get("poster_url_resolved"),
            monogram=_monogram(best_saga["name"]),
        ),
        _spotlight_card_html(
            tr("Completed average", "Media completate"),
            mean_title,
            mean_val,
            mean_meta,
            "#40bcf4",
            monogram="★",
        ),
        _spotlight_card_html(
            tr("Longest completed saga", "Saga più lunga"),
            longest["name"],
            f"{longest['released_films']} film",
            longest_meta,
            "#ff9b38",
            poster_url=longest.get("poster_url_resolved"),
            monogram=_monogram(longest["name"]),
        ),
    ])
    st.markdown(f'<div class="saga-spotlights">{spotlights}</div>', unsafe_allow_html=True)

    if rated:
        show_flop = bool(st.session_state.get("sagas_completed_chart_flop", False))
        c_limit, c_flip = st.columns([1.2, 1.8], vertical_alignment="bottom")
        chart_limit = c_limit.number_input(
            tr("Sagas shown in chart", "Saghe nel grafico"),
            min_value=1,
            max_value=500,
            value=10,
            step=1,
            key="sagas_completed_chart_limit",
        )
        flip_label = (
            tr("🏆 Invert: show TOP sagas", "🏆 Inverti: mostra TOP saghe")
            if show_flop
            else tr("📉 Invert: show FLOP sagas", "📉 Inverti: mostra FLOP saghe")
        )
        c_flip.button(
            flip_label,
            key="sagas_completed_chart_flip",
            on_click=_toggle_completed_chart_order,
            use_container_width=True,
        )

        display_sagas = _select_completed_chart_sagas(rated, limit=chart_limit, show_flop=show_flop)
        if show_flop:
            heading = tr(
                "Flop {shown} completed sagas (lowest avg rating)",
                "Flop {shown} saghe completate (voto medio più basso)",
            ).format(shown=len(display_sagas))
            icon = "📉"
        else:
            heading = tr(
                "Top {shown} completed sagas by your average rating",
                "Top {shown} saghe completate per voto medio",
            ).format(shown=len(display_sagas))
            icon = "🏆"
        if len(rated) > len(display_sagas):
            heading += tr(" · out of {total} rated", " · su {total} votate").format(total=len(rated))
        st.markdown(f"##### {icon} {heading}")

        chart_rows = []
        for s in display_sagas:
            fav = s.get("best_film")
            chart_rows.append({
                "Saga": s["name"],
                "Avg": s["avg_user_rating"],
                "Films": s["released_films"],
                "TMDb": s["avg_tmdb_rating"] if s.get("avg_tmdb_rating") is not None else 0.0,
                "Favorite": f"{fav['title']} ({fav['rating']:g}/10 ★)" if fav else "—",
                "Label": f"{s['avg_user_rating']:.2f} ★",
            })
        chart_df = pd.DataFrame(chart_rows)
        order_names = chart_df["Saga"].tolist()
        bars = alt.Chart(chart_df).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
            x=alt.X("Avg:Q", title=tr("Personal avg / 10", "Media personale / 10"), scale=alt.Scale(domain=[0, 11.2])),
            y=alt.Y("Saga:N", sort=order_names, title=None),
            color=alt.Color(
                "Avg:Q",
                scale=alt.Scale(domain=[4.0, 7.0, 10.0], range=["#ff6b6b", "#ff9b38", "#00e676"]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Saga:N", title="Saga"),
                alt.Tooltip("Avg:Q", title=tr("Your avg / 10", "Media tua / 10"), format=".2f"),
                alt.Tooltip("Favorite:N", title=tr("Favorite film", "Film preferito")),
                alt.Tooltip("Films:Q", title=tr("Chapters", "Capitoli")),
                alt.Tooltip("TMDb:Q", title="TMDb / 10", format=".2f"),
            ],
        )
        labels = alt.Chart(chart_df).mark_text(
            align="left", baseline="middle", dx=6, color="#F4F7FC", fontSize=11, fontWeight=600
        ).encode(
            x=alt.X("Avg:Q"),
            y=alt.Y("Saga:N", sort=order_names),
            text="Label:N",
        )
        st.altair_chart((bars + labels).properties(height=max(180, len(chart_df) * 34)), use_container_width=True)

    completed_sort_labels = {
        "personal": tr("Your highest average rating", "Voto medio più alto"),
        "films": tr("Most chapters", "Più capitoli"),
        "tmdb": tr("Highest TMDb average", "Media TMDb più alta"),
        "gap": tr("You rate higher than TMDb", "Preferite da te rispetto a TMDb"),
        "name": tr("Name A–Z", "Nome A–Z"),
    }
    sort_mode = st.selectbox(
        tr("Sort completed sagas", "Ordina saghe completate"),
        ["personal", "films", "tmdb", "gap", "name"],
        format_func=completed_sort_labels.__getitem__,
        key="sagas_completed_sort",
    )

    def completed_sort_key(s):
        if sort_mode == "name":
            return (s["name"].casefold(),)
        if sort_mode == "films":
            return (-s["released_films"], -(s.get("avg_user_rating") or 0), s["name"])
        field = {"personal": "avg_user_rating", "tmdb": "avg_tmdb_rating", "gap": "taste_gap"}[sort_mode]
        val = s.get(field)
        return (val is None, -(val or 0), -s["released_films"], s["name"])

    _render_saga_grid(sorted(completed, key=completed_sort_key), mode="completed")


def _render_incomplete_section(incomplete):
    if not incomplete:
        st.info(t("sagas_no_started"))
        return

    started = [s for s in incomplete if s["watched_count"] > 0] or incomplete
    started_rated = [s for s in started if s.get("recovery_score") is not None]

    if started_rated:
        rec_saga = max(started_rated, key=lambda s: (s["recovery_score"], s["avg_user_rating"], -s["remaining_count"]))
        rec_val = f"{rec_saga['avg_user_rating']:.2f} / 10 ★"
        nxt = rec_saga.get("next_to_watch")
        rec_meta = (
            tr("{w}/{r} watched · Next: {t}", "{w}/{r} visti · Prossimo: {t}").format(
                w=rec_saga["watched_count"], r=rec_saga["released_films"], t=nxt["title"]
            )
            if nxt
            else f"{rec_saga['watched_count']}/{rec_saga['released_films']} · {tr('Missing', 'Mancano')} {rec_saga['remaining_count']}"
        )
    else:
        rec_saga = max(incomplete, key=lambda s: (s["progress_pct"], s.get("avg_tmdb_rating") or 0))
        rec_val = f"{rec_saga['watched_count']}/{rec_saga['released_films']}"
        rec_meta = tr("Missing {n} films", "Mancano {n} film").format(n=rec_saga["remaining_count"])

    closest_pool = [s for s in started if s["remaining_count"] > 0] or incomplete
    closest = min(
        closest_pool,
        key=lambda s: (s["remaining_count"], -(s.get("avg_user_rating") or 0), -s["progress_pct"]),
    )
    closest_val = tr("{n} left", "Manca {n}" if closest["remaining_count"] == 1 else "Mancano {n}").format(
        n=closest["remaining_count"]
    )
    closest_meta = f"{closest['watched_count']}/{closest['released_films']} ({closest['progress_pct']:.0f}%)"
    if closest.get("avg_user_rating") is not None:
        closest_meta += f" · {closest['avg_user_rating']:.2f} / 10 ★"

    most_missing = max(incomplete, key=lambda s: (s["remaining_count"], s["watched_count"], s["name"]))
    missing_val = tr("{n} missing", "{n} mancanti").format(n=most_missing["remaining_count"])
    missing_meta = f"{most_missing['watched_count']}/{most_missing['released_films']} " + tr("watched", "visti")
    if most_missing.get("avg_user_rating") is not None:
        missing_meta += f" · {most_missing['avg_user_rating']:.2f} / 10 ★"

    spotlights = "".join([
        _spotlight_card_html(
            tr("Top pick to recover", "Da recuperare per i tuoi voti"),
            rec_saga["name"],
            rec_val,
            rec_meta,
            "#00e676",
            poster_url=rec_saga.get("poster_url_resolved"),
            monogram=_monogram(rec_saga["name"]),
        ),
        _spotlight_card_html(
            tr("Closest to completion", "Più vicina al completamento"),
            closest["name"],
            closest_val,
            closest_meta,
            "#40bcf4",
            poster_url=closest.get("poster_url_resolved"),
            monogram=_monogram(closest["name"]),
        ),
        _spotlight_card_html(
            tr("Most films remaining", "Più film mancanti"),
            most_missing["name"],
            missing_val,
            missing_meta,
            "#ff9b38",
            poster_url=most_missing.get("poster_url_resolved"),
            monogram=_monogram(most_missing["name"]),
        ),
    ])
    st.markdown(f'<div class="saga-spotlights">{spotlights}</div>', unsafe_allow_html=True)

    chart_mode_labels = {
        "recommended": tr("🔥 Top-rated partial sagas to recover", "🔥 Saghe parziali più apprezzate (da recuperare)"),
        "missing": tr("📚 Sagas with the most missing films", "📚 Saghe con più film mancanti"),
    }
    chart_mode = st.radio(
        tr("Priority overview", "Vista priorità"),
        options=["recommended", "missing"],
        format_func=chart_mode_labels.__getitem__,
        horizontal=True,
        key="sagas_incomplete_chart_mode",
    )

    if chart_mode == "recommended":
        if started_rated:
            top_rec = sorted(
                started_rated,
                key=lambda s: (-s["avg_user_rating"], -s["recovery_score"], s["remaining_count"]),
            )[:12]
            c_df = pd.DataFrame([{
                "Saga": s["name"],
                "Rating": s["avg_user_rating"],
                "Remaining": s["remaining_count"],
                "Watched": f"{s['watched_count']}/{s['released_films']}",
                "Next": s["next_to_watch"]["title"] if s.get("next_to_watch") else "—",
                "Label": f"{s['avg_user_rating']:.2f} ★ · -{s['remaining_count']} film",
            } for s in top_rec])
            order_names = c_df["Saga"].tolist()
            bars = alt.Chart(c_df).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
                x=alt.X("Rating:Q", title=tr("Your avg rating / 10", "La tua media / 10"), scale=alt.Scale(domain=[0, 12.2])),
                y=alt.Y("Saga:N", sort=order_names, title=None),
                color=alt.Color(
                    "Rating:Q",
                    scale=alt.Scale(domain=[4.0, 7.0, 10.0], range=["#ff6b6b", "#ff9b38", "#00e676"]),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("Saga:N", title="Saga"),
                    alt.Tooltip("Rating:Q", title=tr("Your avg / 10", "Media tua / 10"), format=".2f"),
                    alt.Tooltip("Watched:N", title=tr("Watched", "Visti")),
                    alt.Tooltip("Remaining:Q", title=tr("Missing", "Mancanti")),
                    alt.Tooltip("Next:N", title=tr("Next film", "Prossimo film")),
                ],
            )
            labels = alt.Chart(c_df).mark_text(
                align="left", baseline="middle", dx=6, color="#F4F7FC", fontSize=11, fontWeight=600
            ).encode(
                x=alt.X("Rating:Q"),
                y=alt.Y("Saga:N", sort=order_names),
                text="Label:N",
            )
            st.altair_chart((bars + labels).properties(height=max(200, len(c_df) * 34)), use_container_width=True)
        else:
            st.caption(tr(
                "Rate at least one watched film in a partial saga to rank recommendations by personal taste.",
                "Vota almeno un film in una saga parziale per ordinare i consigli in base ai tuoi gusti.",
            ))
    else:
        top_missing = sorted(
            [s for s in incomplete if s["remaining_count"] > 0],
            key=lambda s: (-s["remaining_count"], -s["watched_count"], s["name"]),
        )[:12]
        if top_missing:
            c_df = pd.DataFrame([{
                "Saga": s["name"],
                "Remaining": s["remaining_count"],
                "Watched": f"{s['watched_count']}/{s['released_films']}",
                "Avg": s["avg_user_rating"] if s.get("avg_user_rating") is not None else 0.0,
                "Label": f"-{s['remaining_count']} film ({s['watched_count']}/{s['released_films']})",
            } for s in top_missing])
            order_names = c_df["Saga"].tolist()
            bars = alt.Chart(c_df).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6, color="#ff9b38").encode(
                x=alt.X("Remaining:Q", title=tr("Missing released films", "Film usciti mancanti"), scale=alt.Scale(domain=[0, max(c_df["Remaining"]) * 1.35])),
                y=alt.Y("Saga:N", sort=order_names, title=None),
                tooltip=[
                    alt.Tooltip("Saga:N", title="Saga"),
                    alt.Tooltip("Remaining:Q", title=tr("Missing", "Mancanti")),
                    alt.Tooltip("Watched:N", title=tr("Watched", "Visti")),
                    alt.Tooltip("Avg:Q", title=tr("Your avg / 10", "Media tua / 10"), format=".2f"),
                ],
            )
            labels = alt.Chart(c_df).mark_text(
                align="left", baseline="middle", dx=6, color="#F4F7FC", fontSize=11, fontWeight=600
            ).encode(
                x=alt.X("Remaining:Q"),
                y=alt.Y("Saga:N", sort=order_names),
                text="Label:N",
            )
            st.altair_chart((bars + labels).properties(height=max(200, len(c_df) * 34)), use_container_width=True)

    inc_sort_labels = {
        "recommended": tr("Best partial sagas to recover (your ratings)", "Consigliate da recuperare (tuoi voti)"),
        "personal": tr("Your highest average rating", "Voto medio personale"),
        "almost": tr("Closest to completion (fewest missing)", "Quasi completate (meno film mancanti)"),
        "most_missing": tr("Most missing films", "Più film mancanti"),
        "progress": tr("Highest progress %", "Progresso %"),
        "tmdb": tr("Highest TMDb rating", "Media TMDb"),
        "name": tr("Name A–Z", "Nome A–Z"),
    }
    sort_mode = st.selectbox(
        tr("Sort sagas to complete", "Ordina saghe da completare"),
        ["recommended", "personal", "almost", "most_missing", "progress", "tmdb", "name"],
        format_func=inc_sort_labels.__getitem__,
        key="sagas_inc_sort",
    )

    def inc_sort_key(s):
        if sort_mode == "name":
            return (s["name"].casefold(),)
        if sort_mode == "recommended":
            if s.get("recovery_score") is not None:
                return (0, -s["recovery_score"], -s["avg_user_rating"], s["remaining_count"], s["name"])
            if s["watched_count"] > 0:
                return (1, -s["progress_pct"], s["remaining_count"], s["name"])
            return (2, -(s.get("avg_tmdb_rating") or 0), s["remaining_count"], s["name"])
        if sort_mode == "personal":
            val = s.get("avg_user_rating")
            return (val is None, -(val or 0), -s["watched_count"], s["remaining_count"], s["name"])
        if sort_mode == "almost":
            return (s["watched_count"] == 0, s["remaining_count"], -(s.get("avg_user_rating") or 0), -s["progress_pct"], s["name"])
        if sort_mode == "most_missing":
            return (-s["remaining_count"], -s["watched_count"], -(s.get("avg_user_rating") or 0), s["name"])
        if sort_mode == "progress":
            return (-s["progress_pct"], -s["watched_count"], -(s.get("avg_user_rating") or 0), s["name"])
        val = s.get("avg_tmdb_rating")
        return (val is None, -(val or 0), -s["watched_count"], s["name"])

    _render_saga_grid(sorted(incomplete, key=inc_sort_key), mode="incomplete")


def render_sagas():
    st.subheader(f"🪐 {t('sagas_title')}")
    st.caption(tr(
        "Explore completed franchises, favorite chapters and the partial sagas most worth finishing.",
        "Esplora le saghe completate, i capitoli preferiti e le saghe iniziate che vale più la pena recuperare.",
    ))
    df = st.session_state.get("enriched_data", pd.DataFrame())
    if df.empty:
        st.info(t("no_data_warning"))
        st.page_link("pages/data_manager.py", label=t("nav_data_manager"), icon="⚙️")
        return
    if "saga_refresh_result" in st.session_state:
        st.info(st.session_state.pop("saga_refresh_result"))

    data = compute_sagas_progress(df)
    kpis = data["kpis"]
    cols = st.columns(4)
    for col, label, value in zip(
        cols,
        [
            t("sagas_kpi_completed"),
            t("sagas_kpi_started"),
            t("sagas_kpi_franchise_films"),
            t("sagas_kpi_tracked"),
        ],
        [
            kpis["completed_count"],
            kpis["started_count"],
            kpis["total_franchise_films_watched"],
            kpis["total_sagas_tracked"],
        ],
    ):
        col.metric(label, value)

    with st.expander(tr("Update saga information", "Aggiorna informazioni sulle saghe")):
        st.write(tr(
            "Scan the entire library to discover collections and refresh their films, ratings and release dates. Existing cached data remains available if requests fail.",
            "Scansiona tutta la libreria per scoprire collezioni e aggiornarne film, voti e date di uscita. Se una richiesta fallisce, i dati già salvati restano disponibili.",
        ))
        if st.button(tr("Discover / refresh TMDb collections", "Scopri / aggiorna collezioni TMDb"), key="sagas_scan_tmdb_btn"):
            progress = st.progress(0.0)
            try:
                report = scan_and_cache_tmdb_collections(df, progress_callback=lambda n, total: progress.progress(n / total))
            except Exception as exc:
                st.error(str(exc))
            else:
                st.session_state["saga_refresh_result"] = tr(
                    "Scanned {scanned} films: {new} new collections, {refreshed} refreshed, {failed} failed requests, {unmatched} uncertain matches.",
                    "Esaminati {scanned} film: {new} nuove collezioni, {refreshed} aggiornate, {failed} richieste fallite, {unmatched} abbinamenti incerti.",
                ).format(**report)
                st.rerun()
        st.caption(tr(
            "Universes use a curated film list. Their known films can be refreshed in each card; TMDb collections are not a complete universe catalog.",
            "Gli universi usano una lista curata. Puoi aggiornare i dati dei film noti dentro ciascuna card; le collezioni TMDb non sono un catalogo completo degli universi.",
        ))

    c1, c2 = st.columns([2.2, 1])
    query = c1.text_input(
        tr("Search saga, film or director", "Cerca saga, film o regista"),
        placeholder=tr("e.g. Dune, Nolan, Star Wars…", "es. Dune, Nolan, Star Wars…"),
        key="sagas_global_search",
    )
    category_labels = {
        "all": tr("All", "Tutti"),
        "universe": tr("Universes", "Universi"),
        "saga": tr("Sagas", "Saghe"),
        "thematic": tr("Thematic cycles", "Cicli tematici"),
    }
    category = c2.selectbox(
        tr("Type", "Tipo"),
        ["all", "universe", "saga", "thematic"],
        format_func=category_labels.__getitem__,
        key="sagas_global_category",
    )

    completed = [s for s in data["completed_sagas"] if _matches_filters(s, query, category)]
    incomplete = [s for s in data["started_sagas"] if _matches_filters(s, query, category)]

    tab_completed, tab_incomplete = st.tabs([
        f"🏆 {tr('Completed sagas', 'Saghe completate')} ({len(completed)})",
        f"🎬 {tr('Sagas to complete', 'Saghe da completare')} ({len(incomplete)})",
    ])

    with tab_completed:
        _render_completed_section(completed)

    with tab_incomplete:
        _render_incomplete_section(incomplete)
