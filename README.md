# Infrastructure Automation Toolbox

This repository contains Python-based tools for IT operations, infrastructure auditing, and security-focused automation.

## Projects

### Mobile Inventory Audit
Compares carrier mobile inventory against Microsoft Intune records to identify missing, unmanaged, excluded, disabled-user, and shared/open devices.

Key capabilities:
- IMEI normalization and matching
- Exclusion handling
- Disabled AD user tagging
- Shared/open device classification
- Excel and CSV reporting

### Perimeter Scanner
Performs lightweight external exposure checks against store/public firewall assets.

Key capabilities:
- Store asset inventory from CSV
- Targeted TCP port checks
- TLS inspection
- Report generation
- Planned Meraki API inventory integration

## Technologies
- Python
- Pandas
- OpenPyXL
- Microsoft Intune
- Microsoft Entra ID / Azure AD
- Cisco Meraki
- Microsoft 365 / Exchange Online
- PowerShell
- Requests / REST API integration

## Notes
This repository is sanitized for portfolio use. Real production data, employee information, IMEIs, and internal network details are excluded.