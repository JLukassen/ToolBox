# Mobile Inventory Audit

This tool compares carrier-exported mobile device records against Microsoft Intune inventory.

## Features
- Detects matched vs missing IMEIs
- Applies manual and pattern-based exclusions
- Tags devices associated with disabled AD users
- Classifies shared/open devices and likely iPad inventory
- Generates summary workbooks and review outputs

## Inputs
- Carrier export
- Intune export
- Optional exclusions CSV
- Optional disabled AD users CSV

## Outputs
- Full audit workbook
- Action list
- Disabled-user review list
- Excluded items report
- Department summaries

## Tech
- Python
- Pandas
- OpenPyXL