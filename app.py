from flask import Flask, request, jsonify, render_template
import pandas as pd
from datetime import datetime, timedelta

#  Initializes a new Flask application
app = Flask(__name__)

# Load Data
df_basicin4 = pd.read_excel("Data.xlsx", sheet_name="Sheet_2")
df_roomtype = pd.read_excel("Data.xlsx", sheet_name="Sheet_3")
df_review = pd.read_excel("BookingHotelABSAViFormat.xlsx")
df_img = pd.read_excel("G2_RoomHotelPhotos.xlsx")
df_rv_ovv = pd.read_excel("OverviewRvInfo.xlsx")

# Define holiday periods
holiday_periods = [("28/04", "02/05"), ("01/06", "31/07"), ("01/09", "03/09")]

def calculate_total_price(row, checkin_datetime, checkout_datetime):
    total_price = 0
    current_date = checkin_datetime
    while current_date < checkout_datetime:
        daily_price = row['price']
        for start, end in holiday_periods:
            start_day, start_month = map(int, start.split('/'))
            end_day, end_month = map(int, end.split('/'))
            start_date = datetime(year=current_date.year, month=start_month, day=start_day)
            end_date = datetime(year=current_date.year, month=end_month, day=end_day)
            if start_date <= current_date <= end_date:
                daily_price *= 1.2  # Holiday price increase
                break
        total_price += daily_price
        current_date += timedelta(days=1)
    return total_price

@app.route('/')
def index():
    return render_template('index.html') # returns the HTML content of the index.html file l

@app.route('/search', methods=['POST']) # sending data securely from the client to the server.
def search(): # handles searching for hotel rooms based on the criteria specified by the user.
    data = request.get_json() # get the input data

    checkin_date = data['checkinDate']
    checkout_date = data['checkoutDate']

    checkin_datetime = datetime.strptime(checkin_date, "%d/%m/%Y")
    checkout_datetime = datetime.strptime(checkout_date, "%d/%m/%Y")

    budget = float(data['budget'])  # Receive and convert budget to float

    search_room_type = data['roomType']
    search_utilities = data['utilities']

    # Filter room types based on user input
    filtered_roomtype = df_roomtype[
        (df_roomtype['room_type'].str.contains(search_room_type)) &
        (df_roomtype['utilities'].apply(lambda x: all(util in x for util in search_utilities)))
    ]

    # Calculate total price for the stay duration and filter
    filtered_roomtype['total_price'] = filtered_roomtype.apply(
        calculate_total_price, args=(checkin_datetime, checkout_datetime), axis=1
    )
    filtered_roomtype = filtered_roomtype[filtered_roomtype['total_price'] <= budget]

    # Merge with basic info
    merged_details = pd.merge(filtered_roomtype, df_basicin4, on='hotel_name', how='inner')

    # Sort and handle reviews
    merged_details.sort_values(by='review_score', ascending=False, inplace=True)

    review_dict = df_review.groupby('hotel_name').apply(
        lambda x: dict(zip(x['review'], x['aspect_sentiment_label']))
    ).reset_index(name='reviews_label')

    # Merge review data
    results = pd.merge(merged_details, review_dict, on='hotel_name', how='inner')

    # Group images by hotel name and create a list of image dictionaries for each hotel
    grouped_images = df_img.groupby('hotel_name').apply(
        lambda x: x[['name', 'photo_link']].to_dict('records') if not x.empty else []).reset_index(name='images')

    # When merging, handle NaN by replacing with an empty list
    results = pd.merge(results, grouped_images, on='hotel_name', how='inner')
    results['images'] = results['images'].apply(lambda x: x if isinstance(x, list) else [])

    results = pd.merge(results, df_rv_ovv, on='hotel_name', how='inner')

    # Convert results to a suitable format for JSON response
    response_data = results.to_dict(orient='records') 
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True) # start the Flask application with debug 