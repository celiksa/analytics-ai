import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pdfkit
import time
import os
from collections import deque
import logging
from datetime import datetime

class WebsiteCrawler:
    def __init__(self, start_url, output_file="documentation.pdf"):
        self.start_url = start_url
        self.domain = urlparse(start_url).netloc
        self.output_file = output_file
        self.visited = set()
        self.queue = deque([start_url])
        self.all_text = []
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('crawler.log')
            ]
        )

    def is_valid_url(self, url):
        parsed = urlparse(url)
        return (
            parsed.netloc == self.domain and
            not url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip')) and
            '#' not in url
        )

    def extract_text(self, soup, url):
        """Extract all text content while maintaining basic structure"""
        print(f"\nExtracting text from: {url}")
        
        # Start with page title and URL
        text_content = []
        title = soup.find('title')
        text_content.append(f"\n\n{'='*80}\n")
        text_content.append(f"Page: {title.text if title else url}\n")
        text_content.append(f"URL: {url}\n")
        text_content.append(f"{'='*80}\n\n")

        # Get all elements with text
        for element in soup.stripped_strings:
            text = element.strip()
            if text:  # Only add non-empty text
                text_content.append(text)
                text_content.append("\n")  # Add newline for separation
                
        return "".join(text_content)

    def get_links(self, url):
        print(f"Fetching links from: {url}")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = set()
            for link in soup.find_all('a'):
                href = link.get('href')
                if href:
                    full_url = urljoin(url, href)
                    if self.is_valid_url(full_url):
                        links.add(full_url)
            
            print(f"Found {len(links)} valid links")
            return links
        
        except Exception as e:
            logging.error(f"Error getting links from {url}: {str(e)}")
            return set()

    def process_page(self, url):
        try:
            print(f"Processing: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = self.extract_text(soup, url)
            self.all_text.append(text_content)
            print("✓ Page text extracted successfully")
            
        except Exception as e:
            logging.error(f"Error processing {url}: {str(e)}")

    def save_to_pdf(self):
        print("\nCreating PDF...")
        try:
            # Create a temporary text file with all content
            temp_text = 'temp_combined.txt'
            with open(temp_text, 'w', encoding='utf-8') as f:
                f.write("\n\nPydantic Documentation\n\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("".join(self.all_text))
            
            # Convert text to PDF
            pdfkit.from_file(temp_text, self.output_file, options={
                'encoding': 'UTF-8',
                'margin-top': '25mm',
                'margin-right': '20mm',
                'margin-bottom': '25mm',
                'margin-left': '20mm',
                'footer-right': '[page]'
            })
            
            os.remove(temp_text)
            size = os.path.getsize(self.output_file)
            print(f"✓ PDF created successfully: {self.output_file} ({size/1024/1024:.1f} MB)")
            
        except Exception as e:
            logging.error(f"Error creating PDF: {str(e)}")

    def crawl(self, delay=2):
        print(f"Starting crawl of {self.start_url}")
        
        try:
            while self.queue:
                url = self.queue.popleft()
                if url in self.visited:
                    continue
                    
                self.visited.add(url)
                self.process_page(url)
                
                new_links = self.get_links(url)
                for link in new_links:
                    if link not in self.visited:
                        self.queue.append(link)
                
                time.sleep(delay)
            
            self.save_to_pdf()
            
        finally:
            print(f"\nCrawl completed")
            print(f"Pages processed: {len(self.visited)}")

def main():
    start_url = "https://ai.pydantic.dev/"
    output_file = "pydantic_documentation.pdf"
    
    crawler = WebsiteCrawler(start_url, output_file)
    crawler.crawl()

if __name__ == "__main__":
    main()