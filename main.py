import argparse
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import json
import random
import re
import urllib3
from datetime import datetime, timedelta
from captcha_solver import solve_captcha
import concurrent.futures
import itertools
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Suppress only the InsecureRequestWarning from urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ITATScraper:
    def __init__(self, start_date, end_date):
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
        self.job_id = self.job_id_str()
        self.bench_values = [
            "199", "203", "205", "207", "209", "211", "213", "215", "217", "219", "221",
            "260", "201", "223", "225", "227", "229", "231", "233", "235", "237",
            "199", "239", "241", "243", "245", "247", "249", "251", "256", "258",
            "253"
        ]
        self.case_types = [
            "Black Money Appeal|BMA",
            "Cross Objection|CO",
            "Estate Duty Appeal|EDA",
            "Expenditure Tax Appeal|ETA",
            "Gift Tax Appeal|GTA",
            "High Court Decision|HCD",
            "Interest Tax Appeal|INTTA",
            "Income Tax Appeal|ITA",
            "Income Tax (International Taxation) Appeal|ITITA",
            "Income Tax (Search & Seizure) Appeal|ITSSA",
            "Income Tax (Transfer Pricing) Appeal|ITTPA",
            "Miscellaneous Application|MA",
            "Reference Appeal|RA",
            "Stay Application|SA",
            "Sur Tax Appeal|STA",
            "Security Transaction Tax Appeal|STTA",
            "TDS Appeal|TDS",
            "Wealth Tax Appeal|WTA"
        ]

    def job_id_str(self):
        return f"{random.randint(100000, 999999)}"

    def csrf(self):
        session = requests.Session()
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://itat.gov.in',
            'Referer': 'https://itat.gov.in/judicial/tribunalorders',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
            'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
        }
        url = "https://itat.gov.in/judicial/tribunalorders"
        response = session.get(url, headers=headers, verify=False, timeout=60*60*60)
        if response.status_code == 200:
            return session.cookies.get_dict()

    def get_captcha(self, cookies):
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Origin': 'https://itat.gov.in',
            'Referer': 'https://itat.gov.in/judicial/tribunalorders',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
        }
        while True:
            response = requests.post('https://itat.gov.in/judicial/get_captcha_tribu2', cookies=cookies, headers=headers, verify=False, timeout=60*60*60)
            match = re.search(r'src="([^"]+)"', response.text)
            if match:
                image_url = match.group(1)
                image_response = requests.get(image_url, cookies=cookies, headers=headers)
                image_data = BytesIO(image_response.content)
                captcha_value = solve_captcha(image_data)
                validation_response = requests.get(f'https://itat.gov.in/judicial/check_captcha_js_tribu2/{captcha_value}', headers=headers, cookies=cookies)
                if validation_response.json().get('success') is True:
                    return captcha_value
            else:
                print("Failed to extract image URL, please try again.")

    def format_date(self, input_date):
        if isinstance(input_date, str):
            try:
                date_obj = datetime.strptime(input_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Input date string must be in 'YYYY-MM-DD' format")
        elif isinstance(input_date, datetime):
            date_obj = input_date
        else:
            raise TypeError("Input must be a string in 'YYYY-MM-DD' format or a datetime object")
        return date_obj.strftime('%d-%b-%Y')

    def get_tribunal_orders(self, bench, case_type, date, _cookies, captcha):
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://itat.gov.in',
            'Referer': 'https://itat.gov.in/judicial/casestatus',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
            'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
        }
        data = {
            'csrf_test_name': _cookies['csrf_cookie_name'],
            'cvr2': 'false',
            'lq': '',
            'lqc': '',
            'bench2': bench,
            'appeal_type2': case_type,
            'filled_on': self.format_date(date),
            'userCaptcha2': captcha,
            'btnSubmit2': 'Submit2',
        }
        response = requests.post('https://itat.gov.in/judicial/casestatus', headers=headers, data=data, cookies=_cookies, verify=False, timeout=60*60*60)
        case_soup = [BeautifulSoup(response.content, 'html.parser')]
        btn_pages = case_soup[0].findAll('form', {'id':'enclosureform'})[-1].findAll('input',{'name':'btnPage'})[1:]
        if btn_pages:
            new_cases = self.process_subsequent_requests(case_soup[0], _cookies)
            case_soup.extend(new_cases)
        return case_soup

    def process_subsequent_requests(self, case_soup, _cookies):
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Content-Length": "508",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "itat.gov.in",
            "Origin": "https://itat.gov.in",
            "Referer": "https://itat.gov.in/judicial/casestatus",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Brave";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"'
        }
        csrf_test_name = _cookies['csrf_cookie_name']
        form_data = case_soup.findAll('form', {'id':'enclosureform'})[-1]
        lq_value = form_data.find('input',{'name':'lq'})['value']
        lqc_value = form_data.find('input',{'name':'lqc'})['value']
        btn_pages = form_data.findAll('input',{'name':'btnPage'})[1:]
        list_reqs = []
        for btn_page in btn_pages:
            req_dict = {'csrf_test_name': csrf_test_name, 'lq':lq_value, 'lqc': lqc_value, 'btnPage': btn_page['value']}
            response = requests.post('https://itat.gov.in/judicial/casestatus', headers=headers, data=req_dict, cookies=_cookies, verify=False, timeout=60*60*60)
            list_reqs.append(BeautifulSoup(response.content,'html.parser'))
        return list_reqs

    def process_cases(self, soup):
        table = soup.find('table', {'class': 'searchtble table table-striped table-hover'})
        if table is None:
            print("Not Applicable / Data Table Not Found")
            return {}
        data = []
        for row in table.find('tbody').find_all('tr'):
            columns = row.find_all('td')
            appeal_number = columns[0].text.strip()
            filed_by = columns[1].text.strip()
            appellant = columns[2].text.strip()
            respondent = columns[3].text.strip()
            assessment_year = columns[4].text.strip()
            bench = columns[5].text.strip()
            case_status = columns[6].text.strip()
            details = columns[7].find('button')['value']
            data.append({
                'Appeal_Number': appeal_number,
                'Filed_By': filed_by,
                'Appellant': appellant,
                'Respondent': respondent,
                'Assessment_Year': assessment_year,
                'Bench': bench,
                'Case_Status': case_status,
                'CASE_ID': details
            })
        return data

    def get_bench_city(self, bench_number):
        benches = [
            {"203": "Agra"}, {"205": "Ahmedabad"}, {"207": "Allahabad"}, {"209": "Amritsar"},
            {"211": "Bangalore"}, {"213": "Bilaspur"}, {"215": "Chandigarh"}, {"217": "Chennai"},
            {"219": "Cochin"}, {"221": "Cuttack"}, {"260": "Dehradun"}, {"201": "Delhi"},
            {"223": "Guwahati"}, {"225": "Hyderabad"}, {"227": "Indore"}, {"229": "Jabalpur"},
            {"231": "Jaipur"}, {"233": "Jodhpur"}, {"235": "Kolkata"}, {"237": "Lucknow"},
            {"199": "Mumbai"}, {"239": "Nagpur"}, {"241": "Panaji"}, {"243": "Patna"},
            {"245": "Pune"}, {"247": "Raipur"}, {"249": "Rajkot"}, {"251": "Ranchi"},
            {"256": "Surat"}, {"258": "Varanasi"}, {"253": "Visakhapatnam"}
        ]
        for bench in benches:
            if bench_number in bench:
                return bench[bench_number]
        return "Bench number not found"

    def extract_case_extended(self, __cookies, CASE_ID):
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://itat.gov.in',
            'Referer': 'https://itat.gov.in/judicial/tribunalorders',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
            'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
        }
        data = {
            'csrf_test_name': __cookies['csrf_cookie_name'],
            'btnDetail': CASE_ID,
        }
        response = requests.post('https://itat.gov.in/judicial/judicialdetail', cookies=__cookies, headers=headers, data=data)
        soup = BeautifulSoup(response.text, 'html.parser')
        case_details = []
        case_details_table = soup.find_all('table', {'class': 'table table-striped table-bordered manage-efects'})
        if case_details_table:
            case_details_table = case_details_table[0]
            rows = case_details_table.find_all('tr')
            current_case_detail = {}
            for row in rows:
                cols = row.find_all('td')
                for col in cols:
                    label = col.get('data-label')
                    text = col.get_text(strip=True).replace('\n', ' ').replace('  ', ' ')
                    if label in ['Appeal Number', 'Filed On', 'Assessment Year', 'Bench Allotted', 'Case Status']:
                        current_case_detail[label] = text
                    elif label == 'Appellant' or label == 'Respondent':
                        if 'Appellant' in current_case_detail:
                            current_case_detail['Respondent'] = text
                        else:
                            current_case_detail['Appellant'] = text
                if len(current_case_detail) >= 5:
                    case_details.append(current_case_detail)
                    current_case_detail = {}
        tabs_content_div = soup.find('div', class_='tabs-content')
        short_summary = {}
        tribunal_orders = []
        daily_orders = []
        if tabs_content_div:
            short_summary_section = tabs_content_div.find_all('section')[0]
            if short_summary_section:
                summary_table = short_summary_section.find('table')
                if summary_table:
                    rows = summary_table.find_all('tr')
                    if rows:
                        cols = rows[0].find_all('td')
                        if len(cols) >= 4:
                            short_summary = {
                                "Date of Last Hearing": cols[0].get_text(strip=True),
                                "Date of Next Hearing": cols[1].get_text(strip=True)
                            }
                        elif len(cols) == 2:
                            short_summary = {
                                "Date of Last Hearing": cols[0].get_text(strip=True),
                                "Date of Next Hearing": cols[1].get_text(strip=True)
                            }
            tribunal_orders_section = tabs_content_div.find_all('section')[1]
            if tribunal_orders_section:
                orders_table = tribunal_orders_section.find('table')
                if orders_table:
                    rows = orders_table.find_all('tr')
                    for row in rows[1:]:
                        cols = row.find_all('td')
                        if len(cols) >= 6:
                            tribunal_orders.append({
                                "Order Type": cols[0].get_text(strip=True),
                                "Date of Order": cols[1].get_text(strip=True),
                                "Pronounced On": cols[2].get_text(strip=True),
                                "Result": cols[3].get_text(strip=True),
                                "Order Link": cols[4].find('a')['href'] if cols[4].find('a') else None,
                                "Status / Remarks": cols[5].get_text(strip=True)
                            })
            daily_orders_section = tribunal_orders_section.find('dl', class_='accordion1')
            if daily_orders_section:
                accordion_items = daily_orders_section.find_all('dt')
                for item in accordion_items:
                    date = item.find('a').get_text(strip=True)
                    content = item.find_next('dd').get_text(" ", strip=True).replace('\n', ' ').replace('  ', ' ')
                    daily_orders.append({
                        "Date": date,
                        "Content": content
                    })
        data = {
            "Case Details": case_details,
            "Short Summary": short_summary,
            "Tribunal Orders": tribunal_orders,
            "Daily Orders": daily_orders
        }
        return json.dumps(data, indent=4)

    def get_bench_data(self, bench, case_type, date):
        print(f"PROCESSING: ---{bench}, {case_type}, {date}---")
        cookie_session = self.csrf()
        captcha = self.get_captcha(cookie_session)
        cases = self.get_tribunal_orders(bench, case_type, date, cookie_session, captcha)
        cases = [self.process_cases(i) for i in cases]
        flattened_cases = [item for sublist in cases for item in sublist]
        for case in flattened_cases:
            case['_add'] = {
                'date': date,
                'bench': self.get_bench_city(bench),
                'bench_code': bench,
                'case_type': case_type,
            }
            case_d = self.extract_case_extended(cookie_session, case['CASE_ID'])
            dir_path = os.path.join('data', self.job_id, 'json')
            os.makedirs(dir_path, exist_ok=True)
            file_path = os.path.join(dir_path, f"{case['CASE_ID']}.json")
            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(json.loads(case_d), json_file, ensure_ascii=False, indent=4)
            case['json_data'] = file_path
        return cases

    def download_pdf(self, pdf_url, save_path):
        base_url = f"{pdf_url}"
        response = requests.get(base_url, stream=True, verify=False)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            return os.path.basename(save_path)
        else:
            print(f"Failed to download: {base_url} - Status Code: {response.status_code}")
            return None

    def process_json_file(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                case_details = json.load(f)
        except Exception as e:
            print(f"Error reading JSON file {file_path}: {e}")
            return [], None
        json_filename = os.path.basename(file_path).replace(".json", "")
        pdf_dir = os.path.join("data", self.job_id, "pdfs", json_filename)
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_links = []
        for order in case_details.get("Tribunal Orders", []):
            if "Order Link" in order and order["Order Link"]:
                pdf_links.append(order["Order Link"])
        pdf_filenames = []
        for index, pdf_url in enumerate(pdf_links, start=1):
            pdf_filename = f"{index}.pdf"
            save_path = os.path.join(pdf_dir, pdf_filename)
            filename = self.download_pdf(pdf_url, save_path)
            if filename:
                pdf_filenames.append(os.path.join(pdf_dir, filename))
        return pdf_filenames, pdf_dir

    def download_pdfs_from_json(self, json_directory):
        print("Starting PDF download from JSON files...")
        json_files = [
            os.path.join(json_directory, f)
            for f in os.listdir(json_directory)
            if f.endswith(".json")
        ]
        pdf_paths = {}
        with ThreadPoolExecutor(max_workers=25) as executor:
            futures = {
                executor.submit(self.process_json_file, json_file): json_file
                for json_file in json_files
            }
            for future in as_completed(futures):
                json_file = futures[future]
                try:
                    pdf_filenames, pdf_dir = future.result()
                    if pdf_filenames:
                        json_identifier = os.path.basename(json_file).replace(".json", "")
                        pdf_paths[json_identifier] = (json_file, pdf_filenames)
                        print(
                            f"Downloading PDFs for case - {json_identifier}: {len(pdf_filenames)} files."
                        )
                    else:
                        print(f"No PDFs found for {json_file}.")
                except Exception as e:
                    print(f"Error processing {json_file}: {e}")
        return pdf_paths

    def append_paths_to_csv(self, csv_file, pdf_paths):
        print("Appending paths to CSV...")
        df = pd.read_csv(csv_file)
        df["PDFs"] = ""
        df["CASE_ID"] = df["CASE_ID"]
        for case_id, (json_path, pdf_files) in pdf_paths.items():
            matching_rows = df[df["CASE_ID"] == case_id]
            if matching_rows.empty:
                print(f"Error: {json_path}")
                continue
            row_index = matching_rows.index[0]
            df.at[row_index, "PDFs"] = ", ".join(pdf_files)
        df.drop(columns=["CASE_ID"], inplace=True)
        df.to_csv(csv_file, index=False)
        print("CSV update completed.")

    def flatten(self, nested_list):
        flattened = []
        for item in nested_list:
            if isinstance(item, list):
                flattened.extend(self.flatten(item))
            else:
                flattened.append(item)
        return flattened

    def run(self):
        date_range = [(self.start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range((self.end_date - self.start_date).days + 1)]
        all_cases = []
        combinations = itertools.product(self.bench_values, self.case_types)
        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
            future_to_bench = {
                executor.submit(self.get_bench_data, bench, case_type, date): (bench, case_type, date)
                for bench, case_type in combinations
                for date in date_range
            }
            for future in concurrent.futures.as_completed(future_to_bench):
                data = future.result()
                all_cases.append(data)
        csv_data = self.flatten(all_cases)
        df = pd.DataFrame(csv_data)
        csv_name = f"ITAT_{self.start_date.strftime('%Y-%m-%d')}_{self.job_id}_ALL_DATA.csv"
        df.to_csv(csv_name, index=False)
        json_directory = os.path.join("data", self.job_id, "json")
        pdf_paths = self.download_pdfs_from_json(json_directory)
        self.append_paths_to_csv(csv_name, pdf_paths)
        print("COMPLETE")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process ITAT data.")
    parser.add_argument('--start-date', type=str, required=True, help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end-date', type=str, required=True, help='End date in YYYY-MM-DD format')
    args = parser.parse_args()

    scraper = ITATScraper(args.start_date, args.end_date)
    scraper.run()