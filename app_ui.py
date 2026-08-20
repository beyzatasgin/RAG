"""Turkish single-user Streamlit UI for the fully local Foundry RAG app."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import streamlit as st

from foundry_runtime import FoundryRuntime, FoundryRuntimeConfig
from ingestion_service import IngestionService
from main import answer_question
from storage import Storage
from ui_logic import (
    DEFAULT_UPLOAD_DIR,
    answer_view,
    ingestion_summary_view,
    read_db_status,
    safe_error_message,
    save_upload,
    validate_question,
    validate_settings,
)


def _default(environment_name: str, fallback: str) -> str:
    return os.environ.get(environment_name) or fallback


def _arguments(settings: dict[str, Any]) -> argparse.Namespace:
    return argparse.Namespace(
        db_path=settings["db_path"],
        question=None,
        top_k=settings["top_k"],
        min_score=settings["min_score"],
        context_budget=settings["context_budget"],
        max_output_tokens=settings["max_output_tokens"],
        model_cache_dir=settings["model_cache_dir"] or None,
        app_data_dir=settings["app_data_dir"] or None,
        logs_dir=settings["logs_dir"] or None,
        allow_download=False,
        debug=settings["debug"],
    )


def _render_status(db_path: str, model_cache_dir: str) -> None:
    try:
        status = read_db_status(db_path)
    except Exception as exc:
        st.error(safe_error_message(exc))
        return
    if not status.exists:
        st.warning("Runtime veritabanı henüz mevcut değil.")
    else:
        cols = st.columns(3)
        cols[0].metric("Belgeler", status.documents)
        cols[1].metric("Chunklar", status.chunks)
        cols[2].metric("Embeddingler", status.embeddings)
        st.caption(
            f"DB integrity: {status.integrity} · Model: {status.model_alias or '-'} · "
            f"Dimension: {status.dimensions or '-'}"
        )
    if model_cache_dir:
        st.caption(f"Model cache yapılandırıldı: {model_cache_dir}")
    else:
        st.warning("Model cache yolu yapılandırılmadı; işlem başlatılmadı.")


def _render_sources(view: Any, debug: bool) -> None:
    st.subheader("Kullanılan kaynaklar")
    if not view.sources:
        st.write("Kaynak yok.")
        return
    if not view.has_valid_inline_citation:
        st.warning(
            "Model cevap içinde geçerli bir kaynak etiketi üretmedi. "
            "Aşağıdaki kaynaklar retrieval sonuçlarından doğrulanmıştır."
        )
    for source in view.sources:
        st.write(f"{source.label} **{source.source}** · chunk {source.chunk_index}")
        if debug:
            st.caption(
                f"semantic={source.semantic_score:.4f} · "
                f"combined={source.combined_score:.4f}"
            )
    if debug and view.unknown_citations:
        st.warning("Bilinmeyen model etiketleri: " + ", ".join(view.unknown_citations))
    st.info("Model yanıtını aşağıdaki kaynaklarla kontrol edin.")


def render_app() -> None:
    st.set_page_config(page_title="Yerel RAG Asistanı", page_icon="📚", layout="centered")
    st.title("Yerel RAG Asistanı")
    st.write("Tamamen yerel Foundry Local RAG asistanı")
    st.caption("Normal kullanım offline ve model indirme kapalıdır. Modeller yalnızca işlem başlatıldığında yüklenir.")

    with st.sidebar:
        st.header("Ayarlar")
        db_path = st.text_input("DB yolu", _default("RAG_DB_PATH", "runtime_data/rag.db"))
        model_cache_dir = st.text_input("Model cache", _default("RAG_MODEL_CACHE_DIR", ""))
        app_data_dir = st.text_input("App data", _default("RAG_APP_DATA_DIR", ""))
        logs_dir = st.text_input("Log yolu", _default("RAG_LOGS_DIR", ""))
        top_k = st.number_input("top_k", 1, 10, 3)
        min_score = st.number_input("min_score", -1.0, 1.0, 0.2, 0.05)
        context_budget = st.number_input("Context bütçesi", 500, 20000, 7000, 500)
        max_output_tokens = st.number_input("Maksimum çıktı token", 32, 512, 192, 16)
        debug = st.toggle("Debug skorları", False)

    settings = {
        "db_path": db_path,
        "model_cache_dir": model_cache_dir,
        "app_data_dir": app_data_dir,
        "logs_dir": logs_dir,
        "top_k": int(top_k),
        "min_score": float(min_score),
        "context_budget": int(context_budget),
        "max_output_tokens": int(max_output_tokens),
        "debug": debug,
    }
    _render_status(db_path, model_cache_dir)

    qa_tab, documents_tab = st.tabs(["Soru-cevap", "Belge yönetimi"])
    with qa_tab:
        question = st.text_area("Sorunuz", placeholder="Örnek: Grand Slam turnuvaları hangileridir?")
        if st.button("Sor", type="primary"):
            try:
                clean = validate_question(question)
                validate_settings(
                    top_k=settings["top_k"],
                    min_score=settings["min_score"],
                    context_budget=settings["context_budget"],
                    max_output_tokens=settings["max_output_tokens"],
                )
                with st.spinner("Yerel modeller çalışıyor..."):
                    st.session_state["rag_answer"] = answer_view(
                        answer_question(_arguments(settings), clean)
                    )
            except Exception as exc:
                st.error(safe_error_message(exc))

        view = st.session_state.get("rag_answer")
        if view is not None:
            st.subheader("Cevap")
            st.write(view.answer)
            _render_sources(view, debug)

    with documents_tab:
        uploaded = st.file_uploader("Belge yükle", type=["txt", "md"])
        if uploaded is not None and st.button("Dosyayı kaydet"):
            try:
                saved = save_upload(uploaded.name, uploaded.getvalue(), overwrite=True)
                st.success(f"Kaydedildi: {saved.name} (aynı ad varsa güvenli biçimde güncellendi)")
            except Exception as exc:
                st.error(safe_error_message(exc))

        if st.button("Belgeleri indeksle"):
            try:
                if not model_cache_dir:
                    raise ValueError("Model cache yolu gerekli; indirme otomatik başlatılmaz.")
                config = FoundryRuntimeConfig(
                    app_name="local-rag-assistant",
                    model_cache_dir=model_cache_dir,
                    app_data_dir=app_data_dir or None,
                    logs_dir=logs_dir or None,
                )
                with st.spinner("Belgeler yerel olarak indeksleniyor..."):
                    with FoundryRuntime(config) as runtime:
                        client = runtime.get_embedding_client(allow_download=False)
                        summary = IngestionService(
                            Storage(db_path), model_alias=config.embedding_model_alias
                        ).ingest(Path(DEFAULT_UPLOAD_DIR), client, delete_missing=False)
                values = ingestion_summary_view(summary)
                st.session_state["ingestion_summary"] = values
            except Exception as exc:
                st.error(safe_error_message(exc))

        summary = st.session_state.get("ingestion_summary")
        if summary:
            st.subheader("İndeksleme özeti")
            st.json(summary)

    st.caption("Tek kullanıcılı yerel eğitim uygulamasıdır; eşzamanlı çok kullanıcılı sunucu için tasarlanmamıştır.")


if __name__ == "__main__":
    render_app()
