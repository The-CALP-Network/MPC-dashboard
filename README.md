# HNRP Analysis

Python project for pulling data from APIs and exporting to CSV format.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the main script:
```bash
python main.py
```

## Project Structure

```
hnrp-analysis/
├── main.py              # Main script
├── data/                # Output CSV files
├── requirements.txt     # Python dependencies
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Configuration

Add your API endpoints and configuration in `main.py` or create a `.env` file for sensitive data.

## Output

CSV files are saved in the `data/` directory with timestamps.
