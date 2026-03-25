Open working folders - cd "C:\Users\ ... \hnrp-analysis”

Load venv - hnrp-venv\Scripts\activate

In Claude Cowork load the calp-fts-dashboard skill

Recall and confirm the latest dashboard load from \hnrp-analysis\plan_mpc_dashboard

Step 1: Run script [`Plan_Funded_Requirements_2020_2026.py`](../hnrp-analysis/Plan_Funded_Requirements_2020_2026.py)
  Checkfile has been updated in (..\hnrp-analysis\plan_data)
  
Step 2: Run script [`MPC_requirements_funded_2020_2026.py`](../hnrp-analysis/MPC_requirements_funded_2020_2026.py)
  Check file has been updated in (..\hnrp-analysis\mpc_data)
  
Step 3: Run script [`Combine_plan_mpc_data.py`](..hnrp-analysis/combine_plan_mpc_data.py)
  Check file loaded to (..\hnrp-analysis\combined_data)
  
Once run,update the skill.md file in (..\hnrp-analysis\skill file)

## Validation
The script validates against:
- Globalfunding and requirements here https://fts.unocha.org/plans/overview/2026
- Multipurpose cash here https://fts.unocha.org/global-sectors/16/summary/2026
- Individual response plans https://fts.unocha.org/plans/1502/summary
  - The above year and response codes will change to access all the data
