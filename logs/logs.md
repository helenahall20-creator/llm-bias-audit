## 11-19-2026 Pilot Run
- After completing query set up earlier this week I ran a pilot with 50 random prompts
- Results are good, all records were sucessfully parsed and there is a good variability

## 11-20-2026 Running Queries
- running query.py 3 times.
    - Run 1 = baseline and explicit details
    - Run 2 = implict details
    - Run 3 = mitigation statement
- generated 4.384 rows in results table

## 11-22-2026 Analyzing
- built an analysis pipeline that calculates baseline adjusted effects, demographic spread, and chance spread from shuffling group labels.
- First results - mean excess spread in SD
    - Explicit: insurance 0.055, race 0.019, gender 0.012
    - Implicit: insurance -0.018, race 0.029, gender -0.013
    - Mitigation: insurance 0.017, race 0.030, gender -0.015
- No attribute clearly stands out and the effects are small

## 11-24-2026 Observing Results
- Analyzed the spread by attribute for all combinations
- Found 6 combinations with a p < 0.05. 5 were explicit and one was mitigation
- Adding a FDR correction to account for the 45 comparisons
- None of the 6 results that appear to be significant survive the correction 


