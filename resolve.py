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

        return http_status.strip(), url_effective, url.strip()
    except subprocess.CalledProcessError as e:
        return "Error", url.strip(), url.strip()

# Click command to process the file
@click.command()
@click.argument('file', type=click.File('r'))
def process_urls(file):
    urls = [line.strip() for line in file if line.strip()]
    output_file = "result.txt"
    
    # Write CSV header
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Status Code", "Resolved URL", "Original URL"])
    
    # Use ThreadPoolExecutor to fetch URLs in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(fetch_url_info, url): url for url in urls}
        for future in as_completed(future_to_url):
            http_status, url_effective, original_url = future.result()
            # If the status code is 404, set the resolved URL to be the same as the original
            if http_status == "404":
                url_effective = original_url
            # Write the result to the output file
            with open(output_file, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([http_status, url_effective, original_url])

if __name__ == '__main__':
    process_urls()
