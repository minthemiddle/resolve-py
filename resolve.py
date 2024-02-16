import click
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess

# Function to execute curl and return status code and effective URL
def fetch_url_info(url):
    try:
        # Check the status without following redirects
        http_status = subprocess.check_output(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
            universal_newlines=True)
        
        # If the status is not an error, follow redirects to get the final URL
        if http_status.strip() not in ["000", "Error"]:
            url_effective = subprocess.check_output(
                ["curl", "-s", "-L", "-o", "/dev/null", "-w", "%{url_effective}", url],
                universal_newlines=True).strip()
        else:
            url_effective = "Error"

        # Check if the resolved URL is using HTTP
        is_http = url_effective.startswith('http://')

        return http_status.strip(), url_effective, url.strip(), int(is_http)
    except subprocess.CalledProcessError as e:
        return "Error", url.strip(), url.strip(), 0


# Click command to process the file
@click.command()
@click.option('--input-file', '-i', 'input_file', type=click.Path(exists=True), required=True, help='Input CSV file path.')
@click.option('--output-file', '-o', 'output_file', type=click.Path(), default=None, help='Output CSV file path (optional).')
def process_urls(input_file, output_file):
    with open(input_file, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]
    
    if output_file is None:
        output_file = input_file
    
    # Write CSV header
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Status Code", "Resolved URL", "Original URL", "Is HTTP"])
    
    # Use ThreadPoolExecutor to fetch URLs in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(fetch_url_info, url): url for url in urls}
        for future in as_completed(future_to_url):
            http_status, url_effective, original_url, is_http = future.result()
            # If the status code is 404, set the resolved URL to be the same as the original
            if http_status == "404":
                url_effective = original_url
            # Write the result to the output file
            with open(output_file, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([http_status, url_effective, original_url, is_http])

if __name__ == '__main__':
    process_urls()
