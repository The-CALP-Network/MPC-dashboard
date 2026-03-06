"""
HNRP Analysis - API Data to CSV
Main script for pulling data from APIs and exporting to CSV
"""

import requests
import csv
from datetime import datetime


def fetch_api_data(api_url):
    """
    Fetch data from API endpoint
    
    Args:
        api_url (str): The API endpoint URL
    
    Returns:
        dict: JSON response from API
    """
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


def save_to_csv(data, filename):
    """
    Save data to CSV file
    
    Args:
        data (list): List of dictionaries containing data
        filename (str): Output CSV filename
    """
    if not data:
        print("No data to save")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"data/{filename}_{timestamp}.csv"
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        print(f"Data saved to {filepath}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")


def main():
    """Main execution function"""
    # TODO: Add your API URL here
    api_url = "https://api.example.com/data"
    
    print("Fetching data from API...")
    data = fetch_api_data(api_url)
    
    if data:
        print("Saving data to CSV...")
        save_to_csv(data, "hnrp_data")
        print("Complete!")


if __name__ == "__main__":
    main()
