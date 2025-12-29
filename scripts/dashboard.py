# scripts/dashboard.py
import sqlite3
import pandas as pd
import streamlit as st
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "pm_speeches.db")


@st.cache_data
def load_metrics() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT
            m.chunk_id,
            m.pm_term_id,
            m.date,
            m.category,
            m.depth_level,
            m.origin_phase,
            s.pm_name,
            s.title
        FROM chunk_metrics AS m
        JOIN chunks AS c ON m.chunk_id = c.id
        JOIN speeches AS s ON c.speech_id = s.id
        ORDER BY m.date, m.origin_phase;
    """, conn)
    conn.close()
    return df


def main() -> None:
    st.title("首相発言ラダー：分析ダッシュボード（MVP）")

    df = load_metrics()

    # 絞り込み
    pm_names = ["すべて"] + sorted(df["pm_name"].unique().tolist())
    selected_pm = st.selectbox("首相を選択", pm_names)
    if selected_pm != "すべて":
        df = df[df["pm_name"] == selected_pm]

    st.subheader("カテゴリ別 発言チャンク数")
    cat_counts = df.groupby("category")["chunk_id"].count().reset_index(name="count")
    st.bar_chart(cat_counts.set_index("category"))

    st.subheader("origin_phase × depth_level の分布（表）")
    pivot = pd.pivot_table(
        df,
        values="chunk_id",
        index="depth_level",
        columns="category",
        aggfunc="count",
        fill_value=0,
    )
    st.dataframe(pivot)


if __name__ == "__main__":
    main()