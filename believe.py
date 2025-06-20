import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Colors usually associated with the platforms
color_mapping = {
    "YouTube UGC": "red",
    "YouTube Official Content": "red",
    "Apple Music": "pink",
    "Spotify": "green",
    "Amazon Premium": "orange",
    "Soundcloud": "orange",
    "YouTube Audio Tier": "red",
    "TikTok": "pink",
    "Amazon Prime": "orange",
    "Pandora": "blue",
    "Netease": "grey",
    "UMA (Vkontakte)": "blue",
    "Facebook / Instagram": "blue",
    "UMA (BOOM)": "blue",
    "Yandex": "green"
}

# Function to format the Quantity values
def format_quantity(value):
    if value < 1e3:
        return f"{value}"
    elif value < 1e6:
        return f"{value/1e3:.1f}K ({value:,.0f})"
    elif value < 1e9:
        return f"{value/1e6:.1f}M ({value:,.0f})"
    else:
        return f"{value/1e9:.1f}B ({value:,.0f})"

# Modifying the generate_hover_data function to:
# 1. Add total revenue from the platform.
# 2. Sort the platforms based on revenue in descending order.
def generate_hover_data_modified(row, df):
    country = row["Country / Region"]
    country_data = df[df["Country / Region"] == country]
    
    platforms_info = country_data[["Platform", "Quantity", "Unit Price", "Net Revenue", "Sales Month"]].values
    sorted_platforms_info = sorted(platforms_info, key=lambda x: x[3], reverse=True)[:20]  
    
    platform_details = []
    for platform, quantity, unit_price, net_revenue, sales_month in sorted_platforms_info:
        try:
            formatted_date = datetime.strptime(sales_month, "%Y/%m/%d").strftime("%B %Y")
        except ValueError:
            try:
                formatted_date = datetime.strptime(sales_month, "%Y-%m-%d").strftime("%B %Y")
            except ValueError:
                formatted_date = "Unknown Date"
        
        platform_details.append(f"{platform}: {quantity:,} (€{unit_price:.6f} per stream, €{net_revenue:.2f} total). Sales Month: {formatted_date}")
    
    return f"€{row['Net Revenue']:.2f}<br>{row['Percentage Revenue']}%<br>{row['Streams']} streams<br><br>" + "<br>".join(platform_details)




# Function to display top tracks
def show_top_tracks(df):
    # Filter and aggregate data
    df_filtered = df[df['Client Payment Currency'] == 'EUR']
    df_grouped = df_filtered.groupby('Release title').agg({'Net Revenue': 'sum'}).reset_index()
    df_grouped = df_grouped[df_grouped['Net Revenue'] >= 100].sort_values(by='Net Revenue', ascending=False)
    
    # Format the Net Revenue column
    df_grouped['Net Revenue'] = df_grouped['Net Revenue'].apply(lambda x: x)
    
    # Display top tracks
    if df_grouped.empty:
        st.write("No tracks have earned more than 100 EUR.")
    else:
        st.write("## Top Tracks by Earnings")
        
        selected_rows = st.multiselect("Select Releases to Calculate Total Revenue:", df_grouped.index.tolist(), format_func=lambda x: f"{df_grouped.loc[x, 'Release title']} (€{df_grouped.loc[x, 'Net Revenue']:.2f})")
        st.table(df_grouped.rename(columns={'Release title': 'Release Title'}).set_index('Release Title'))
        
        # Show total earnings for selected tracks
        if selected_rows:
            total_earnings = df_grouped.loc[selected_rows, 'Net Revenue'].sum()
            st.write(f"### Total Earnings for Selected Tracks: €{total_earnings:.2f}")

def load_csv_with_auto_delimiter(uploaded_file):
    """
    Load a CSV file and automatically determine the delimiter.
    """
    # Check the first line of the file to determine the delimiter
    first_line = uploaded_file.readline().decode('utf-8')
    if ";" in first_line and "," not in first_line:
        delimiter = ";"
    else:
        delimiter = ","
    
    # Reset the pointer to the start of the file
    uploaded_file.seek(0)
    
    # Load the CSV with the determined delimiter
    df = pd.read_csv(uploaded_file, delimiter=delimiter)

    # Automatically display top tracks table
    show_top_tracks(df)
    return df

# Title of the app
st.title("Analysis of Revenue Distribution")

# Add a file uploader to the app with a unique key
uploaded_file = st.file_uploader("Choose a CSV file", type="csv", key="unique_file_uploader_key")

# If a file is uploaded
if uploaded_file is not None:
    # Use the new function to load the CSV file
    df = load_csv_with_auto_delimiter(uploaded_file)

    # Add a text input for the release title
    release_title = st.text_input("Enter the release title")

    # If a release title is entered
    if release_title:
        # Filter the dataframe for the release title
        df_filtered = df[df["Release title"] == release_title]
        
        # Calculate total net revenue for the selected release title
        total_revenue = df_filtered["Net Revenue"].sum()
        
        # Display the total net revenue
        st.write(f"Total Revenue for Track '{release_title}': €{total_revenue:.2f}")
        
        # ------------------ Net Revenue by Platform ------------------
        platform_revenue = df_filtered.groupby(["Platform"]).agg({"Net Revenue": "sum", "Quantity": "sum"}).reset_index()
        platform_revenue = platform_revenue.sort_values(by="Net Revenue", ascending=False)

        # Calculate total streams for the song and format it
        total_streams_for_song = df_filtered["Quantity"].sum()
        total_streams_formatted = format_quantity(total_streams_for_song)

        # Add formatted total streams to hover data
        platform_revenue["Total Streams"] = total_streams_formatted
        platform_revenue["Streams"] = platform_revenue["Quantity"].apply(format_quantity)

        fig = px.bar(platform_revenue, x='Net Revenue', y='Platform', orientation='h', color='Platform',
             color_discrete_map=color_mapping, title=f"Net Revenue by Platform (Total Streams: {total_streams_formatted})",
             hover_data=['Streams', 'Total Streams'])

        st.plotly_chart(fig)

        
        # ------------------ Net Revenue by Country ------------------
        country_data = df_filtered.groupby(["Country / Region"]).agg({"Net Revenue": "sum", "Quantity": "sum"}).reset_index()
        country_data = country_data.sort_values(by="Net Revenue", ascending=False).head(30)
        total_net_revenue = country_data["Net Revenue"].sum()
        country_data["Percentage Revenue"] = ((country_data["Net Revenue"] / total_net_revenue) * 100).round(2)
        country_data["Streams"] = country_data["Quantity"].apply(format_quantity)
        country_data["Platform Details"] = country_data.apply(generate_hover_data_modified, df=df_filtered, axis=1)

        fig_country = px.bar(country_data, x='Country / Region', y='Net Revenue', title="Net Revenue by Country",
                             hover_data=['Streams', 'Percentage Revenue', 'Platform Details'], custom_data=['Platform Details'])
        fig_country.update_traces(hovertemplate='%{x}<br>%{customdata[0]}')
        
        st.plotly_chart(fig_country)
