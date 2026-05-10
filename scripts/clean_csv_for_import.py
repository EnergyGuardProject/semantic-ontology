import pandas as pd

def enforce_unique_nonempty_headers(input_csv, output_csv):
    df = pd.read_csv(input_csv)

    clean_cols = []
    cols_to_keep = []

    seen = set()

    for i, col in enumerate(df.columns):
        # Skip empty headers
        if col is None or str(col).strip() == "":
            print(f"Dropping column {i}: empty header")
            continue

        # Skip duplicates (keep only first instance)
        if col in seen:
            print(f"Dropping column {i}: duplicate header '{col}'")
            continue

        seen.add(col)
        clean_cols.append(col)
        cols_to_keep.append(i)

    # Keep only the valid columns
    df = df.iloc[:, cols_to_keep]
    df.columns = clean_cols

    df.to_csv(output_csv, index=False)
    print(f"\n✔ Saved cleaned file to: {output_csv}")

path = '../Pilot 2 data samples/RED_1sec_v2_2025-01-30'
input_csv = f"{path}.csv"
output_csv = f"{path}_cleaned.csv"

print(f"Cleaning CSV file: {input_csv}")
print(f"{output_csv} will have unique, non-empty headers.\n")
    
enforce_unique_nonempty_headers(input_csv, output_csv)