from playwright.sync_api import sync_playwright
import pandas as pd
import re

# Function to convert formatted volume (M, K, L, Cr) into pure numbers
def convert_to_number(value):
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

# URL of Curve Finance pools page
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

    # Debugging: Print extracted data
    print("Raw Pool Names:", pools[:6])
    print("Filtered Base APYs:", base_apys[:6])
    print("Numerical Volumes:", numerical_volumes[:6])

    # Ensure equal-length lists
    min_length = min(len(pools), len(base_apys), len(numerical_volumes))
    selected_pools = pools[:min_length]
    selected_apys = base_apys[:min_length]
    selected_volumes = numerical_volumes[:min_length]

    # Create DataFrame
    df = pd.DataFrame({"Pool Name": selected_pools, "Base APY": selected_apys, "Volume": selected_volumes})

    # Filter only the required pool names
    required_pools = ["USDC/MONEY Curve LP", "USDC/USDM", "4pool"]
    df = df[df["Pool Name"].isin(required_pools)]

    # Print final table
    print(df.to_string(index=False))

    browser.close()
