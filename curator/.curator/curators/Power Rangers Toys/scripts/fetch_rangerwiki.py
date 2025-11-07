#!/usr/bin/env python3
"""Scrape Power Rangers toy data from RangerWiki."""

import re
import json
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin

BASE_URL = "https://powerrangers.fandom.com"
IMAGE_DIR = Path("images")
OUTPUT_FILE = "scraped_toylines.json"

SERIES_LIST = [
    "Mighty_Morphin_Power_Rangers",
    "Power_Rangers_Zeo",
    "Power_Rangers_Turbo",
    "Power_Rangers_in_Space",
    "Power_Rangers_Lost_Galaxy",
    "Power_Rangers_Lightspeed_Rescue",
    "Power_Rangers_Time_Force",
    "Power_Rangers_Wild_Force",
    "Power_Rangers_Ninja_Storm",
    "Power_Rangers_Dino_Thunder",
    "Power_Rangers_S.P.D.",
    "Power_Rangers_Mystic_Force",
    "Power_Rangers_Operation_Overdrive",
    "Power_Rangers_Jungle_Fury",
    "Power_Rangers_RPM",
    "Power_Rangers_Samurai",
    "Power_Rangers_Megaforce",
    "Power_Rangers_Dino_Charge",
    "Power_Rangers_Ninja_Steel",
    "Power_Rangers_Beast_Morphers",
    "Power_Rangers_Dino_Fury",
    "Power_Rangers_Cosmic_Fury"
]

def fetch_page(url):
    """Fetch wiki page with error handling."""
    try:
        response = requests.get(url, timeout=30, headers={"User-Agent": "PowerRangersCurator/1.0"})
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_product_number(text):
    """Extract 4-digit product number from text."""
    match = re.search(r'\b(\d{4})\b', text)
    return match.group(1) if match else None

def download_image(img_url, product_number):
    """Download image and return local path."""
    if not img_url:
        return None
    
    try:
        IMAGE_DIR.mkdir(exist_ok=True)
        ext = img_url.split('.')[-1].split('?')[0][:4]
        local_path = IMAGE_DIR / f"{product_number}.{ext}"
        
        if local_path.exists():
            return str(local_path)
        
        response = requests.get(img_url, timeout=30)
        response.raise_for_status()
        local_path.write_bytes(response.content)
        return str(local_path)
    except Exception as e:
        print(f"Failed to download image {img_url}: {e}")
        return None

def parse_toy_section(html, series_name):
    """Extract toy data from wiki page HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    toys = []
    
    # Look for tables with toy data
    tables = soup.find_all('table', class_=['wikitable', 'article-table'])
    
    for table in tables:
        rows = table.find_all('tr')[1:]  # Skip header
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) < 2:
                continue
            
            # Extract text from first few columns
            text_data = [col.get_text(strip=True) for col in cols[:4]]
            combined_text = ' '.join(text_data)
            
            product_number = extract_product_number(combined_text)
            if not product_number:
                continue
            
            # Extract image if present
            img_tag = row.find('img')
            img_url = urljoin(BASE_URL, img_tag['src']) if img_tag and img_tag.get('src') else None
            
            # Parse year from text
            year_match = re.search(r'(19\d{2}|20\d{2})', combined_text)
            year = year_match.group(1) if year_match else None
            
            # Detect scale
            scale = None
            if '5-inch' in combined_text.lower() or '5"' in combined_text:
                scale = '5-inch'
            elif '8-inch' in combined_text.lower() or '8"' in combined_text:
                scale = '8-inch'
            elif 'deluxe' in combined_text.lower():
                scale = 'Deluxe'
            
            toys.append({
                'product_number': product_number,
                'name': text_data[0] if text_data else f"{product_number} {series_name}",
                'series': series_name.replace('_', ' '),
                'description': combined_text[:500],
                'year': year,
                'scale': scale,
                'image_url': img_url,
                'source_url': f"{BASE_URL}/wiki/{series_name}"
            })
    
    return toys

def scrape_all_series():
    """Main scraping function."""
    all_toys = []
    
    for series in SERIES_LIST:
        print(f"Scraping {series}...")
        url = f"{BASE_URL}/wiki/{series}"
        html = fetch_page(url)
        
        if html:
            toys = parse_toy_section(html, series)
            print(f"  Found {len(toys)} toy lines")
            
            # Download images
            for toy in toys:
                if toy['image_url']:
                    local_path = download_image(toy['image_url'], toy['product_number'])
                    toy['image_local'] = local_path
                    time.sleep(0.5)  # Rate limiting
            
            all_toys.extend(toys)
        
        time.sleep(2)  # Rate limiting between pages
    
    # Save to JSON
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_toys, f, indent=2)
    
    print(f"\nTotal toys scraped: {len(all_toys)}")
    print(f"Saved to {OUTPUT_FILE}")
    return all_toys

if __name__ == '__main__':
    scrape_all_series()
