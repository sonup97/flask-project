from flask import Flask, render_template,request, redirect, url_for,session,jsonify
from string import ascii_uppercase
from flask_cors import CORS
import folium
import json
import datetime
from flask_pymongo import PyMongo
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from bson import ObjectId
import os
import requests
import random

app = Flask(__name__)
CORS(app)

app.config['MONGO_DBNAME'] = 'Hackmania'
app.config['MONGO_URI'] = 'mongodb+srv://nareshvaishnavrko11:nareshrko11@cluster0.hudqzdr.mongodb.net/Hackmania'
client = MongoClient('mongodb+srv://nareshvaishnavrko11:nareshrko11@cluster0.hudqzdr.mongodb.net/')
mongo = PyMongo(app)

db = client['Hackmania']
shopping_list_collection = db['cart']
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.secret_key = 'nareshrko10'
app.config['SESSION_COOKIE_SECURE'] = True  # Ensures session cookie is sent only over HTTPS (secure)
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevents access to the session cookie via JavaScript
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Session cookie sent with same-site requests (Lax or Strict)

api_key = '54f5fef66dd24f61a654f4f36667b65f'

# Function to fetch news using the API
def fetch_news(page, q):
    current_date = datetime.datetime.now()
    yesterday = current_date - datetime.timedelta(days=1)
    yesterday_date = yesterday.strftime('%Y-%m-%d')
    
   
    # yesterday_date = datetime.strptime('2023-07-29', '%Y-%m-%d')
    url = f'https://newsapi.org/v2/everything?q={q}&from={yesterday_date}&language=en&pageSize=20&page={page}&sortBy=popularity'
    headers = {'x-api-key': api_key}
    response = requests.get(url, headers=headers)
    news_data = response.json()
    articles = news_data.get('articles', [])
    cleaned_articles = [{'title': article['title'], 'description': article['description'], 'urlToImage': article['urlToImage'], 'url': article['url']} for article in articles]
    return cleaned_articles, news_data.get('totalResults', 0)


@app.route('/',methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/signin')
def signin():
    return render_template('signin.html')

@app.route('/sell')
def sell():
    return render_template('seller.html')

@app.route('/account', methods=['POST'])
def create_account():
    
    if request.method == 'POST':
        # Get form data
        fullName = request.form['full-name']
        Age = request.form['Age']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        
        # Check if a file was uploaded
        if 'Photo' in request.files :
            Photo = request.files['Photo']           
            # Securely save the uploaded photos to the defined folder
            filename = secure_filename(Photo.filename)
            Photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))    
        else:
            # Set photo to None or default image paths
            filename = None  
        
        # Insert data into MongoDB
        mongo.db.users.insert_one({
            'full-name': fullName,
            'Age': Age,
            'email': email,
            'phone': phone,
            'address': address,
            'Photo': filename ,
        })
        
        # Redirect to success page...
        return redirect(url_for('index'))
    else:
        return 'Error'
    
@app.route('/map', methods=['GET', 'POST'])
def display_map():

    if request.method == 'POST':
        district = request.form['district'].strip()

        # Query the MongoDB database for the latitude and longitude of the given district
        # and store the results in a list of dictionaries
        locations = list(mongo.db.Maps.find({'district': district, 'latitude': {'$exists': True}, 'longitude': {'$exists': True}}, {'_id': 0, 'latitude': 1, 'longitude': 1}))
        
        if not locations:
            return render_template('map.html', district=district, error='No records found for this district.')
        
        # Create a Folium map centered on the first location in the list
        map = folium.Map(location=[locations[0]['latitude'], locations[0]['longitude']], zoom_start=10)
        
        # Add markers for all the locations in the list
        for location in locations:
            # Query the MongoDB database for the user information
            user_info = mongo.db.Maps.find_one({'district': district, 'latitude': location['latitude'], 'longitude': location['longitude']})
            
            # Create the URL for the farmer's profile using the farmer's ID
            profile_url = url_for('farmer_profile', farmer_id = str(user_info['_id']))
            
            # Modify the popup HTML to include the "More Info" link leading to the farmer's profile
            popup_html = f"""
            <div style="width: 300px;">
                <h3 style="margin: 0; padding: 10px; background-color: #00704A; color: #FFF; text-align: center; font-size: 20px;">
                    {user_info['name']}
                </h3>
                <div style="padding: 10px;">
                    <p style="margin: 0; margin-bottom: 5px; font-size: 16px;">Phone: {user_info['phone_number']}</p>
                    <p style="margin: 0; margin-bottom: 5px; font-size: 16px;">Email ID: {user_info['email']}</p>
                    <p style="margin: 0; margin-bottom: 5px; font-size: 16px;"> Timing: {user_info['open_hours']}</p>
                    <p style="margin: 0; margin-bottom: 5px; font-size: 16px;">Currently: {user_info['Open/Closed']}</p>
                    <p style="margin: 0; margin-bottom: 5px; font-size: 16px;">Pickup and Drop: {user_info['Online Grocery Pickup Service Offered']}</p>
                    <p style="margin: 0; margin-bottom: 5px; font-size: 16px;">Home Delivery: {user_info['Grocery Delivery Service Offered']} </p>
                    <div style="text-align: center;">
                        <a href='{profile_url}' target='_blank' style="color: #002F6C; text-decoration: none; font-size: 13px; display: inline-block;">More Info</a>
                    </div>
                </div>
            </div>
            """  # Add a marker with the pop-up to the map
            folium.Marker(location=[location['latitude'], location['longitude']], popup=popup_html).add_to(map)
        
        # Convert the map to HTML and pass it to the template
        map_html = map._repr_html_()
        return render_template('map.html', district=district, map_html=map_html)

    # If the request method is not 'POST', return the default map page
    return render_template('map.html', district='', map_html='', error='')

@app.route('/me/<farmer_id>')
def my_profile(farmer_id):
    # Check if the user is logged in by verifying the 'farmer_id' in the session
    logged_in_farmer_id = session.get('farmer_id')

    # Fetch the farmer's details from MongoDB using the given ID
    farmer_info = mongo.db.users.find_one({'_id': ObjectId(farmer_id)})

    if farmer_info:
        # If the user is logged in, allow them to view any farmer profile
        if logged_in_farmer_id:
            return render_template('myprofile.html', farmer_info=farmer_info)
        else:
            return "Access denied ! Log in first"
    else:
        return "Farmer not found"
    
@app.route('/farmer/<farmer_id>')
def farmer_profile(farmer_id):
    # Check if the user is logged in by verifying the 'farmer_id' in the session
    logged_in_farmer_id = session.get('farmer_id')

    # Fetch the farmer's details from MongoDB using the given ID
    farmer_info = mongo.db.Maps.find_one({'_id': ObjectId(farmer_id)})

    if farmer_info:
        # If the user is logged in, allow them to view any farmer profile
        if logged_in_farmer_id:
            return render_template('s_profile.html', farmer_info=farmer_info)
        else:
            return "Access denied ! Log in first"
    else:
        return "Farmer not found"
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get the email from the form
        email = request.form['email']

        # Check if the email exists in the database
        farmer_info = mongo.db.users.find_one({'email': email})

        if farmer_info:
            # If the email exists, store the farmer_id in the session
            session['farmer_id'] = str(farmer_info['_id'])
            return redirect(url_for('index'))  # Redirect to home page after successful login
        else:
            # If the email is not found, show an error message or redirect to a registration page
            return "Email not found. Please sign up first."

    # If the request method is GET, render the login page (signin.html)
    return render_template('signin.html')
    
@app.route('/logout')
def logout():
    # Clear the session data (log out the user)
    session.clear()
    # Redirect the user to the home page
    return redirect(url_for('index'))

@app.route('/s_signup')
def s_signup():
    return render_template('s_signup.html')

@app.route('/s_ind')
def s_index():
    return render_template('s_index.html')

@app.route('/s_account', methods=['POST'])
def s_create_account():
    
    if request.method == 'POST':
        # Get form data
        fullName = request.form['full-name']
        Age = request.form['Age']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        
        
        # Check if a file was uploaded
        if 'Photo' in request.files :
            
            Photo = request.files['Photo']           
            # Securely save the uploaded photos to the defined folder
            filename = secure_filename(Photo.filename)
            Photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))    
        else:
            # Set photo and land_photo to None or default image paths
            filename = None  
        
        # Insert data into MongoDB
        mongo.db.sellers.insert_one({
            'full-name': fullName,
            'Age': Age,
            'email': email,
            'phone': phone,
            'address': address,           
            'Photo': filename ,
        })
        
        # Redirect to success page...
        return redirect(url_for('s_index'))
    else:
        return 'Error'
    
@app.route('/s_signin')
def s_signin():
    return render_template('s_signin.html')


@app.route('/s_login', methods=['GET', 'POST'])
def s_login():
    if request.method == 'POST':
        # Get the email from the form
        email = request.form['email']

        # Check if the email exists in the database
        farmer_info = mongo.db.sellers.find_one({'email': email})

        if farmer_info:
            # If the email exists, store the farmer_id in the session
            session['farmer_id'] = str(farmer_info['_id'])
            return redirect(url_for('s_index'))  # Redirect to home page after successful login
        else:
            # If the email is not found, show an error message or redirect to a registration page
            return "Email not found. Please sign up first."

    # If the request method is GET, render the login page (signin.html)
    return render_template('s_signin.html')

@app.route('/sellprod', methods=['POST'])
def sell_crops():
    if 'farmer_id' in session:
        if request.method == 'POST':
            # Get form data
            name =request.form['name']
            product_image = request.files['product_image']
            price_per_unit = request.form['price_per_unit']
            brand = request.form['brand']
            category = request.form['category']
            carbon = float(request.form['carbon'])
            water = float(request.form['water'])
            recycle = request.form['recycle']
            certify = request.form['certify']
            india = request.form['india']

            # Securely save the uploaded crop image to the defined folder
            product_image_filename = secure_filename(product_image.filename)
            product_image.save(os.path.join(app.config['UPLOAD_FOLDER'], product_image_filename))
            
            calculated_rating = str(5 - carbon/4 - water/100)

            # Insert trade data into the "trades" collection
            trade_data = {
                'seller_id': ObjectId(session['farmer_id']),
                'Product_Name':name,
                'image_url': product_image_filename,
                'price_per_unit': price_per_unit,
                'Brand': brand,
                'Category': category,
                'Carbon_Footprint_(kg CO2e)':carbon,
                'Water_Usage_(liters)':water,
                'Recyclability':recycle,
                'Certification':certify,
                'Made_in_India':india,
                'Sustainability_Rating': calculated_rating
            }
            mongo.db.images.insert_one(trade_data).inserted_id

            # Update the user's document in the "users" collection
            # mongo.db.users.update_one(
            #     {'_id': ObjectId(session['farmer_id'])},
            #     {'$push': {'trade.sell': trade_id}}
            # )
            # Redirect to the profile page after submission
            
            return redirect(url_for('s_index', farmer_id=session['farmer_id']))

    return "Access denied. Please log in."



# Function to fetch news using the API
def fetch_news(page, q):
    current_date = datetime.datetime.now()
    yesterday = current_date - datetime.timedelta(days=1)
    yesterday_date = yesterday.strftime('%Y-%m-%d')
    
   
    # yesterday_date = datetime.strptime('2023-07-29', '%Y-%m-%d')
    url = f'https://newsapi.org/v2/everything?q={q}&from={yesterday_date}&language=en&pageSize=20&page={page}&sortBy=popularity'
    headers = {'x-api-key': api_key}
    response = requests.get(url, headers=headers)
    news_data = response.json()
    articles = news_data.get('articles', [])
    cleaned_articles = [{'title': article['title'], 'description': article['description'], 'urlToImage': article['urlToImage'], 'url': article['url']} for article in articles]
    return cleaned_articles, news_data.get('totalResults', 0)

@app.route('/news')
def news():
    return render_template('news.html')

@app.route('/api/news', methods=['GET'])
def get_news():
    current_query = "Eco-Friendly Products"
    current_page = 1

    # Fetch news for the current query and page
    articles, total_results = fetch_news(current_page, current_query)

    # If no articles found, return a message
    if total_results == 0:
        return jsonify({'message': 'No news articles found for the query "Eco-Friendly Products" on the specified date.'})

    first_five_articles = articles[:3]
    return jsonify(first_five_articles)

@app.route('/farmer')
def farmindex():
    return render_template('findex.html')

@app.route('/payment')
def pay():
    return render_template('gateway.html')

@app.route('/highlights')
def highlights():
    return render_template('highlights.html')

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

# Handle form submissions
@app.route('/Register', methods=['GET', 'POST'])
def register():
    if 'farmer_id' in session:
        
        if request.method == 'POST':
            name = request.form['name']
            phone_number = request.form['phone_number']
            email = request.form['email']    
            district = request.form['district']   
            address = request.form['address']
            latitude = request.form['latitude']
            longitude = request.form['longitude']
            open_hours = request.form['open_hours']
            OpenClosed = request.form['Open/Closed']
            GroceryPickup = request.form['Online Grocery Pickup Service Offered']
            DeliveryService = request.form['Grocery Delivery Service Offered']       
            otherinfo = request.form['other-info']

            # Check if a file was uploaded
            if 'shop_photo' in request.files:
                # photo = request.files['photo']
                shop_photo = request.files['shop_photo']
                shop_photo_filename = secure_filename(shop_photo.filename)
                
                # photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                shop_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], shop_photo_filename))
            else:
                shop_photo_filename = None  # Or provide a default image path
            
            # Insert data into MongoDB
            seller_data={
                'seller_id': ObjectId(session['farmer_id']),
                'name':name,
                'phone_number': phone_number,
                'email': email,
                'district': district,
                'address': address,
                'latitude': latitude,
                'longitude': longitude,
                'open_hours':open_hours,
                'Open/Closed':OpenClosed,
                'Online Grocery Pickup Service Offered':GroceryPickup,
                'Grocery Delivery Service Offered':DeliveryService,
                'other-info':otherinfo
            }
            mongo.db.Maps.insert_one(seller_data).inserted_id 
            
            return redirect(url_for('index'))
        else:
            return 'Error'
        
    return "Access denied. Please log in."

@app.route('/buy')
def buy():
    crops = mongo.db.images.find()
    return render_template('buy.html',crops=crops)

@app.route('/buy_crops', methods=['GET', 'POST'])
def buy_crops():

    if request.method == 'POST':
        crop_name = request.form.get('crop_name', '').strip()
        if crop_name:
            # Query the "trades" collection to get listings for the searched crop
            crops_list = list(mongo.db.images.find({'Product_Name': crop_name}))

    return render_template('buy.html', crops_list=crops_list)

@app.route('/product/<product_id>')
def product_detail(product_id):
    # Fetch the product details from the database using the product_id
    product = mongo.db.images.find_one({'_id': ObjectId(product_id)})
    return render_template('product.html', product=product)


@app.route('/add_to_list', methods=['POST'])
def add_to_list():
    product_id = request.form.get('product_id')
    product = db.images.find_one({'_id': ObjectId(product_id)})

    if product:
        product['price_per_unit'] = float(product['price_per_unit'])  # Convert to float

        cart = db.cart
        product_without_id = {key: value for key, value in product.items() if key != '_id'}
        cart.insert_one(product_without_id)

    return redirect(url_for('buy'))

@app.route('/delete/<string:item_id>')
def delete_item(item_id):
    shopping_list_collection.delete_one({'_id': ObjectId(item_id)})
    return redirect('/shopping_list')

@app.route('/clear_all', methods=['POST'])
def clear_all():
    shopping_list_collection.delete_many({})
    return redirect('/shopping_list')

@app.route('/shopping_list')
def shopping_list():
    shopping_list = list(shopping_list_collection.find())
    total_price = sum([product['price_per_unit'] for product in shopping_list])
    return render_template('shopping_list.html', shopping_list=shopping_list, total_price=total_price)

# @app.route("/thrift_profile/<event_id>")
# def thrift_profile(event_id):
#     try:
#         # Convert the event_id parameter to an ObjectId (assuming it's stored as ObjectId in MongoDB)
#         event_object_id = ObjectId(event_id)

#         # Query the MongoDB collection for the thrift event with the specified ObjectId
#         thrift_event = db.Thrift_1.find_one({"_id": event_object_id})

#         if thrift_event is None:
#             # Handle event not found
#             return render_template("event_not_found.html")

#         # You can then render the thrift event profile template here
#         return render_template("thrift_event_profile.html", thrift_event=thrift_event)

#     except Exception as e:
#         # Handle any potential exceptions, e.g., invalid ObjectId format
#         return render_template("event_not_found.html")

@app.route("/thrift_profile/<event_id>")
def event_details(event_id):
    try:
        # Convert the event_id parameter to an ObjectId (assuming it's stored as ObjectId in MongoDB)
        event_object_id = ObjectId(event_id)

        # Query the MongoDB collection for the event with the specified ObjectId
        event = db.Thrift_1.find_one({"_id": event_object_id})

        if event is None:
            # Handle event not found
            return ("event_not_found")
    
        return render_template("thrift_profile.html", event=event)
    except Exception as e:
        # Handle any potential exceptions, e.g., invalid ObjectId format
        return render_template("thrift_profile.html")

@app.route('/tmap', methods=['GET', 'POST'])
def display_tmap():

    if request.method == 'POST':
        district = request.form['district'].strip()

        # Query the MongoDB database for the latitude and longitude of the given district
        # and store the results in a list of dictionaries
        locations = list(mongo.db.Thrift_1.find({'district': district, 'latitude': {'$exists': True}, 'longitude': {'$exists': True}}, {'_id': 0, 'latitude': 1, 'longitude': 1}))
        
        if not locations:
            return render_template('thrift_map.html', district=district, error='No records found for this district.')
        
        # Create a Folium map centered on the first location in the list
        map = folium.Map(location=[locations[0]['latitude'], locations[0]['longitude']], zoom_start=10)
        
        # Add markers for all the locations in the list
        for location in locations:
            # Query the MongoDB database for the user information
            user_info = mongo.db.Thrift_1.find_one({'district': district, 'latitude': location['latitude'], 'longitude': location['longitude']})
            
            # Create the URL for the thrift event profile using the event's ID
            profile_url = url_for('event_details', event_id=str(user_info['_id']))
            
            # Modify the popup HTML to include the "More Info" link leading to the thrift event profile
            popup_html = f"""
            <div style="width: 300px;">
                <h3 style="margin: 0; padding: 10px; background-color: #00704A; color: #FFF; text-align: center; font-size: 20px;">
                    {user_info['name']}
                </h3>
                <div style="padding: 10px;">
                    <p style="margin: 0; margin-bottom: 5px; font-size: 16px;">Timing : {user_info['time']} </p>
                    <p style="margin: 0; margin-bottom: 5px; font-size: 16px;">Date : {user_info['date']} </p>
                    <div style="text-align: center;">
                        <a href='{profile_url}' target='_blank' style="color: #002F6C; text-decoration: none; font-size: 13px; display: inline-block;">More Info</a>
                    </div>
                </div>
            </div>
            """  # Add a marker with the pop-up to the map
            folium.Marker(location=[location['latitude'], location['longitude']], popup=popup_html).add_to(map)
        
        # Convert the map to HTML and pass it to the template
        map_html = map.get_root().render()
        return render_template('thrift_map.html', district=district, map_html=map_html)

    # If the request method is not 'POST', return the default map page
    return render_template('thrift_map.html', district='', map_html='', error='')

products = [
    "Solar-Powered Portable Charger",
    "Eco-Friendly Laptop",
    "Energy-Efficient Refrigerator",
    "Smart Thermostat",
    "Recycled Plastic Speaker",
    "Solar-Powered Desk Lamp",
    "Energy-Efficient Washing Machine",
    "Recycled Plastic Keyboard",
    "Solar-Powered Phone Charger",
    "Recycled Polyester Dress",
    "Organic Hemp T-Shirt",
    "Recycled PET Joggers",
    "Organic Cotton Hoodie",
    "Natural Hair Serum",
    "Organic Lip Balm",
    "Natural Face Cream",
    "Natural Perfume",
    "Vegan Eyebrow Pencil",
    "Herbal Hair Mask",
    "Sustainable Mascara"
]

# Generate random probabilistic data (example only)
def generate_random_probabilities(products):
    probabilities = {}
    for product in products:
        related_products = random.sample(products, random.randint(1, 5))
        if product in related_products:
            related_products.remove(product)  # Remove the product itself if it's in the list
        probabilities[product] = {related: random.uniform(0.1, 1.0) for related in related_products}
    return probabilities

# Calculate recommendations based on probabilistic data
def recommend_products(basket, probabilities, num_suggestions=5):
    if not basket:
        return []  # No basket, no recommendations

    # Calculate product scores based on basket and probabilities
    scores = {}
    for product in basket:
        if product in probabilities:
            for related_product, probability in probabilities[product].items():
                if related_product not in basket:
                    scores[related_product] = scores.get(related_product, 0) + probability

    # Sort products by score and return top recommendations
    recommendations = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:num_suggestions]
    return recommendations

# Example usage:
# Generate random probabilities (you can replace this with real data)
probabilities = generate_random_probabilities(products)

@app.route('/shopping_list')
def shoppinglist():
    # Fetch or generate the list of recommended products
    recommended_products = ["Solar-Powered Desk Lamp", "Solar-Powered Phone Charge", "Natural Perfume"]

    shopping_list = list(shopping_list_collection.find())
    total_price = sum([product['price_per_unit'] for product in shopping_list])

    # Calculate product recommendations based on items in the shopping cart
    recommendations = recommend_products([product['Product_Name'] for product in shopping_list], probabilities)

    return render_template("shopping_list.html", products=products, recommendations=recommendations, recommended_products=recommended_products, total_price=total_price)

if __name__ == '__main__':
    app.run(port=5000, debug=True)
