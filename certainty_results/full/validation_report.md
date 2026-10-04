# Validation report: single-scenario certainty experiment

## Baseline (L*_SO from output/sm_16 Gurobi logs)

| budget | L*_SO | final gap | L*_SO (stochastic_solution.csv) | L_SO(x̄) | L*_WS |
|---|---|---|---|---|---|
| 0.0 | 44.6213 | 0.00% | 44.62 | 44.6206 | 44.6306 |
| 10.0 | 22.2014 | 1.77% | 22.2 | 31.2122 | 13.6293 |
| 20.0 | 13.7445 | 4.71% | 13.74 | 26.4041 | 6.3603 |
| 30.0 | 8.3023 | 0.00% | 8.3 | 23.5239 | 2.7672 |
| 40.0 | 4.7961 | 0.35% | 4.79 | 22.0041 | 0.9433 |
| 50.0 | 2.3515 | 0.01% | 2.35 | 21.1784 | 0.1853 |
| 60.0 | 0.6043 | 0.00% | 0.6 | 21.1520 | 0.0073 |
| 70.0 | 0.0208 | 0.00% | 0.02 | 21.1520 | -0.0000 |
| 80.0 | 0.0000 | 0.00% | 0.0 | 21.1520 | -0.0000 |

Values in raw model units (divide by 10 for GW).

## Wait-and-see cache match (decision step == WS subproblem)

144/144 solves match `wait_and_see_dict.json` within the MIP gap.

## Cross-matrix diagonal L(x_k, k) vs L_in

144/144 diagonals match within tolerance (max |diff| = 0.1026).

## Ordering chain L*_WS ≤ L*_SO ≤ min_k L_SO(x_k) ≤ mean_k L_SO(x_k)

```
 budget  ws_le_so  so_le_min_xk  min_le_mean_xk  mean_L_in_eq_ws
      0      True          True            True             True
     10      True          True            True             True
     20      True          True            True             True
     30      True          True            True             True
     40      True          True            True             True
     50      True          True            True             True
     60      True          True            True             True
     70      True          True            True             True
     80      True          True            True             True
```

`mean_L_in_eq_ws` is only checked when all 16 scenarios ran (NA otherwise).

## Negative regret beyond the baseline's own gap

None.

## Effect of the minimum-spend tie-break

The tie-break changed L_SO(x_k) in 56/144 (scenario, budget) pairs.
- w_5_05 $50M: raw=27.8082 tie-broken=27.7983 (spend raw=45.55M, tie-broken=43.33M)
- w_5_05 $60M: raw=27.8082 tie-broken=27.7983 (spend raw=45.55M, tie-broken=43.33M)
- w_5_05 $70M: raw=27.8082 tie-broken=27.7983 (spend raw=45.55M, tie-broken=43.33M)
- w_5_05 $80M: raw=27.8082 tie-broken=27.7983 (spend raw=45.55M, tie-broken=43.33M)
- w_5_10 $40M: raw=30.3195 tie-broken=30.2960 (spend raw=39.05M, tie-broken=38.30M)
- w_5_10 $50M: raw=30.3195 tie-broken=30.2960 (spend raw=39.12M, tie-broken=38.30M)
- w_5_10 $60M: raw=30.3195 tie-broken=30.2960 (spend raw=39.12M, tie-broken=38.30M)
- w_5_10 $70M: raw=30.3195 tie-broken=30.2960 (spend raw=39.12M, tie-broken=38.30M)
- w_5_10 $80M: raw=30.2753 tie-broken=30.2960 (spend raw=40.23M, tie-broken=38.30M)
- w_5_15 $10M: raw=37.3364 tie-broken=37.3813 (spend raw=9.95M, tie-broken=9.72M)
- w_5_15 $60M: raw=35.8436 tie-broken=35.8716 (spend raw=31.27M, tie-broken=30.50M)
- w_5_15 $70M: raw=35.8436 tie-broken=35.8716 (spend raw=31.27M, tie-broken=30.50M)
- w_5_15 $80M: raw=35.8436 tie-broken=35.8716 (spend raw=31.27M, tie-broken=30.50M)
- w_5_25 $70M: raw=31.8724 tie-broken=31.9505 (spend raw=36.80M, tie-broken=35.60M)
- w_5_25 $80M: raw=31.8724 tie-broken=31.9505 (spend raw=36.80M, tie-broken=35.60M)
- wnw_5_05 $20M: raw=22.6452 tie-broken=22.6353 (spend raw=19.95M, tie-broken=19.82M)
- wnw_5_10 $70M: raw=6.3355 tie-broken=6.3318 (spend raw=63.15M, tie-broken=61.70M)
- wnw_5_10 $80M: raw=6.3355 tie-broken=6.3318 (spend raw=63.15M, tie-broken=61.70M)
- wnw_5_15 $60M: raw=11.9014 tie-broken=11.9085 (spend raw=56.42M, tie-broken=55.05M)
- wnw_5_15 $70M: raw=11.9014 tie-broken=11.9085 (spend raw=56.42M, tie-broken=55.05M)
- wnw_5_15 $80M: raw=11.9014 tie-broken=11.9085 (spend raw=56.42M, tie-broken=55.05M)
- wnw_5_25 $50M: raw=22.5343 tie-broken=22.9694 (spend raw=47.77M, tie-broken=46.50M)
- wnw_5_25 $60M: raw=22.5343 tie-broken=22.9694 (spend raw=47.77M, tie-broken=46.50M)
- wnw_5_25 $70M: raw=22.5343 tie-broken=22.9694 (spend raw=47.77M, tie-broken=46.50M)
- wnw_5_25 $80M: raw=22.5547 tie-broken=22.9694 (spend raw=48.27M, tie-broken=46.50M)
- nw_5_05 $40M: raw=17.7789 tie-broken=17.6602 (spend raw=39.88M, tie-broken=39.73M)
- nw_5_05 $60M: raw=16.9940 tie-broken=16.9950 (spend raw=52.15M, tie-broken=51.00M)
- nw_5_05 $70M: raw=16.9940 tie-broken=16.9950 (spend raw=52.15M, tie-broken=51.00M)
- nw_5_05 $80M: raw=16.9940 tie-broken=16.9950 (spend raw=52.15M, tie-broken=51.00M)
- nw_5_10 $70M: raw=6.4227 tie-broken=6.4168 (spend raw=63.38M, tie-broken=61.80M)
- nw_5_10 $80M: raw=6.4227 tie-broken=6.4168 (spend raw=63.38M, tie-broken=61.80M)
- nw_5_15 $40M: raw=12.6334 tie-broken=12.6393 (spend raw=40.00M, tie-broken=39.77M)
- nw_5_15 $60M: raw=10.1885 tie-broken=10.1926 (spend raw=58.80M, tie-broken=56.92M)
- nw_5_15 $70M: raw=10.1885 tie-broken=10.1926 (spend raw=58.80M, tie-broken=56.92M)
- nw_5_15 $80M: raw=10.1885 tie-broken=10.1926 (spend raw=58.80M, tie-broken=56.92M)
- nw_5_25 $50M: raw=23.3301 tie-broken=23.5940 (spend raw=46.52M, tie-broken=45.17M)
- nw_5_25 $60M: raw=23.3301 tie-broken=23.5940 (spend raw=46.52M, tie-broken=45.17M)
- nw_5_25 $70M: raw=23.3226 tie-broken=23.5940 (spend raw=46.73M, tie-broken=45.17M)
- nw_5_25 $80M: raw=23.3226 tie-broken=23.5940 (spend raw=46.73M, tie-broken=45.17M)
- nnw_5_05 $50M: raw=28.9590 tie-broken=28.9598 (spend raw=43.05M, tie-broken=42.00M)
- nnw_5_05 $60M: raw=28.9590 tie-broken=28.9598 (spend raw=43.05M, tie-broken=42.00M)
- nnw_5_05 $70M: raw=28.9590 tie-broken=28.9598 (spend raw=43.05M, tie-broken=42.00M)
- nnw_5_05 $80M: raw=28.9585 tie-broken=28.9598 (spend raw=43.15M, tie-broken=42.00M)
- nnw_5_10 $50M: raw=18.5440 tie-broken=18.5478 (spend raw=49.20M, tie-broken=47.85M)
- nnw_5_10 $60M: raw=18.5440 tie-broken=18.5478 (spend raw=49.20M, tie-broken=47.85M)
- nnw_5_10 $70M: raw=18.5440 tie-broken=18.5478 (spend raw=49.20M, tie-broken=47.85M)
- nnw_5_10 $80M: raw=18.5416 tie-broken=18.5478 (spend raw=49.40M, tie-broken=47.85M)
- nnw_5_15 $50M: raw=24.5571 tie-broken=24.9387 (spend raw=43.62M, tie-broken=42.17M)
- nnw_5_15 $60M: raw=24.5571 tie-broken=24.9387 (spend raw=43.62M, tie-broken=42.17M)
- nnw_5_15 $70M: raw=24.5559 tie-broken=24.9387 (spend raw=43.73M, tie-broken=42.17M)
- nnw_5_15 $80M: raw=24.5559 tie-broken=24.9387 (spend raw=43.73M, tie-broken=42.17M)
- nnw_5_25 $40M: raw=34.3970 tie-broken=34.5189 (spend raw=36.10M, tie-broken=34.95M)
- nnw_5_25 $50M: raw=34.3970 tie-broken=34.5189 (spend raw=36.10M, tie-broken=34.95M)
- nnw_5_25 $60M: raw=34.3970 tie-broken=34.5189 (spend raw=36.10M, tie-broken=34.95M)
- nnw_5_25 $70M: raw=34.3970 tie-broken=34.5189 (spend raw=36.10M, tie-broken=34.95M)
- nnw_5_25 $80M: raw=34.3970 tie-broken=34.5189 (spend raw=36.10M, tie-broken=34.95M)
