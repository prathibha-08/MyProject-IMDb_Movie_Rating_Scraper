🎬 IMDb Movie Scraper

A Python-based project that fetches movie details using the OMDb API and stores the data in a structured format (CSV file). This project demonstrates API integration, data extraction, and file handling in Python.

🚀 Features

Fetch movie details using OMDb API

Retrieve information such as:

🎬 Title

🎬 Director

🎬 Main Actors

🎬 Runtime

🎬 Plot

🎬 Poster URL

Save results into a CSV file

Simple and easy-to-use Python script

🧠 Technologies Used

Python

Requests

CSV module / Pandas

OMDb API

📂 Project Structure
IMDB-Movie-Scraper/
│
├── main.py          # Main script
├── movies.csv       # Output file
├── README.md        # Project documentation
└── requirements.txt # Required libraries

⚙️ How It Works

User enters a movie name.

The program sends a request to the OMDb API.

The API returns movie data in JSON format.

The script extracts required details.

Data is saved into a CSV file.

▶️ Installation & Setup

Clone the repository:

git clone https://github.com/your-username/imdb-movie-scraper.git


Navigate to the project folder:

cd imdb-movie-scraper


Install required libraries:

pip install -r requirements.txt


Add your OMDb API key inside the script:

api_key = "your_api_key_here"


Run the program:

python main.py

🎯 Objective

The objective of this project is to understand how APIs work and how real-time movie data can be fetched, processed, and stored using Python.
