"""
Combine HPC Plan Requirements and MPC Requirements datasets
Merges data from 2020-2026 into a single comprehensive file
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import glob
import matplotlib.pyplot as plt
import numpy as np

# Directory paths
PLAN_DATA_DIR = Path(r"C:\Users\rcrew\CALP\CALP - 100 Python working folder\hnrp-analysis\plan_data")
MPC_DATA_DIR = Path(r"C:\Users\rcrew\CALP\CALP - 100 Python working folder\hnrp-analysis\mpc_data")
OUTPUT_DIR = Path(r"C:\Users\rcrew\CALP\CALP - 100 Python working folder\hnrp-analysis\combined_data")


def find_latest_file(pattern):
    """
    Find the most recent file matching the pattern
    """
    files = glob.glob(pattern)
    if not files:
        return None
    # Sort by modification time, most recent first
    files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    return files[0]


def load_hpc_data():
    """
    Load the latest HPC plan requirements and funding data
    """
    print("Looking for HPC plan data...")
    
    # Look in the plan_data directory
    pattern = str(PLAN_DATA_DIR / "ocha_hpc_2020_2026_plan_requirements_and_funding*.csv")
    hpc_file = find_latest_file(pattern)
    
    # Fallback to current directory if not found
    if not hpc_file:
        hpc_file = find_latest_file("ocha_hpc_2020_2026_plan_requirements_and_funding*.csv")
    
    if not hpc_file:
        raise FileNotFoundError(
            f"Could not find HPC plan data file. \n"
            f"Expected location: {PLAN_DATA_DIR}\n"
            f"Expected pattern: ocha_hpc_2020_2026_plan_requirements_and_funding*.csv"
        )
    
    print(f"✓ Found HPC data: {hpc_file}")
    df = pd.read_csv(hpc_file)
    print(f"  Loaded {len(df)} rows")
    return df


def load_mpc_data():
    """
    Load the latest MPC requirements and funding data
    """
    print("\nLooking for MPC data...")
    
    # Look in the mpc_data directory
    # NOTE: pattern uses _2020_2026_* (with trailing underscore) to avoid matching
    # single-year files like mpc_requirements_funding_2020_20260312...csv
    pattern = str(MPC_DATA_DIR / "mpc_requirements_funding_2020_2026_*.csv")
    mpc_file = find_latest_file(pattern)
    
    # Fallback to current directory if not found
    if not mpc_file:
        mpc_file = find_latest_file("mpc_requirements_funding_2020_2026_*.csv")
    
    if not mpc_file:
        raise FileNotFoundError(
            f"Could not find MPC data file. \n"
            f"Expected location: {MPC_DATA_DIR}\n"
            f"Expected pattern: mpc_requirements_funding_2020_2026_*.csv"
        )
    
    print(f"✓ Found MPC data: {mpc_file}")
    df = pd.read_csv(mpc_file)
    print(f"  Loaded {len(df)} rows")
    return df


def combine_datasets(df_hpc, df_mpc):
    """
    Combine HPC and MPC datasets on plan_id and year
    """
    print("\nCombining datasets...")
    
    # Ensure both have year and plan_id columns
    if 'year' not in df_hpc.columns or 'plan_id' not in df_hpc.columns:
        raise ValueError("HPC data missing required columns: year or plan_id")
    
    if 'year' not in df_mpc.columns or 'plan_id' not in df_mpc.columns:
        raise ValueError("MPC data missing required columns: year or plan_id")
    
    # Prepare HPC data - select and rename columns
    df_hpc_clean = df_hpc[[
        'year',
        'plan_id',
        'plan_version_id',
        'plan_code',
        'plan_name',
        'start_date',
        'end_date',
        'plan_group',
        'requirements_usd',
        'funded_usd',
        'coverage_pct'
    ]].copy()
    
    # Prepare MPC data - select and rename columns
    df_mpc_clean = df_mpc[[
        'year',
        'plan_id',
        'country',
        'mpc_requirements_usd',
        'mpc_funded_usd',
        'percent_funded'
    ]].copy()
    
    # Rename MPC coverage column for clarity
    df_mpc_clean = df_mpc_clean.rename(columns={
        'percent_funded': 'mpc_coverage_pct'
    })
    
    # Merge on plan_id and year (outer join to include all records)
    df_combined = pd.merge(
        df_hpc_clean,
        df_mpc_clean,
        on=['plan_id', 'year'],
        how='outer'
    )
    
    print(f"✓ Combined dataset has {len(df_combined)} rows")
    
    # Reorder columns to match specification
    column_order = [
        'year',
        'plan_id',
        'plan_name',
        'country',
        'plan_version_id',
        'plan_code',
        'start_date',
        'end_date',
        'plan_group',
        'requirements_usd',
        'funded_usd',
        'coverage_pct',
        'mpc_requirements_usd',
        'mpc_funded_usd',
        'mpc_coverage_pct'
    ]
    
    df_combined = df_combined[column_order]
    
    # Sort by year and plan requirements (descending)
    df_combined = df_combined.sort_values(
        ['year', 'requirements_usd'],
        ascending=[True, False],
        na_position='last'
    )
    
    return df_combined


def generate_summary(df):
    """
    Generate summary statistics for the combined dataset
    """
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    # Overall totals
    total_plans = df['plan_id'].nunique()
    total_req = df['requirements_usd'].sum()
    total_funded = df['funded_usd'].sum()
    total_mpc_req = df['mpc_requirements_usd'].sum()
    total_mpc_funded = df['mpc_funded_usd'].sum()
    
    overall_coverage = (total_funded / total_req * 100) if total_req > 0 else 0
    overall_mpc_coverage = (total_mpc_funded / total_mpc_req * 100) if total_mpc_req > 0 else 0
    
    print(f"\nOVERALL (2020-2026):")
    print(f"  Total unique plans: {total_plans}")
    print(f"  Total plan records: {len(df)}")
    print(f"  Total requirements: ${total_req:,.0f}")
    print(f"  Total funded: ${total_funded:,.0f}")
    print(f"  Overall coverage: {overall_coverage:.1f}%")
    print(f"  Total MPC requirements: ${total_mpc_req:,.0f}")
    print(f"  Total MPC funded: ${total_mpc_funded:,.0f}")
    print(f"  Overall MPC coverage: {overall_mpc_coverage:.1f}%")
    
    # Year-by-year breakdown
    print(f"\nYEAR-BY-YEAR BREAKDOWN:")
    print("-"*80)
    print(f"{'Year':<6} {'Plans':<8} {'Requirements':<18} {'Funded':<18} {'Coverage':<10} {'MPC Req':<18} {'MPC Fund':<18} {'MPC Cov':<10}")
    print("-"*80)
    
    for year in sorted(df['year'].dropna().unique()):
        year_data = df[df['year'] == year]
        plans = year_data['plan_id'].nunique()
        req = year_data['requirements_usd'].sum()
        funded = year_data['funded_usd'].sum()
        cov = (funded / req * 100) if req > 0 else 0
        mpc_req = year_data['mpc_requirements_usd'].sum()
        mpc_funded = year_data['mpc_funded_usd'].sum()
        mpc_cov = (mpc_funded / mpc_req * 100) if mpc_req > 0 else 0
        
        print(f"{int(year):<6} {plans:<8} ${req:>15,.0f} ${funded:>15,.0f} {cov:>8.1f}% ${mpc_req:>15,.0f} ${mpc_funded:>15,.0f} {mpc_cov:>8.1f}%")
    
    print("="*80)
    
    # Data completeness
    print(f"\nDATA COMPLETENESS:")
    print(f"  Plans with HPC data: {df['requirements_usd'].notna().sum()}")
    print(f"  Plans with MPC data: {df['mpc_requirements_usd'].notna().sum()}")
    print(f"  Plans with both HPC and MPC data: {(df['requirements_usd'].notna() & df['mpc_requirements_usd'].notna()).sum()}")
    print(f"  Plans with country information: {df['country'].notna().sum()}")


def save_combined_data(df, output_dir=None):
    """
    Save the combined dataset to CSV
    """
    # Use default output directory if none specified
    if output_dir is None:
        output_dir = OUTPUT_DIR
    else:
        output_dir = Path(output_dir)
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use timestamped filename to track when the file was generated
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"combined_plan_mpc_requirements_funding_2020_2026_{timestamp}.csv"
    filepath = Path(output_dir) / filename
    
    # Save to CSV
    df.to_csv(filepath, index=False)
    
    print(f"\n{'='*80}")
    print(f"✓ SUCCESS: Combined data saved to: {filepath}")
    print(f"{'='*80}\n")
    
    return filepath


def create_visualizations(df, output_dir=None):
    """
    Create bar charts for Requirements per year and MPC requirements per year
    """
    print("\nGenerating visualizations...")
    
    # Use default output directory if none specified
    if output_dir is None:
        output_dir = OUTPUT_DIR
    else:
        output_dir = Path(output_dir)
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Group by year and sum requirements
    yearly_data = df.groupby('year').agg({
        'requirements_usd': 'sum',
        'mpc_requirements_usd': 'sum'
    }).reset_index()
    
    # Sort by year
    yearly_data = yearly_data.sort_values('year')
    
    # Convert to billions for better readability
    yearly_data['requirements_billions'] = yearly_data['requirements_usd'] / 1_000_000_000
    yearly_data['mpc_requirements_billions'] = yearly_data['mpc_requirements_usd'] / 1_000_000_000
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Humanitarian Requirements Analysis (2020-2026)', fontsize=16, fontweight='bold')
    
    # Chart 1: Total Requirements per Year
    years = yearly_data['year'].astype(int)
    requirements = yearly_data['requirements_billions']
    
    bars1 = ax1.bar(years, requirements, color='#1f77b4', alpha=0.8, edgecolor='black', linewidth=1.2)
    ax1.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Requirements (Billions USD)', fontsize=12, fontweight='bold')
    ax1.set_title('Total Plan Requirements per Year', fontsize=14, fontweight='bold', pad=15)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_axisbelow(True)
    
    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        if not np.isnan(height):
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'${height:.1f}B',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Set x-axis to show all years
    ax1.set_xticks(years)
    ax1.set_xticklabels(years, rotation=0)
    
    # Chart 2: MPC Requirements per Year
    mpc_requirements = yearly_data['mpc_requirements_billions']
    
    bars2 = ax2.bar(years, mpc_requirements, color='#ff7f0e', alpha=0.8, edgecolor='black', linewidth=1.2)
    ax2.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax2.set_ylabel('MPC Requirements (Billions USD)', fontsize=12, fontweight='bold')
    ax2.set_title('MPC Requirements per Year', fontsize=14, fontweight='bold', pad=15)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    ax2.set_axisbelow(True)
    
    # Add value labels on bars
    for bar in bars2:
        height = bar.get_height()
        if not np.isnan(height) and height > 0:
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'${height:.2f}B',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Set x-axis to show all years
    ax2.set_xticks(years)
    ax2.set_xticklabels(years, rotation=0)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save figure with fixed filename (no timestamp)
    fig_filename = "requirements_analysis_charts.png"
    fig_filepath = Path(output_dir) / fig_filename
    plt.savefig(fig_filepath, dpi=300, bbox_inches='tight')
    print(f"✓ Charts saved to: {fig_filepath}")
    
    # Display the chart
    plt.show()
    
    return fig_filepath


def main():
    """
    Main execution function
    """
    print("\n" + "="*80)
    print("COMBINING HPC PLAN AND MPC REQUIREMENTS DATA (2020-2026)")
    print("="*80 + "\n")
    
    try:
        # Load datasets
        df_hpc = load_hpc_data()
        df_mpc = load_mpc_data()
        
        # Combine datasets
        df_combined = combine_datasets(df_hpc, df_mpc)
        
        # Generate summary
        generate_summary(df_combined)
        
        # Save combined data
        output_file = save_combined_data(df_combined)
        
        # Create visualizations
        chart_file = create_visualizations(df_combined)
        
        # Show sample of combined data
        print("\nSAMPLE OF COMBINED DATA (First 10 rows):")
        print("-"*80)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(df_combined.head(10).to_string(index=False))
        
        return output_file, chart_file
        
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        print("\nPlease ensure you have run the following scripts first:")
        print("  1. Plan_Funded_Requirements_2020_2026.py")
        print("  2. MPC_requirements_funded_2020_2026.py")
        return None
    
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()