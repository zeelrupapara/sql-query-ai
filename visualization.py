import altair as alt
import pandas as pd
import streamlit as st
import re

def generate_visualization(sql_query, results, columns, chart_type, x_col, y_col):
    if not results or not columns:
        return None

    df = pd.DataFrame(results, columns=columns)

    if not x_col:
        return None

    try:
        if chart_type == "bar":
            if y_col:
                chart = alt.Chart(df).mark_bar().encode(
                    x=alt.X(x_col, type='nominal'),
                    y=alt.Y(y_col, type='quantitative')
                ).properties(title=f"Bar Chart of {y_col} by {x_col}")
            else:
                chart = alt.Chart(df).mark_bar().encode(
                    x=alt.X(x_col, type='nominal'),
                ).properties(title=f"Bar Chart of {x_col}")
            return chart
        elif chart_type == "line":
            if y_col:
                chart = alt.Chart(df).mark_line().encode(
                    x=alt.X(x_col, type='quantitative'),
                    y=alt.Y(y_col, type='quantitative')
                ).properties(title=f"Line Chart of {y_col} by {x_col}")
            else:
                chart = alt.Chart(df).mark_line().encode(
                    x=alt.X(x_col, type='quantitative'),
                ).properties(title=f"Line Chart of {x_col}")
            return chart
        elif chart_type == "scatter":
            if y_col:
                chart = alt.Chart(df).mark_scatter().encode(
                    x=alt.X(x_col, type='quantitative'),
                    y=alt.Y(y_col, type='quantitative')
                ).properties(title=f"Scatter Plot of {y_col} vs {x_col}")
                return chart
            else:
                st.error("Scatter plots require both X and Y axes.")
                return None
        elif chart_type == "histogram":
            chart = alt.Chart(df).mark_bar().encode(
                alt.X(x_col, type='quantitative', bin=True),
                y='count()'
            ).properties(title=f"Histogram of {x_col}")
            return chart
        else:
            return None
    except Exception as e:
        st.error(f"Error generating visualization: {e}")
        return None
