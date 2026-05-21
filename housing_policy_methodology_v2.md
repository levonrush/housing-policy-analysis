# Australian housing, wages, investor tax settings and macro shocks: updated empirical method

## Research question

Did Australian dwelling prices diverge from wages after the 1999 CGT discount, and did that change remain after accounting for interest rates, housing credit, investor lending, immigration and dwelling supply?

A stronger version tests whether the 1999 CGT discount, operating alongside existing negative gearing, changed the transmission of cheap credit and investor demand into dwelling prices relative to wages.

A later reform, if legislated and observed, can be tested as a policy reversal.

## Important policy coding

Negative gearing was not introduced by the Howard government. It existed earlier, was quarantined from 1985 to 1987, and was restored in 1987.

The Howard-era shock is the 1999 CGT discount. The mechanism is the combination of:

```text
deductible rental losses
+ concessionally taxed capital gains
+ leverage
```

## Outcome

```text
log_price_wage_ratio = log(real_dwelling_price_index / real_wage_index)
```

## Event variables

| Event | Coding |
|---|---|
| Negative gearing restored | `post_1987_ng = 1` from 1987 Q3 |
| CGT discount | `post_1999_cgt = 1` from 1999 Q4 |
| GFC acute shock | `gfc_shock = 1` from 2008 Q3 to 2009 Q2 |
| Post-GFC regime | `post_gfc = 1` after 2009 Q2 |
| COVID acute shock | `covid_shock = 1` from 2020 Q1 to 2021 Q4 |
| Post-COVID regime | `post_covid = 1` from 2022 Q1 |
| Reform announcement | parameterised, default 2026 Q2 |
| Reform implementation | parameterised, default 2027 Q3 |

The reform variables should remain provisional until final legislation is confirmed.

## Hypotheses

### H1: The price-wage ratio changed after the 1999 CGT discount

```text
H0: post_1999_cgt = 0 and time_after_1999 = 0
H1: post_1999_cgt != 0 and/or time_after_1999 != 0
```

### H2: The 1999 change remains after confounders

```text
H0: post-1999 terms become zero after controlling for rates, credit, migration and supply
H1: post-1999 terms remain non-zero after controls
```

### H3: The CGT discount amplified investor demand

```text
H0: investor_credit_share × post_1999_cgt = 0
H1: investor_credit_share × post_1999_cgt > 0
```

### H4: The CGT discount amplified the effect of lower rates

```text
H0: mortgage_rate × post_1999_cgt = 0
H1: mortgage_rate × post_1999_cgt < 0
```

### H5: Migration pressure matters more when supply is constrained

```text
H0: nom_per_1000 × low_supply = 0
H1: nom_per_1000 × low_supply > 0
```

### H6: The GFC changed the level, trend or transmission mechanism

Relevant terms:
- `gfc_shock`
- `post_gfc`
- `time_after_gfc`
- `mortgage_rate × post_gfc`
- `housing_credit_growth × post_gfc`

### H7: COVID changed the level, trend or transmission mechanism

Relevant terms:
- `covid_shock`
- `post_covid`
- `time_after_covid`
- `mortgage_rate × post_covid`
- `housing_credit_growth × post_covid`

### H8: Later reform weakens the investor-tax channel

```text
H0: investor_credit_share × post_reform_implementation = 0
H1: investor_credit_share × post_reform_implementation < 0
```

### H9: Later reform weakens price-wage divergence

```text
H0: time_after_reform_implementation = 0
H1: time_after_reform_implementation < 0
```

## Model sequence

### Model 1: interrupted time series

```text
y_t =
    time
  + post_1999_cgt
  + time_after_1999
  + gfc_shock
  + post_gfc
  + time_after_gfc
  + covid_shock
  + post_covid
  + time_after_covid
  + error
```

### Model 2: controlled interrupted time series

```text
y_t =
    Model 1 terms
  + mortgage_rate
  + housing_credit_growth
  + investor_credit_share
  + nom_per_1000
  + dwelling_completions_per_1000
  + error
```

### Model 3: tax-amplifier model

```text
y_t =
    controls
  + post_1999_cgt
  + time_after_1999
  + investor_credit_share × post_1999_cgt
  + mortgage_rate × post_1999_cgt
  + GFC terms
  + COVID terms
  + error
```

### Model 4: reform reversal model

```text
y_t =
    historical policy terms
  + confounders
  + post_reform_announcement
  + time_after_reform_announcement
  + post_reform_implementation
  + time_after_reform_implementation
  + investor_credit_share × post_reform_implementation
  + mortgage_rate × post_reform_implementation
  + error
```

### Model 5: panel fixed effects

```text
y_{g,t} =
    geography fixed effects
  + quarter fixed effects
  + migration
  + completions
  + investor exposure × post_1999
  + investor exposure × post_reform
  + GFC shock
  + COVID shock
  + error
```

## Inference rules

A strong historical tax-amplifier result requires:

1. A break or slope change near 1999.
2. The result survives controls for rates, credit, migration and supply.
3. `investor_credit_share × post_1999_cgt` is positive.
4. `mortgage_rate × post_1999_cgt` is negative.
5. GFC and COVID terms do not absorb the 1999 result.
6. Panel results show larger effects in more investor-exposed geographies.

A strong reversal result requires:

1. Investor credit weakens after reform announcement or implementation.
2. The price-wage ratio trend weakens after implementation.
3. Effects are larger in investor-heavy or established-dwelling markets.
4. Results survive controls for rates, migration, credit, supply, GFC and COVID.
