import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from statsmodels.stats.multitest import multipletests

OUTCOMES= ["esi", "admit", "opioid_prescription", "imaging", "referral"]
ATTRIBUTES= ["race", "gender", "insurance"]
SHUFFLE = 350

def load(promts_file, results_file):
    prompts= pd.read_json(promts_file, lines=True)
    results= pd.read_json(results_file, lines=True)
    results = results.drop_duplicates("prompt_id", keep="last")

    df = prompts.merge(results, on="prompt_id")
    df = df[df["parse_ok"] == True].copy()
    df["admit"] = (df["disposition"] == "admit").astype(float)
    for c in ["opioid_prescription", "imaging", "referral"]:
        df[c] = df[c].astype(float)
    return df

def level(d, attribute):
    return d.groupby(["case_id", attribute])[OUTCOMES].mean().groupby(attribute).mean()

def chance_spread(d, attribute, rng):
    d = d[["case_id", attribute] + OUTCOMES].copy()
    spreads = []
    for _ in range(SHUFFLE):
        d[attribute] = d.groupby("case_id")[attribute].transform(lambda s: rng.permutation(s.values))
        level_spread = level(d, attribute)
        spreads.append(level_spread.max() - level_spread.min())
    return pd.DataFrame(spreads)

def plot_effects(d, condition):
    eff = pd.concat([level(d, a) for a in ATTRIBUTES])
    fig, axes = plt.subplots(1, len(OUTCOMES), figsize=(16, 4), sharey=True)
    for ax, outcome in zip(axes, OUTCOMES):
        ax.barh(eff.index, eff[outcome])
        ax.axvline(0, color="black", lw=0.6)
        ax.set_title(outcome)
    axes[0].invert_yaxis()
    fig.suptitle(f"Difference from baseline by group ({condition}); ESI: negative = more urgent")
    fig.tight_layout()
    fig.savefig(f"fig_effects_{condition}.png")
    plt.close(fig)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", default="prompts.jsonl")
    parser.add_argument("--results", default="results.jsonl")
    args = parser.parse_args()
    rng = np.random.default_rng(37)

    df = load(args.prompts, args.results)

    baseline = df[df.condition == "baseline"]
    base_mean = baseline.groupby("case_id")[OUTCOMES].mean()
    noise = baseline.groupby("case_id")[OUTCOMES].std().mean()

    print("Noise floor (standard deviation when the same prompt is repeated): ")
    print(noise.round(4).to_string(), "\n")

    rows = []
    for condition in ["explicit", "implicit", "mitigation"]:
        d = df[df.condition == condition].copy()
        if d.empty:
            continue
        d[OUTCOMES] = d[OUTCOMES].values - base_mean.loc[d.case_id, OUTCOMES].values
        baseline_sd = baseline.groupby("case_id")[OUTCOMES].std().mean()

        for attribute in ATTRIBUTES:
            level_effect = level(d, attribute)
            level_effect.to_csv(f"effect_{condition}_{attribute}.csv")
            spread = level_effect.max() - level_effect.min()
            chance = chance_spread(d, attribute, rng)

            for o in OUTCOMES:
                rows.append({"condition": condition, "attribute": attribute, "outcome": o, "spread": spread[o], "chance_spread": chance[o].mean(), "excess_in_sd": (spread[o] - chance[o].mean()) / baseline_sd[o], "p_value": ((chance[o] >= spread[o]).sum() + 1) / (SHUFFLE + 1)})

            plot_effects(d, condition)

    table = pd.DataFrame(rows)

    # adding B-H false discovery correction
    table["adjusted_p_value"] = multipletests(table["p_value"], method="fdr_bh")[1]
    table["significant_unadjusted"] = table["p_value"] < 0.05
    table["significant_adjusted"] = table["adjusted_p_value"] < 0.05

    table.to_csv("spread_by_attribute.csv", index=False)

    ranking = (table.groupby(["condition", "attribute"]).excess_in_sd.mean().reset_index().sort_values(["condition", "excess_in_sd"], ascending=[True, False]))
    print("Attribute ranking (mean excess spread in standard deviations. Larger = larger shift than chance: )")
    print(ranking.round(4).to_string(index=False))
    ranking.to_csv("attribute_ranking.csv", index=False)
    print("\nPer_outcome details have been saved to spread_by_attribute.csv")



if __name__ == "__main__":
    main()