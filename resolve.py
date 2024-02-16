import click
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
from urllib.parse import urlparse

# Function to extract the base part of the URL
def extract_base(url):
    netloc = urlparse(url).netloc
    netloc = netloc.split(':')[0]
    netloc = netloc.replace('www.', '')
    parts = netloc.split('.')
    if len(parts) > 2:
        return '.'.join(parts[1:-1])
    else:
        return parts[0]

# Function to execute curl and return status code, effective URL, and base change
def fetch_url_info(url):
    try:
        http_status = subprocess.check_output(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",  "--connect-timeout", "5", "--max-time", "7", url],
            universal_newlines=True).strip()
        
        if http_status not in ["000", "Error"]:
            url_effective = subprocess.check_output(
                ["curl", "-s", "-L", "-o", "/dev/null", "-w", "%{url_effective}", "--connect-timeout", "5", "--max-time", "7", url],
                universal_newlines=True).strip()
        else:
            url_effective = "Error"

        is_http = url_effective.startswith('http://')
        original_base = extract_base(url)
        final_base = extract_base(url_effective)
        base_changed = original_base != final_base

        return http_status, url_effective, url, int(is_http), base_changed
    except subprocess.CalledProcessError:
        return "Error", url, url, 0, False

# Click command to process the file
@click.command()
@click.option('--input-file', '-i', 'input_file', type=click.Path(exists=True), required=True, help='Input CSV file path.')
@click.option('--output-file', '-o', 'output_file', type=click.Path(), default=None, help='Output CSV file path (optional).')
def process_urls(input_file, output_file):
    with open(input_file, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]
    
    if output_file is None:
        output_file = input_file
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Status Code", "Resolved URL", "Original URL", "Is HTTP", "Base Changed"])
    
    with ThreadPoolExecutor(max_workers=16) as executor:
        future_to_url = {executor.submit(fetch_url_info, url): url for url in urls}
        for future in as_completed(future_to_url):
            http_status, url_effective, original_url, is_http, base_changed = future.result()
            if http_status == "404":
                url_effective = original_url
            with open(output_file, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([http_status, url_effective, original_url, is_http, base_changed])

if __name__ == '__main__':
    process_urls()
