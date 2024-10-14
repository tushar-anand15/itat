# ITAT Scraper

This project is a web scraper designed to extract data from the Income Tax Appellate Tribunal (ITAT) website. It automates the process of retrieving tribunal orders, solving captchas, and downloading related PDFs.

## Features

- Scrapes tribunal orders based on specified date ranges.
- Solves captchas automatically.
- Downloads PDFs of tribunal orders.
- Supports concurrent processing for faster data retrieval.
- Outputs data in CSV and JSON formats.

## Requirements

- Python 3.7+
- `requests`
- `beautifulsoup4`
- `pandas`
- `tqdm`
- `concurrent.futures`
- `itertools`

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/itat-scraper.git
   cd itat-scraper
   ```

2. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

   Ensure you have a `requirements.txt` file with the necessary dependencies listed.

## Usage

Run the script with the desired start and end dates:
'''bash
python main.py --start-date YYYY-MM-DD --end-date YYYY-MM-DD
'''


## Configuration

- **Date Range**: Specify the start and end dates using the `--start-date` and `--end-date` command-line arguments.
- **Output**: The script generates a CSV file with the scraped data and downloads PDFs to a specified directory.

## Project Structure

- `ITATScraper`: Main class encapsulating the scraping logic.
- `data/`: Directory for storing JSON and PDF files (ignored by Git).
- `.gitignore`: Specifies files and directories to be ignored by Git.
- `README.md`: Project documentation.

