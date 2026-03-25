import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import plotly.subplots
from plotly.subplots import make_subplots
from pathlib import Path

st.set_page_config(
    page_title="Natura Financial Dashboard",
    page_icon="",
    layout="wide",
)
@st.cache_data

def shorten_number(x):
    """
    This function is used to create the shorten label so the values will be displayed in a rounded and more readable format.
    """
    # If the value is missing (NaN / None), show nothing
    if pd.isna(x):
        return ""

    # If the number is 1,000,000 or larger, convert to millions
    elif abs(x) >= 1_000_000:
        return f"{x / 1_000_000:.1f}M"

    # If the number is 1,000 or larger, convert to thousands
    elif abs(x) >= 1_000:
        return f"{x / 1_000:.0f}k"

    # Otherwise, keep the number as it is
    else:
        return f"{x:.0f}"

def load_balance_statement(folder_path):
    dfs_list = []

    for file in os.listdir(folder_path):
        if file.endswith(".xlsx"):
            file_path = os.path.join(folder_path, file)
            df_name = os.path.splitext(file)[0]

            df_active = pd.read_excel(file_path, sheet_name="DF Ind Ativo")
            df_passive = pd.read_excel(file_path, sheet_name="DF Ind Passivo")

            df_join = pd.merge(
                df_active,
                df_passive,
                how="outer",
                on="Codigo Conta"
            )

            df_join["source"] = df_name
            dfs_list.append(df_join)

    dfs = pd.concat(dfs_list, ignore_index=True)

    cols_base = [
        "Codigo Conta",
        "Descricao Conta_x",
        "Precisao_x",
        "Descricao Conta_y",
        "Precisao_y",
        "source"
    ]

    cols_remove = [
        "Valor Penultimo Exercicio_x",
        "Valor Antepenultimo Exercicio_x",
        "Valor Penultimo Exercicio_y",
        "Valor Antepenultimo Exercicio_y"
    ]

    year_map = {
        "2021": ("Valor Penultimo Exercicio_x", "Valor Penultimo Exercicio_y"),
        "2020": ("Valor Antepenultimo Exercicio_x", "Valor Antepenultimo Exercicio_y")
    }

    dfs_extra_years = []

    for year, (col_x, col_y) in year_map.items():
        df_year = (
            dfs[dfs["source"] == "2022"][cols_base + [col_x, col_y]]
            .rename(columns={
                col_x: "Valor Ultimo Exercicio_x",
                col_y: "Valor Ultimo Exercicio_y"
            })
        )

        df_year["source"] = year
        dfs_extra_years.append(df_year)

    dfs = dfs.drop(columns=cols_remove)
    dfs = pd.concat([dfs] + dfs_extra_years, ignore_index=True)

    dfs["Codigo Conta"] = dfs["Codigo Conta"].astype(str)
    dfs["MainGroup"] = dfs["Codigo Conta"].str[0]

    dfs_group1 = dfs[dfs["MainGroup"] == "1"].copy()
    dfs_group2 = dfs[dfs["MainGroup"] == "2"].copy()

    dfs_group1 = dfs_group1[[
        "Codigo Conta",
        "Descricao Conta_x",
        "Precisao_x",
        "Valor Ultimo Exercicio_x",
        "source",
        "MainGroup"
    ]].rename(columns={
        "Descricao Conta_x": "Descricao Conta",
        "Precisao_x": "Precisao",
        "Valor Ultimo Exercicio_x": "Valor Ultimo Exercicio"
    })

    dfs_group2 = dfs_group2[[
        "Codigo Conta",
        "Descricao Conta_y",
        "Precisao_y",
        "Valor Ultimo Exercicio_y",
        "source",
        "MainGroup"
    ]].rename(columns={
        "Descricao Conta_y": "Descricao Conta",
        "Precisao_y": "Precisao",
        "Valor Ultimo Exercicio_y": "Valor Ultimo Exercicio"
    })

    final_df = pd.concat([dfs_group1, dfs_group2], ignore_index=True)

    final_df = final_df.dropna(subset=["Descricao Conta", "Valor Ultimo Exercicio"])
    final_df = final_df.rename(columns={"source": "Year"})

    final_df["Valor Ultimo Exercicio"] = (
        final_df["Valor Ultimo Exercicio"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    final_df["Valor Ultimo Exercicio"] = pd.to_numeric(
        final_df["Valor Ultimo Exercicio"],
        errors="coerce"
    )

    final_df = final_df.rename(columns={
        "Codigo Conta": "Account Code",
        "Descricao Conta": "Account Description",
        "Precisao": "Precision",
        "Valor Ultimo Exercicio": "Value in Thousands BRL",
        "Year": "Year",
        "MainGroup": "Main Group"
    })

    final_df["Year"] = pd.to_numeric(final_df["Year"], errors="coerce")

    final_df["Account Description"] = final_df["Account Description"].replace({
        "Ativo Circulante": "Current Assets",
        "Passivo Circulante": "Current Liabilities"
    })

    return final_df

def build_main_assets_comparison_chart(df):
    df = df.copy()

    accounts_forAssets = {
        "Caixa e Equivalentes de Caixa": ["Cash and Cash Equivalents", "1.01.01"],
        "Aplicações Financeiras": ["Financial Assets", "1.01.02"],
        "Contas a Receber": ["Accounts Receivable", "1.01.03"],
    }

    # Translation map
    rename_accounts = {
        pt_name: values[0]
        for pt_name, values in accounts_forAssets.items()
    }

    # Apply translation
    df["Account Description"] = df["Account Description"].replace(rename_accounts)

    # Make Year categorical/string so Plotly uses discrete colors
    df["Year"] = df["Year"].astype(str)

    # Selected account codes
    selected_codes = [values[1] for values in accounts_forAssets.values()]

    # Filter only the selected accounts
    df_assets_3 = df[
        df["Account Code"].isin(selected_codes)
    ].copy().sort_values(["Account Description", "Year"])

    # Filter only 2020 and 2025
    df_assets_3_20_25 = df_assets_3[
        df_assets_3["Year"].isin(["2020", "2025"])
    ].copy()

    # Make labels
    df_assets_3_20_25["Label"] = (
        df_assets_3_20_25["Value in Thousands BRL"].apply(shorten_number)
    )

    color_map = {
        "2020": "darkred",
        "2025": "seagreen"
    }

    fig = px.bar(
        df_assets_3_20_25,
        x="Value in Thousands BRL",
        y="Account Description",
        orientation="h",
        color="Year",
        color_discrete_map=color_map,
        template="simple_white",
        text="Label",
        barmode="group",
        
    )

    fig.update_layout(
        hovermode="x",
        legend=dict(
            font=dict(size=16),
            title=dict(font=dict(size=18))
        ),
        xaxis_title_font=dict(size=20),
        yaxis_title_font=dict(size=20),
    )

    fig.update_traces(
        texttemplate="%{text}",
        textposition="outside",
        hovertemplate=None,
    )

    # Comment "Decrease in Financial Assets"
    fig.add_annotation(
        x=957433,  
        y="Financial Assets",
        text="Financial Assets Decrease",
        showarrow=True,
        arrowhead=6,
        arrowcolor="white",
        ax=150,
        ay=-50,
        borderwidth=0.5,
        borderpad=2,
        bordercolor="white",
        font=dict(size=16)
    )

    # Comment "Growth in Accounts Receivable"
    fig.add_annotation(
        x=4798044, 
        y="Accounts Receivable",
        text="Accounts Receivable Huge Growth",
        showarrow=True,
        arrowhead=6,
        ax=100,
        ay=-75,
        borderwidth=0.5,        
        borderpad=2,
        bordercolor="white",
        font=dict(size=16)
    )

    fig.update_yaxes(
    tickfont=dict(size=16)
    )
    
    fig.update_xaxes(
    tickfont=dict(size=16)
    )
    

    return fig

def build_current_assets_liabilities_chart(df): 
    df_current = df[df["Account Code"].isin(["1.01", "2.01"])].copy()
    df_current = df_current.sort_values(["Year", "Account Code"])
    df_current["Label"] = df_current["Value in Thousands BRL"].apply(shorten_number)

    colors = {
        "Current Assets": "palegreen",
        "Current Liabilities": "orange",
    }

    min_year = int(df_current["Year"].min())
    max_year = int(df_current["Year"].max())

    fig = px.line(
        df_current,
        x="Year",
        y="Value in Thousands BRL",
        color="Account Description",
        color_discrete_map=colors,
        markers=True,
        template="simple_white",
        labels="Label",
        width=50
    )

    fig.add_vrect(
        x0=2020,
        x1=2022,
        fillcolor="firebrick",
        opacity=0.25,
        line_width=0,
        layer="below"
    )

    fig.add_vrect(
        x0=2022,
        x1=2025,
        fillcolor="seagreen",
        opacity=0.25,
        line_width=0,
        layer="below"
    )

    fig.update_xaxes(
        title="Year",
        type="linear",
        tickmode="linear",
        dtick=1,
        range=[min_year, max_year]
    )

    fig.update_yaxes(
        title="Value in Thousands BRL"
    )

    fig.update_layout(
        title="Current Assets vs Current Liabilities",
        legend_title="Account Description",
        hovermode="x unified",
        xaxis_title_font=dict(size=20),
        yaxis_title_font=dict(size=20),
        xaxis=dict(tickfont=dict(size=16)),
        yaxis=dict(tickfont=dict(size=16)),
        legend=dict(font=dict(size=16))
    )

    fig.add_annotation(
        x=2022,
        y=3665000,
        showarrow=True,
        arrowhead=7,
        text="End of Pandemic Period",
        startarrowsize=3,
        font=dict(size=16),
        arrowcolor="white",
        arrowwidth=1.25
    )

    fig.update_traces(
        hovertemplate=None,
        line=dict(width=3),
        marker=dict(size=10),
    )

    fig.update_yaxes(
    tickfont=dict(size=16)
    )
    
    fig.update_xaxes(
    tickfont=dict(size=16)
    )

    return fig

def plot_long_term_assets_chart(df):
    accounts_forLongTAssets = {
        "Investimentos": ["Investments", "1.02.02"],
        "Imobilizado": ["Fixed Assets", "1.02.03"],
        "Passivo Não Circulante": ["Long Term Liabilities", "2.02"]
    }

    color_map = {
        "Investments": "seagreen",
        "Fixed Assets": "mediumturquoise",
    }

    # Create translation map
    rename_long_assets = {
        pt_name: values[0]
        for pt_name, values in accounts_forLongTAssets.items()
    }

    # Get selected account codes
    selected_codes_long_assets = [
        values[1] for values in accounts_forLongTAssets.values()
    ]

    # Filter dataframe
    df_longTAssets = df[
        df["Account Code"].isin(selected_codes_long_assets)
    ].copy()

    # Rename account descriptions
    df_longTAssets["Account Description"] = (
        df_longTAssets["Account Description"].replace(rename_long_assets)
    )

    # Create labels
    df_longTAssets["Label"] = (
        df_longTAssets["Value in Thousands BRL"].apply(shorten_number)
    )

    # Make sure Year is ordered cleanly
    df_longTAssets["Year"] = df_longTAssets["Year"].astype(str)
    df_longTAssets = df_longTAssets.sort_values("Year")

    # Keep only bar categories
    df_longTAssetsOnly = df_longTAssets[
        df_longTAssets["Account Description"].isin(["Investments", "Fixed Assets"])
    ].copy()

    category_orders={"Account Description": ["Investments", "Fixed Assets"]}

    # Create stacked bars
    fig = px.bar(
        df_longTAssetsOnly,
        x="Year",
        y="Value in Thousands BRL",
        color="Account Description",
        barmode="stack",
        color_discrete_map=color_map,
        template="simple_white",
        text="Label",
        category_orders=category_orders
    )

    fig.update_layout(
        bargap=0.2,
        bargroupgap=0.0,
        xaxis_title="Year",
        yaxis_title="Value in Thousands BRL",
        legend_title_text=""
    )

    fig.update_traces(
        marker_line_width=0,
        opacity=0.9,
        textposition="outside",
        textfont=dict(size=16),
        texttemplate="<b>%{text}</b>"

    )  

    # Extract line data
    df_ltl = df_longTAssets[
        df_longTAssets["Account Description"] == "Long Term Liabilities"
    ].copy()

    # Add line trace
    fig.add_trace(
        go.Scatter(
            x=df_ltl["Year"],
            y=df_ltl["Value in Thousands BRL"],
            name="Long Term Liabilities",
            line=dict(color="firebrick", width=3),
            marker=dict(size=8),
            opacity=0.60
        )
    )

    fig.update_layout(
        xaxis_title_font=dict(size=20),
        yaxis_title_font=dict(size=20),
        xaxis=dict(tickfont=dict(size=16)),
        yaxis=dict(tickfont=dict(size=16)),
        legend=dict(font=dict(size=16))
    )

    return fig

def plot_short_liabilities_percent_chart(df):

    accounts_forSL = {
        "Obrigações Sociais e Trabalhistas": ["Social and labor obligations", "2.01.01"],
        "Fornecedores": ["Suppliers", "2.01.02"],
        "Obrigações Fiscais": ["Tax obligations", "2.01.03"],
        "Empréstimos e Financiamentos": ["Loans and financing", "2.01.04"],
        "Outras Obrigações": ["Other liabilities", "2.01.05"]
    }

    color_map = {
        "Suppliers": "darkred",
        "Loans and financing": "indianred",
        "Tax obligations": "coral",
        "Social and labor obligations": "darkorange",
        "Other liabilities": "bisque"
    }

    # translation map and selected codes
    rename_short_l = {pt: v[0] for pt, v in accounts_forSL.items()}
    selected_codes_short_l = [v[1] for v in accounts_forSL.values()]

    # prepare dataframe
    df_shortLiab = df[
        df["Account Code"].isin(selected_codes_short_l)
    ].copy()

    df_shortLiab["Account Description"] = df_shortLiab["Account Description"].replace(rename_short_l)
    df_shortLiab["Year"] = df_shortLiab["Year"].astype(str)
    df_shortLiab = df_shortLiab.sort_values("Year", ascending=False)

    # yearly totals & percentages
    df_shortLiab["Year Total"] = df_shortLiab.groupby("Year")["Value in Thousands BRL"].transform("sum")
    df_shortLiab["Pct Total"] = df_shortLiab["Value in Thousands BRL"] / df_shortLiab["Year Total"]
    df_shortLiab["(%) of Current Liabilities"] = df_shortLiab["Pct Total"]
    df_shortLiab["Pct Label"] = (df_shortLiab["Pct Total"] * 100).round(1).astype(str) + "%"

    # enforce category order (stack + legend follow this order)
    order = ["Other liabilities", "Suppliers", "Loans and financing", "Tax obligations", "Social and labor obligations"]
    df_shortLiab["Account Description"] = pd.Categorical(
        df_shortLiab["Account Description"], categories=order, ordered=True
    )

    # build figure
    fig = px.bar(
        df_shortLiab,
        x="(%) of Current Liabilities",
        y="Year",
        orientation="h",
        color="Account Description",
        barmode="stack",
        text="Pct Label",
        template="simple_white",
        color_discrete_map=color_map,
        category_orders={"Account Description": order}
    )

    fig.update_layout(
        xaxis=dict(tickformat=".0%", title="Percent of current liabilities", tickfont=dict(size=16)),
        yaxis=dict(title="Year", tickfont=dict(size=16)),
        legend_title_text="",
        xaxis_title_font=dict(size=20),
        yaxis_title_font=dict(size=20),
        legend=dict(font=dict(size=16))
    )

    fig.update_traces(
        texttemplate="<b>%{text}</b>"
    )

    return fig

def build_bs_donut_2021_2025(df):
    accounts_forBS = {
        "Ativo Circulante": ["Current Assets", "1.01"],
        "Ativo Não Circulante": ["Long Term Assets", "1.02"],
        "Passivo Circulante": ["Current Liabilities", "2.01"],
        "Passivo Não Circulante": ["Long Term Liabilities", "2.02"],
        "Patrimônio Líquido": ["Equity", "2.03"]
    }

    color_map = {
        "Current Assets": "darkgreen",
        "Long Term Assets": "lightgreen",
        "Current Liabilities": "darkorange",
        "Long Term Liabilities": "firebrick",
        "Equity": "teal"
    }

    # Create translation map
    rename_bs = {
        pt_name: values[0]
        for pt_name, values in accounts_forBS.items()
    }

    # Get selected account codes
    selected_codes_bs = [
        values[1] for values in accounts_forBS.values()
    ]

    # Create filtered dataframe
    df_bs = df[
        df["Account Code"].isin(selected_codes_bs)
    ].copy()

    # Rename descriptions
    df_bs["Account Description"] = (
        df_bs["Account Description"].replace(rename_bs)
    )

    df_bs["Year"] = df_bs["Year"].astype(str)

    # Filter the two years
    df_2021 = df_bs[df_bs["Year"] == "2021"].copy()
    df_2025 = df_bs[df_bs["Year"] == "2025"].copy()
    
    #Array to sort the colors of the pie chart.
    account_order = ["1.01", "2.02", "2.01", "2.03", "1.02"]

    df_2021["Account Code"] = pd.Categorical(
        df_2021["Account Code"],
        categories=account_order,
        ordered=True
    )

    df_2025["Account Code"] = pd.Categorical(
        df_2025["Account Code"],
        categories=account_order,
        ordered=True
    )
        
    df_2021 = df_2021.sort_values("Account Code")
    df_2025 = df_2025.sort_values("Account Code")

    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{'type': 'domain'}, {'type': 'domain'}]],
        horizontal_spacing=0.05
    )

    fig.add_trace(
        go.Pie(
            labels=df_2021["Account Description"],
            values=df_2021["Value in Thousands BRL"],
            name="<b>2021</b>",
            sort=False,
            marker=dict(
                colors=[color_map[label] for label in df_2021["Account Description"]]
            )
        ),
        1, 1
    )

    fig.add_trace(
        go.Pie(
            labels=df_2025["Account Description"],
            values=df_2025["Value in Thousands BRL"],
            name="<b>2025</b>",
            sort=False,
            marker=dict(
                colors=[color_map[label] for label in df_2025["Account Description"]]
            )
        ),
        1, 2
    )

    fig.update_traces(
        hole=0.45,
        textinfo="label+percent",        
        hoverinfo="label+percent+name",
        texttemplate="<b>%{label}</b><br><b>%{percent}</b>",
        textposition="outside",
    )

    fig.update_layout(
        title_text="Balance Sheet Composition: 2021 vs 2025",
        template="simple_white",
        annotations=[
            dict(
                text="2021",
                x=sum(fig.get_subplot(1, 1).x) / 2,
                y=sum(fig.get_subplot(1, 1).y) / 2,
                font_size=18,
                showarrow=False,
                xanchor="center"
            ),
            dict(
                text="2025",
                x=sum(fig.get_subplot(1, 2).x) / 2,
                y=sum(fig.get_subplot(1, 2).y) / 2,
                font_size=18,
                showarrow=False,
                xanchor="center"
            )
        ],
        #Had to increase the size of the graph to match the others
        width=900,
        height=450,
        margin=dict(l=20, r=20, t=80, b=20),
        legend=dict(font=dict(size=14))
    )



    return fig

# -----------------------------
# Streamlit Page Set Up
# -----------------------------
st.title("Natura Financial After Pandemics")
st.markdown("Interactive financial data visualization built from Natura balance sheet files.")

BASE_DIR = Path(__file__).resolve().parent
folder_path = BASE_DIR / "SOURCE"
st.write("Using folder:", folder_path)


if os.path.exists(folder_path):
    df_balance = load_balance_statement(folder_path)

    Paragraph1 = "  During the pandemic, many retail businesses suffered with a low clients flow and other financial issues," \
    "Natura, the brazilian cosmetics company, was no excession."

    Paragraph2 = "  In this project, we will investigate, using data visualization, the impact of the pandemic in the company balance statements."
    
    Paragraph3 = "  Current Assets and Liabilities are useful to show how much does the company have in their easily accessible assets to cover liabilities." \
    "A comparison between them allow us to see if the company has enough to cover for their short term operations."

    Paragraph4 = "  With the current assets vs liabilities graph we can see how they suffered in 2021 with current liabilities" \
    "higher than their current assets, tendency that, if kept, could lead the company to bankrupcy." \
    "Thankfully, we also see they recovered, with a highlight in 2024"


    st.subheader("Current Assets vs Current Liabilities")
    st.markdown()
    fig_current = build_current_assets_liabilities_chart(df_balance)
    st.plotly_chart(fig_current, use_container_width=True)

    st.subheader("Main Assets Comparison - Pandemic and After Pandemic")
    fig_mainAssets = build_main_assets_comparison_chart(df_balance)
    st.plotly_chart(fig_mainAssets, use_container_width=True)

    st.subheader("Main Short Term Liabilities Along the Years")
    fig = plot_short_liabilities_percent_chart(df_balance)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Main Long Term Assets x Long Term Liabilities")
    fig_mainLTAxLTL = plot_long_term_assets_chart(df_balance)
    st.plotly_chart(fig_mainLTAxLTL, use_container_width=True)

    st.subheader("Balance Sheet - 2021 and 2025")
    fig_FSPieChart = build_bs_donut_2021_2025(df_balance)
    st.plotly_chart(fig_FSPieChart, use_container_width=True)


else:
    st.error("The provided folder path does not exist. Please check the path and try again.")
    