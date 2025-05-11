# Logzilla

## Overview
This is an educational tool designed to demonstrate how data collection and information gathering works on Windows systems. It shows the techniques that could potentially be used by malicious software, helping security professionals understand and defend against such methods.

## Features
- Screenshots capture
- Browser data collection (cookies, autofill)
- Network information gathering
- Data compression and export

## Educational Purpose
This tool is created **STRICTLY FOR EDUCATIONAL PURPOSES ONLY**. It demonstrates:
- How browser data is stored and can be accessed
- System information that is readily available to applications
- Methods of data exfiltration

## Usage
1. Clone the repository
2. Install required dependencies:

```bash
pip install pillow requests pywin32 cryptography psutil
```
3. To build the executable:

```bash
python build_exe.py
```
## Follow the prompts to customize your build with:
- Your Discord webhook URL
- Custom application name
- Custom error message
- Optional custom icon

## Requirements
- Windows operating system
- Python 3.6+
- Required libraries: pillow, requests, pywin32, cryptography, psutil

## Legal Disclaimer
This software is provided for educational purposes only. Adequate measures have been taken to ensure that the code in this repository is used for legitimate educational purposes. Any misuse of this software for malicious purposes is strictly prohibited.

**DO NOT USE THIS SOFTWARE TO:**
- Collect data from systems you do not own
- Access information without explicit permission
- Violate privacy laws or regulations

## License
This project is for educational purposes only and should not be used in production environments.