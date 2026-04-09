# Holdout Evaluation

Dataset: `data/processed/holdout.parquet`

## Summary

| Metric | Value |
| --- | ---: |
| Records | 2000 |
| Macro F1 | 0.3545 |
| Product Macro F1 | 0.5246 |
| Issue Macro F1 | 0.1843 |
| Exact Match Rate | 0.2230 |
| Fallback Rate | 1.0000 |

## Product Breakdown

| Label | Support | Predicted | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| CREDIT_CARD | 128 | 243 | 0.3868 | 0.7344 | 0.5067 |
| BANK_ACCOUNT | 89 | 50 | 0.5800 | 0.3258 | 0.4173 |
| MORTGAGE | 79 | 67 | 0.7910 | 0.6709 | 0.7260 |
| LOAN | 65 | 115 | 0.3130 | 0.5538 | 0.4000 |
| DEBT_COLLECTION | 229 | 75 | 0.5200 | 0.1703 | 0.2566 |
| MONEY_TRANSFER | 67 | 62 | 0.5645 | 0.5224 | 0.5426 |
| OTHER | 1343 | 1388 | 0.8098 | 0.8369 | 0.8231 |

## Issue Breakdown

| Label | Support | Predicted | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| BILLING | 129 | 218 | 0.1376 | 0.2326 | 0.1729 |
| FRAUD | 18 | 406 | 0.0271 | 0.6111 | 0.0519 |
| PAYMENT | 97 | 460 | 0.0935 | 0.4433 | 0.1544 |
| IDENTITY_THEFT | 8 | 89 | 0.0225 | 0.2500 | 0.0412 |
| CUSTOMER_SERVICE | 156 | 27 | 0.5185 | 0.0897 | 0.1530 |
| CREDIT_REPORTING | 1351 | 457 | 0.8687 | 0.2939 | 0.4392 |
| OTHER | 241 | 343 | 0.2362 | 0.3361 | 0.2774 |

## Fairness

- Baseline: `CREDIT_REPORTING` (1340 rows, exact match 0.2724)
- Minimum Support: `50`

| Group | Support | Exact Match Rate | Disparity Ratio vs Baseline |
| --- | ---: | ---: | ---: |
| DEBT_COLLECTION | 229 | 0.0524 | 0.1924 |
| BANK_ACCOUNT | 89 | 0.0899 | 0.3300 |
| MORTGAGE | 79 | 0.2658 | 0.9758 |
| MONEY_TRANSFER | 67 | 0.0896 | 0.3289 |
| CREDIT_CARD | 128 | 0.1641 | 0.6024 |
| LOAN | 65 | 0.1692 | 0.6211 |

## Sampled Failures

### 10057965
- Truth: `OTHER` / `CREDIT_REPORTING`
- Prediction: `OTHER` / `PAYMENT`
- Confidence: 0.5000
- Fallback Used: yes
- State/Date: SC / 2024-09-08
- Excerpt: I recently looked at my Transunion credit report and noticed some things are incomplete and not accurate. Account name XXXX XXXX XXXX XXXX has reported that...

### 10090331
- Truth: `OTHER` / `CREDIT_REPORTING`
- Prediction: `OTHER` / `PAYMENT`
- Confidence: 0.5000
- Fallback Used: yes
- State/Date: GA / 2024-09-11
- Excerpt: In accordance with the Fair Credit Reporting Act. 15 USC 1681i ( a ) ( 1 ) ( A ), Can you reinvestigate the completeness and accuracy of the list of accounts...

### 10135910
- Truth: `OTHER` / `CREDIT_REPORTING`
- Prediction: `CREDIT_CARD` / `CREDIT_REPORTING`
- Confidence: 0.5000
- Fallback Used: yes
- State/Date: WI / 2024-09-16
- Excerpt: I wrote a letter to Wells Fargo XX/XX/XXXX regarding an inquiry on my credit report dated XX/XX/XXXX stating I has a current mortgage of {$1000.00}. I am cur...

### 10136876
- Truth: `DEBT_COLLECTION` / `OTHER`
- Prediction: `OTHER` / `BILLING`
- Confidence: 0.5000
- Fallback Used: yes
- State/Date: FL / 2024-09-16
- Excerpt: Could you please take a moment to review and examine the attached documents? I believe your expertise will be invaluable in ensuring their accuracy and compl...

### 10165020
- Truth: `OTHER` / `CREDIT_REPORTING`
- Prediction: `OTHER` / `OTHER`
- Confidence: 0.5000
- Fallback Used: yes
- State/Date: TX / 2024-09-18
- Excerpt: This is an unfair system to be ignored and taken advantage of while plenty of laws are broken due to malpractice and the severity of not taking my situation...
