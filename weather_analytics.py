import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import time
import plotly.express as px
import io
import csv

# Title and description
st.title("Weather analytics Web Application")
st.markdown('The data is sourced from https://meteostat.net')

st.sidebar.title('Filters and Navigation')

# Allow multiple file uploads
uploaded_files = st.sidebar.file_uploader(
    "Upload one or more Excel or CSV files", 
    type=["xlsx", "xls", "csv"], 
    accept_multiple_files=True
)

@st.cache_data(show_spinner="Loading data...")
def load_file(file):
    time.sleep(1)  # simulate processing delay

    # For remote URL (string)
    if isinstance(file, str):
        return pd.read_excel(file)
    
    filename = file.name.lower()

    if filename.endswith(('.xlsx', '.xls')):
        return pd.read_excel(file)
    
    elif filename.endswith('.csv'):
        # Auto-detect delimiter
        sample = file.read(2048).decode('utf-8', errors='ignore')
        file.seek(0)
        dialect = csv.Sniffer().sniff(sample)
        delimiter = dialect.delimiter

        return pd.read_csv(file, delimiter=delimiter)
    
    else:
        st.warning(f"Unsupported file format: {file.name}")
        return None

# Load and union all valid uploaded files
if uploaded_files:
    dataframes = []
    for file in uploaded_files:
        df = load_file(file)
        if df is not None:
            dataframes.append(df)

    # Check if all DataFrames have the same structure
    if all(df.columns.equals(dataframes[0].columns) for df in dataframes):
        weather_df = pd.concat(dataframes, ignore_index=True)
    else:
        st.error("Uploaded files do not have the same structure.")
        weather_df = None
else:
    default_url = 'https://github.com/ElshanAziz/streamlit/raw/refs/heads/main/weather_dataset.xlsx'
    weather_df = load_file(default_url)

# Display preview if loaded successfully
#if weather_df is not None:
    #st.dataframe(weather_df.head())

#def load_file(local_file):
    #time.sleep(3)
    #if local_file is not None:
        #weather_df = pd.read_excel(local_file)
    #else:
        #weather_df = pd.read_excel('https://github.com/ElshanAziz/streamlit/raw/refs/heads/main/weather_dataset.xlsx')
    #return weather_df

weather_df['date'] = pd.to_datetime(weather_df['date'], errors='coerce')
weather_df['year'] = weather_df['date'].dt.year.astype(str)
weather_df['month'] = weather_df['date'].dt.month.astype(str).str.zfill(2)
weather_df['month_name'] = weather_df['date'].dt.strftime('%B')
weather_df.rename(columns={'tavg':'temperature_average',
                           'tmin':'temperature_min',
                           'tmax':'temperature_max',
                           'prcp':'precipitation',
                           'wdir':'wind_direction',
                           'wspd':'wind_speed',
                           'wpgt':'wind_peak_gust',
                           'snow':'snow_depth',
                           'pres':'pressure',
                           'tsun':'total_sunshine_duration'
                           },inplace=True)
                           
# Define the month-to-season mapping
def get_season(month):
    month = int(month)
    if month in [12, 1, 2]:
        return 'Winter'
    elif month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    elif month in [9, 10, 11]:
        return 'Fall'

# Apply the mapping to create a new column 'season'
weather_df['season'] = weather_df['month'].apply(get_season)

# Define the month order
month_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

# Get unique years, months, seasons, and cities
years = weather_df['year'].unique().tolist()
months = weather_df['month_name'].unique().tolist()
seasons = weather_df['season'].unique().tolist()
cities = weather_df['city'].unique().tolist()

# Create select boxes for user input
selected_years = st.sidebar.multiselect('Select the year', years)
selected_months = st.sidebar.multiselect('Select the month', months)
selected_seasons = st.sidebar.multiselect('Select the season', seasons)
selected_cities = st.sidebar.multiselect('Select the city', cities)

# Create select boxes for X,Y,Z values
st.markdown('Choose parameters for 3D visualization')
numeric_columns = weather_df.select_dtypes(include=['number']).columns.tolist()
selected_x_var = st.selectbox('X value', numeric_columns)
selected_y_var = st.selectbox('Y value', numeric_columns)
selected_z_var = st.selectbox('Z value', numeric_columns)

# Filter DataFrame based on user selections
filtered_df = weather_df.copy()
if selected_cities:
    filtered_df = filtered_df[filtered_df['city'].isin(selected_cities)]
if selected_years:
    filtered_df = filtered_df[filtered_df['year'].isin(selected_years)]
if selected_months:
    filtered_df = filtered_df[filtered_df['month_name'].isin(selected_months)]
if selected_seasons:
    filtered_df = filtered_df[filtered_df['season'].isin(selected_seasons)]

# Ensure the filtered data is correct
#st.write("Filtered Data:", filtered_df)

# Aggregate data to get monthly average values
filtered_df['year_month'] = filtered_df['date'].dt.to_period('M').astype(str)  # Create a period column for year-month
aggregated_df = filtered_df.groupby(['city', 'season', 'year', 'year_month'], as_index=False).agg(
    {selected_x_var: 'mean', selected_y_var: 'mean', selected_z_var:'mean'}
)
aggregated_df.rename(columns={f'{selected_x_var}': f'{selected_x_var}_mean', f'{selected_y_var}': f'{selected_y_var}_mean', f'{selected_z_var}': f'{selected_z_var}_mean'}, inplace=True)

# Check the aggregated data
#st.write("Aggregated Data:", aggregated_df)

# Convert 'year_month' to a string for better display in the chart
#filtered_df['year_month'] = filtered_df['year_month'].astype(str)
#aggregated_df['year_month'] = aggregated_df['year_month'].astype(str)


# Sort aggregated DataFrame by year_month
filtered_df = filtered_df.sort_values(by=['year_month'])
aggregated_df = aggregated_df.sort_values(by=['year_month'])


# Create and display the Plotly 3D scatter plot
fig1 = px.scatter_3d(
    filtered_df,
    x=selected_x_var,
    y=selected_y_var,
    z=selected_z_var,
    color='city',  # Color points by country
    title=f'3D Scatter Plot of {selected_x_var}, {selected_y_var}, and {selected_z_var}'
)

st.plotly_chart(fig1)


# Create Plotly line chart
fig_line = px.line(
    aggregated_df,
    x='year_month',
    y=f'{selected_y_var}_mean',
    color='city',
    title=f"Average {selected_y_var} by Year and Month",
    labels={'year_month': 'Year-Month', f'{selected_y_var}_mean': f'Average {selected_y_var}'},
    markers=True  # Add markers to the lines
)

# Update layout for better visibility in dark themes
fig_line.update_layout(
    xaxis_title='Year-Month',
    yaxis_title=f'Average {selected_y_var}',
    xaxis_type='category',  # Set x-axis to categorical
    plot_bgcolor='rgba(0,0,0,0)',  # Transparent background for plot
    paper_bgcolor='rgba(0,0,0,0)',  # Transparent background for paper
    font_color='white',  # White color for text
    xaxis=dict(
        title_font_color='white',
        tickfont_color='white',
        tickangle=-45  # Rotate x-axis labels for better readability
    ),
    yaxis=dict(
        title_font_color='white',
        tickfont_color='white'
    )
)

# Display Plotly figure in Streamlit
st.plotly_chart(fig_line, use_container_width=True)



# Create Plotly box plot
fig_box = px.box(
    filtered_df,
    x='year_month',
    y=selected_y_var,
    color='city',
    title= f'Distribution of {selected_y_var} Per Month by City',
    labels={'year_month': 'Year-Month', selected_y_var: f'Daily {selected_y_var}'}
)

# Update layout for better visibility in dark themes
fig_box.update_layout(
    xaxis_title='Year-Month',
    yaxis_title=f'Daily {selected_y_var}',
    xaxis_type='category',  # Set x-axis to categorical
    plot_bgcolor='rgba(0,0,0,0)',  # Transparent background for plot
    paper_bgcolor='rgba(0,0,0,0)',  # Transparent background for paper
    font_color='white',  # White color for text
    xaxis=dict(
        title_font_color='white',
        tickfont_color='white',
        tickangle=-45  # Rotate x-axis labels for better readability
    ),
    yaxis=dict(
        title_font_color='white',
        tickfont_color='white'
    )
)
# Display Plotly figure in Streamlit
st.plotly_chart(fig_box, use_container_width=True)


# Create Plotly histogram
fig_hist = px.histogram(
    filtered_df,
    x=selected_y_var,
    color='city',
    title=f"Distribution of {selected_y_var}",
    labels={selected_y_var: f'{selected_y_var}'}
)

fig_hist.update_layout(
    xaxis_title=f'{selected_y_var}',
    yaxis_title='Count',
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font_color='white'
)

st.plotly_chart(fig_hist, use_container_width=True)

# Display the static table of aggregated data
st.subheader("Data Review")
st.table(aggregated_df)
#filtered_df.head()
