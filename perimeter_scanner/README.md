# Perimeter Scanner

This tool performs lightweight external exposure checks against store firewall/public WAN targets.

## Features
- Reads asset inventory from CSV
- Scans approved and enabled assets only
- Checks common ports
- Performs TLS checks
- Generates CSV and Excel summaries
- Supports future Meraki API inventory refresh

## Inputs
- store_assets.csv

## Outputs
- Raw JSON results
- Summary CSV
- Summary Excel workbook

## Tech
- Python
- Pandas
- Requests
- SSL / Socket libraries