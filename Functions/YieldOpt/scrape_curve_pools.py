from playwright.sync_api import sync_playwright
import pandas as pd
import re
import json

def convert_to_number(value):
    """Converts formatted numbers (M, K, L, Cr) into pure numerical values."""
    value = value.replace("$", "").replace(",", "").strip()  # Remove currency symbols and commas

    # Convert Lakh (L) to pure number
    if "L" in value:
        num = float(re.sub(r"[^\d.]", "", value))  # Extract numeric part
        return int(num * 100_000)  # Convert to 100,000

    # Convert Crore (Cr) to pure number
    elif "Cr" in value:
        num = float(re.sub(r"[^\d.]", "", value))
        return int(num * 10_000_000)  # Convert to 10 million

    # Convert Millions (M) to pure number
    elif "M" in value:
        num = float(re.sub(r"[^\d.]", "", value))
        return int(num * 1_000_000)

    # Convert Thousands (K) to pure number
    elif "K" in value:
        num = float(re.sub(r"[^\d.]", "", value))
        return int(num * 1_000)

    # Default case: Convert raw numbers to integer
    return int(value) if value.isdigit() else value

def scrape_curve_pools():
    """Scrapes Curve Finance pools and returns JSON data."""
    
    url = "https://curve.fi/dex/#/base/pools?filter=usd"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Run in headless mode
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")

        # Extract Pool Names
        pools = page.locator("//span[contains(@class, 'bpDKDq')]").all_inner_texts()

        # Extract Base APYs (ignoring APRs with → and CRV rewards)
        all_apys = page.locator("//span[contains(@class, 'hNyuCR')]").all_inner_texts()
        base_apys = [apy for apy in all_apys if re.match(r"^\d+\.\d+%$", apy)]  # Keep only xx.xx% format

        # Extract and convert Volumes to pure numbers
        raw_volumes = page.locator("//span[contains(@class, 'fIKwhp')]").all_inner_texts()
        numerical_volumes = [convert_to_number(vol) for vol in raw_volumes]

        # Extract additional US$ column (e.g., TVL)
        raw_usd_values = page.locator("//span[contains(@class, 'hNyuCR')]").all_inner_texts()
        usd_values = [convert_to_number(val) for val in raw_usd_values if val.startswith("US$")]

        # Ensure equal-length lists
        min_length = min(len(pools), len(base_apys), len(numerical_volumes), len(usd_values))
        selected_pools = pools[:min_length]
        selected_apys = base_apys[:min_length]
        selected_volumes = numerical_volumes[:min_length]
        selected_usd_values = usd_values[:min_length]

        # Create structured JSON data
        pool_data = []
        for i in range(min_length):
            pool_data.append({
                "Pool Name": selected_pools[i],
                "Base APY": selected_apys[i],
                "Volume": selected_volumes[i],
                "USD Value": selected_usd_values[i]  # Additional scraped column
            })

        browser.close()

    return json.dumps(pool_data, indent=4)

# Example usage
if __name__ == "__main__":
    data = scrape_curve_pools()
    print(data)
