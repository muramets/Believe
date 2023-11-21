import streamlit as st
import pandas as pd
import requests

# Function to process the CSV data for music revenue analysis
def process_data(uploaded_file, video_platforms):
    # Read the CSV file
    data = pd.read_csv(uploaded_file, delimiter=';')

    # Convert Net Revenue to numeric format
    data['Net Revenue'] = pd.to_numeric(data['Net Revenue'].str.replace(',', '.'), errors='coerce')

    # Filter for specified video platforms only
    data = data[data['Platform'].isin(video_platforms)]

    # Dictionary to store results
    platforms_data = {}

    # Sum revenue for each track across all platforms
    track_total_revenues = data.groupby('Track title')['Net Revenue'].sum()

    for platform in video_platforms:
        # Filter data for each platform
        platform_data = data[data['Platform'] == platform]

        # Skip the platform if no data is found
        if platform_data.empty:
            continue

        # Calculate total revenue for the platform
        total_revenue = platform_data['Net Revenue'].sum()

        # Group data by track title and calculate revenue per track, sort by revenue
        tracks_revenue = platform_data.groupby('Track title')['Net Revenue'].sum().reset_index().sort_values(by='Net Revenue', ascending=False)

        # Reorder columns
        tracks_revenue = tracks_revenue[['Track title', 'Net Revenue']]

        # Store in dictionary
        platforms_data[platform] = {'Total Revenue': total_revenue, 'Tracks Revenue': tracks_revenue}

    # Sort platforms by total revenue
    sorted_platforms_data = dict(sorted(platforms_data.items(), key=lambda item: item[1]['Total Revenue'], reverse=True))

    # Sort tracks by total revenue
    sorted_tracks = track_total_revenues.sort_values(ascending=False).index.tolist()

    return sorted_platforms_data, sorted_tracks, track_total_revenues

def display_platform_revenues(platforms_data):
    # Отображение данных по каждой платформе
    for platform, data in platforms_data.items():
        st.subheader(f"{platform} - Total Revenue: €{data['Total Revenue']:.2f}")
        # Отображение таблицы для каждой платформы с доходами по трекам
        st.dataframe(data['Tracks Revenue'].reset_index(drop=True).rename(columns={'index': 'Rank'}), width=1000)

# Function to convert a number into a human-readable format
def human_readable_number(number):
    for unit in ['', 'K', 'M', 'B', 'T']:
        if abs(number) < 1000.0:
            return f"{number:3.1f}{unit}"
        number /= 1000.0
    return f"{number:.1f}P"

# Ваш API ключ
api_key = "AIzaSyD2o2ThPSZcfouOCjtNkUrQT0sBKlwnxJk"

# Функция для получения названий каналов с использованием YouTube API
def fetch_channel_views(df):
    session = requests.Session()
    channel_views = {}
    progress_bar = st.progress(0)
    video_ids = df['Content'][1:].tolist()  # Пропускаем первую строку с общими данными

    # Разбиваем список ID видео на группы по 50
    groups_of_video_ids = [video_ids[i:i + 50] for i in range(0, len(video_ids), 50)]
    for i, group in enumerate(groups_of_video_ids):
        apiUrl = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={','.join(group)}&key={api_key}"
        response = session.get(apiUrl)
        if response.status_code == 200:
            json_response = response.json()
            for item in json_response.get('items', []):
                channel_title = item['snippet']['channelTitle']
                # Получаем индекс видео из исходного списка video_ids
                video_id = item['id']
                video_id_index = video_ids.index(video_id) + 1  # +1, так как мы пропустили первую строку в df
                views = df.at[video_id_index, 'Views']
                channel_views[channel_title] = channel_views.get(channel_title, 0) + views
        # Обновляем прогресс бар после обработки каждой группы
        progress_bar.progress((i + 1) / len(groups_of_video_ids))
    progress_bar.empty()
    session.close()
    return channel_views

# Функция для отображения списка каналов в виде прокручиваемой таблицы
def display_channels_scrollable_table(channel_views, total_views, selected_track_revenue):
    channel_data = pd.DataFrame(list(channel_views.items()), columns=['Channel', 'Views'])
    channel_data['Percentage'] = (channel_data['Views'] / total_views) * 100
    # Расчет дохода для каждого канала в соответствии с процентом просмотров
    channel_data['Revenue'] = (channel_data['Percentage'] / 100) * selected_track_revenue
    channel_data.sort_values(by='Percentage', ascending=False, inplace=True)
    channel_data.reset_index(drop=True, inplace=True)
    channel_data.index = channel_data.index + 1
    channel_data['Views'] = channel_data['Views'].apply(human_readable_number)
    channel_data['Percentage'] = channel_data['Percentage'].apply(lambda x: f"({x:.2f}%)")
    st.dataframe(channel_data, width=1000, height=600)    

# Streamlit app combining both functionalities
def app():
    st.title('Music Revenue and YouTube Views Analysis')

    video_platforms = [
        'YouTube Music Premium', 'Youtube Shorts', 'Facebook / Instagram', 'Believe Rights Services (YouTube)',
        'TikTok', 'YouTube Official Music Content', 'Youtube Audio Tier', 'Youtube Audio Fingerprint'
    ]

    uploaded_file = st.file_uploader("Choose a Music Revenue CSV file", type="csv")
    if uploaded_file is not None:
        platforms_data, sorted_tracks, track_total_revenues = process_data(uploaded_file, video_platforms)

        # Dropdown to select a track should be at the top
        selected_track = st.selectbox("Select a Track", [''] + sorted_tracks)

        # If a track is selected, show its revenue right after the track selection
        if selected_track:
            total_revenue = track_total_revenues[selected_track]
            st.subheader(f"Revenue for '{selected_track}' across platforms: €{total_revenue:.2f}")

            # Display revenue per platform for the selected track
            platform_revenues = [(platform, data['Tracks Revenue'][data['Tracks Revenue']['Track title'] == selected_track]['Net Revenue'].sum()) for platform, data in platforms_data.items() if data['Tracks Revenue'][data['Tracks Revenue']['Track title'] == selected_track]['Net Revenue'].sum() > 0]
            for platform, revenue in sorted(platform_revenues, key=lambda x: x[1], reverse=True):
                st.write(f"{platform}: €{revenue:.2f}")

            # Checkbox to choose to distribute revenue across projects right after displaying revenue for the selected track
            if st.checkbox("I want to distribute revenue across projects"):
                # Создание списка платформ, содержащих "YouTube" в названии, без учета регистра
                youtube_platforms = [platform for platform in video_platforms if "youtube" in platform.lower()]

                # Установка этих платформ как выбранных по умолчанию в выпадающем списке
                selected_platforms = st.multiselect("Select platforms for revenue distribution", video_platforms, default=youtube_platforms)
                # Вычисление дохода от выбранного трека с выбранных платформ
                selected_track_revenue = sum([data['Tracks Revenue'][data['Tracks Revenue']['Track title'] == selected_track]['Net Revenue'].sum() for platform, data in platforms_data.items() if platform in selected_platforms])


                # Отображение суммы дохода для распределения
                st.write(f"Revenue from selected platforms: €{selected_track_revenue:.2f}")
                
                # Filter platform revenues based on selected platforms
                filtered_platform_revenues = {platform: revenue for platform, revenue in platform_revenues if platform in selected_platforms}

                # Upload CSV file for YouTube statistics
                st.title('YouTube Channel View Analysis')
                uploaded_file = st.file_uploader("Choose a CSV file", type='csv')
                if uploaded_file is not None:
                    df = pd.read_csv(uploaded_file)
                    total_views = df.at[0, 'Views']  # Extracting the total views from the first row, fourth column
                    channel_views = fetch_channel_views(df)
                    selected_track_revenue = sum([data['Tracks Revenue'][data['Tracks Revenue']['Track title'] == selected_track]['Net Revenue'].sum() for platform, data in platforms_data.items()])
                    display_channels_scrollable_table(channel_views, total_views, selected_track_revenue)

        # Now, display the overall platform revenues and tracks revenue after the track selection
        display_platform_revenues(platforms_data)

# Run the app
if __name__ == "__main__":
    app()
