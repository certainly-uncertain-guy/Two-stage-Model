# Validation report: slow-storm sensitivity

116/117 checks passed.

## Failed checks

```
                                                            check  budget    value  reference  passed  informational
uniform mean of x_RO == robust_decisions_stochastic_solutions.csv    30.0 8.765967        8.7   False          False
```

## Informational flags (not pass/fail)

```
                                                  check  budget     value  reference  passed  informational
info: delta_rev >= 0 (else uniform baseline suboptimal)    20.0 -0.085216        0.0   False           True
```

## All checks

```
                                                            check  budget         value     reference  passed  informational
                                    uniform mean of x_SO == L*_SO     0.0  4.462061e+01  4.462125e+01    True          False
uniform mean of x_RO == robust_decisions_stochastic_solutions.csv     0.0  4.462061e+01  4.462000e+01    True          False
                                         max_k L(x_RO,k) <= L*_RO     0.0  5.603461e+01  5.603461e+01    True          False
                              uniform mean of x_MV == L_SO(x_bar)     0.0  4.462061e+01  4.462061e+01    True          False
                                               WS_slow <= L*_slow     0.0  4.645644e+01  4.645392e+01    True          False
                                          L*_slow <= L_slow(x_SO)     0.0  4.645392e+01  4.645392e+01    True          False
                                          L*_slow <= L_slow(x_MV)     0.0  4.645392e+01  4.645392e+01    True          False
                     solver objective == evaluated L_slow(x_slow)     0.0  4.645510e+01  4.645392e+01    True          False
               info: delta_mis >= 0 (re-solve beats uniform plan)     0.0  0.000000e+00  0.000000e+00    True           True
          info: delta_rev >= 0 (else uniform baseline suboptimal)     0.0  0.000000e+00  0.000000e+00    True           True
                                    uniform mean of x_SO == L*_SO    10.0  2.220200e+01  2.220144e+01    True          False
uniform mean of x_RO == robust_decisions_stochastic_solutions.csv    10.0  2.345128e+01  2.345000e+01    True          False
                                         max_k L(x_RO,k) <= L*_RO    10.0  2.579095e+01  2.581173e+01    True          False
                              uniform mean of x_MV == L_SO(x_bar)    10.0  3.121219e+01  3.121219e+01    True          False
                                               WS_slow <= L*_slow    10.0  1.476931e+01  2.261129e+01    True          False
                                          L*_slow <= L_slow(x_SO)    10.0  2.261129e+01  2.263053e+01    True          False
                                          L*_slow <= L_slow(x_MV)    10.0  2.261129e+01  3.292488e+01    True          False
                     solver objective == evaluated L_slow(x_slow)    10.0  2.261116e+01  2.261129e+01    True          False
               info: delta_mis >= 0 (re-solve beats uniform plan)    10.0  1.923520e-02  0.000000e+00    True           True
          info: delta_rev >= 0 (else uniform baseline suboptimal)    10.0  8.259620e-02  0.000000e+00    True           True
                                    uniform mean of x_SO == L*_SO    20.0  1.374453e+01  1.374453e+01    True          False
uniform mean of x_RO == robust_decisions_stochastic_solutions.csv    20.0  1.512784e+01  1.513000e+01    True          False
                                         max_k L(x_RO,k) <= L*_RO    20.0  1.570352e+01  1.570561e+01    True          False
                              uniform mean of x_MV == L_SO(x_bar)    20.0  2.640412e+01  2.640412e+01    True          False
                                               WS_slow <= L*_slow    20.0  6.960547e+00  1.384949e+01    True          False
                                          L*_slow <= L_slow(x_SO)    20.0  1.384949e+01  1.418638e+01    True          False
                                          L*_slow <= L_slow(x_MV)    20.0  1.384949e+01  2.839870e+01    True          False
                     solver objective == evaluated L_slow(x_slow)    20.0  1.384936e+01  1.384949e+01    True          False
               info: delta_mis >= 0 (re-solve beats uniform plan)    20.0  3.368982e-01  0.000000e+00    True           True
          info: delta_rev >= 0 (else uniform baseline suboptimal)    20.0 -8.521569e-02  0.000000e+00   False           True
                                    uniform mean of x_SO == L*_SO    30.0  8.302299e+00  8.302299e+00    True          False
uniform mean of x_RO == robust_decisions_stochastic_solutions.csv    30.0  8.765967e+00  8.700000e+00   False          False
                                         max_k L(x_RO,k) <= L*_RO    30.0  9.915172e+00  9.915172e+00    True          False
                              uniform mean of x_MV == L_SO(x_bar)    30.0  2.352391e+01  2.352391e+01    True          False
                                               WS_slow <= L*_slow    30.0  3.126096e+00  8.388351e+00    True          False
                                          L*_slow <= L_slow(x_SO)    30.0  8.388351e+00  8.477090e+00    True          False
                                          L*_slow <= L_slow(x_MV)    30.0  8.388351e+00  2.600638e+01    True          False
                     solver objective == evaluated L_slow(x_slow)    30.0  8.388351e+00  8.388351e+00    True          False
               info: delta_mis >= 0 (re-solve beats uniform plan)    30.0  8.873896e-02  0.000000e+00    True           True
          info: delta_rev >= 0 (else uniform baseline suboptimal)    30.0  8.578042e-02  0.000000e+00    True           True
                                    uniform mean of x_SO == L*_SO    40.0  4.796114e+00  4.796114e+00    True          False
uniform mean of x_RO == robust_decisions_stochastic_solutions.csv    40.0  4.996731e+00  4.990000e+00    True          False
                                         max_k L(x_RO,k) <= L*_RO    40.0  5.256550e+00  5.256550e+00    True          False
                              uniform mean of x_MV == L_SO(x_bar)    40.0  2.200406e+01  2.200406e+01    True          False
                                               WS_slow <= L*_slow    40.0  1.079772e+00  4.787697e+00    True          False
                                          L*_slow <= L_slow(x_SO)    40.0  4.787697e+00  4.988519e+00    True          False
                                          L*_slow <= L_slow(x_MV)    40.0  4.787697e+00  2.443383e+01    True          False
                     solver objective == evaluated L_slow(x_slow)    40.0  4.787697e+00  4.787697e+00    True          False
               info: delta_mis >= 0 (re-solve beats uniform plan)    40.0  2.008225e-01  0.000000e+00    True           True
          info: delta_rev >= 0 (else uniform baseline suboptimal)    40.0  8.194375e-02  0.000000e+00    True           True
                                    uniform mean of x_SO == L*_SO    50.0  2.351514e+00  2.351514e+00    True          False
uniform mean of x_RO == robust_decisions_stochastic_solutions.csv    50.0  2.468297e+00  2.460000e+00    True          False
                                         max_k L(x_RO,k) <= L*_RO    50.0  2.537650e+00  2.537650e+00    True          False
                              uniform mean of x_MV == L_SO(x_bar)    50.0  2.117844e+01  2.117844e+01    True          False
                                               WS_slow <= L*_slow    50.0  1.979737e-01  2.334437e+00    True          False
                                          L*_slow <= L_slow(x_SO)    50.0  2.334437e+00  2.486720e+00    True          False
                                          L*_slow <= L_slow(x_MV)    50.0  2.334437e+00  2.366296e+01    True          False
                     solver objective == evaluated L_slow(x_slow)    50.0  2.334437e+00  2.334437e+00    True          False
               info: delta_mis >= 0 (re-solve beats uniform plan)    50.0  1.522825e-01  0.000000e+00    True           True
          info: delta_rev >= 0 (else uniform baseline suboptimal)    50.0  1.374069e-01  0.000000e+00    True           True
                                    uniform mean of x_SO == L*_SO    60.0  6.042750e-01  6.042750e-01    True          False
uniform mean of x_RO == robust_decisions_stochastic_solutions.csv    60.0  6.042750e-01  6.000000e-01    True          False
                                         max_k L(x_RO,k) <= L*_RO    60.0  6.171000e-01  6.171000e-01    True          False
                              uniform mean of x_MV == L_SO(x_bar)    60.0  2.114704e+01  2.115205e+01    True          False
                                               WS_slow <= L*_slow    60.0  7.301250e-03  5.703394e-01    True          False
                                          L*_slow <= L_slow(x_SO)    60.0  5.703394e-01  6.068400e-01    True          False
                                          L*_slow <= L_slow(x_MV)    60.0  5.703394e-01  2.363661e+01    True          False
                     solver objective == evaluated L_slow(x_slow)    60.0  5.703394e-01  5.703394e-01    True          False
               info: delta_mis >= 0 (re-solve beats uniform plan)    60.0  3.650062e-02  0.000000e+00    True           True
          info: delta_rev >= 0 (else uniform baseline suboptimal)    60.0  1.423163e-01  0.000000e+00    True           True
                                    uniform mean of x_SO == L*_SO    70.0  2.082000e-02  2.082000e-02    True          False
uniform mean of x_RO == robust_decisions_stochastic_solutions.csv    70.0  2.082000e-02  2.000000e-02    True          False
                                         max_k L(x_RO,k) <= L*_RO    70.0  2.082000e-02  2.082000e-02    True          False
                              uniform mean of x_MV == L_SO(x_bar)    70.0  2.114705e+01  2.115205e+01    True          False
                                               WS_slow <= L*_slow    70.0 -3.410605e-13  1.691625e-02    True          False
                                          L*_slow <= L_slow(x_SO)    70.0  1.691625e-02  2.082000e-02    True          False
                                          L*_slow <= L_slow(x_MV)    70.0  1.691625e-02  2.363661e+01    True          False
                     solver objective == evaluated L_slow(x_slow)    70.0  1.691625e-02  1.691625e-02    True          False
               info: delta_mis >= 0 (re-solve beats uniform plan)    70.0  3.903750e-03  0.000000e+00    True           True
          info: delta_rev >= 0 (else uniform baseline suboptimal)    70.0  1.786200e-01  0.000000e+00    True           True
                                    uniform mean of x_SO == L*_SO    80.0 -2.670525e-16  1.023182e-12    True          False
uniform mean of x_RO == robust_decisions_stochastic_solutions.csv    80.0 -2.670525e-16  0.000000e+00    True          False
                                         max_k L(x_RO,k) <= L*_RO    80.0  0.000000e+00  0.000000e+00    True          False
                              uniform mean of x_MV == L_SO(x_bar)    80.0  2.114705e+01  2.115205e+01    True          False
                                               WS_slow <= L*_slow    80.0 -3.410605e-13 -2.670525e-16    True          False
                                          L*_slow <= L_slow(x_SO)    80.0 -2.670525e-16 -2.670525e-16    True          False
                                          L*_slow <= L_slow(x_MV)    80.0 -2.670525e-16  2.363661e+01    True          False
                     solver objective == evaluated L_slow(x_slow)    80.0  1.136868e-13 -2.670525e-16    True          False
               info: delta_mis >= 0 (re-solve beats uniform plan)    80.0  0.000000e+00  0.000000e+00    True           True
          info: delta_rev >= 0 (else uniform baseline suboptimal)    80.0  1.838250e-01  0.000000e+00    True           True
                             L_lambda(x_RO) <= L*_RO (lambda=0.0)     0.0  4.462061e+01  5.603461e+01    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.0)    10.0  2.345128e+01  2.581173e+01    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.0)    20.0  1.512784e+01  1.570561e+01    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.0)    30.0  8.765967e+00  9.915172e+00    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.0)    40.0  4.996731e+00  5.256550e+00    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.0)    50.0  2.468297e+00  2.537650e+00    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.0)    60.0  6.042750e-01  6.171000e-01    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.0)    70.0  2.082000e-02  2.082000e-02    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.0)    80.0 -2.670525e-16  0.000000e+00    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.25)     0.0  4.507893e+01  5.603461e+01    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.25)    10.0  2.360274e+01  2.581173e+01    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.25)    20.0  1.513512e+01  1.570561e+01    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.25)    30.0  8.824946e+00  9.915172e+00    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.25)    40.0  5.003568e+00  5.256550e+00    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.25)    50.0  2.475558e+00  2.537650e+00    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.25)    60.0  6.049162e-01  6.171000e-01    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.25)    70.0  2.082000e-02  2.082000e-02    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.25)    80.0 -2.670525e-16  0.000000e+00    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.5)     0.0  4.553726e+01  5.603461e+01    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.5)    10.0  2.375420e+01  2.581173e+01    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.5)    20.0  1.514239e+01  1.570561e+01    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.5)    30.0  8.883925e+00  9.915172e+00    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.5)    40.0  5.010405e+00  5.256550e+00    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.5)    50.0  2.482819e+00  2.537650e+00    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.5)    60.0  6.055575e-01  6.171000e-01    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.5)    70.0  2.082000e-02  2.082000e-02    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=0.5)    80.0 -2.670525e-16  0.000000e+00    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.75)     0.0  4.599559e+01  5.603461e+01    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.75)    10.0  2.390567e+01  2.581173e+01    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.75)    20.0  1.514966e+01  1.570561e+01    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.75)    30.0  8.942903e+00  9.915172e+00    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.75)    40.0  5.017241e+00  5.256550e+00    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.75)    50.0  2.490080e+00  2.537650e+00    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.75)    60.0  6.061987e-01  6.171000e-01    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.75)    70.0  2.082000e-02  2.082000e-02    True          False
                            L_lambda(x_RO) <= L*_RO (lambda=0.75)    80.0 -2.670525e-16  0.000000e+00    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=1.0)     0.0  4.645392e+01  5.603461e+01    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=1.0)    10.0  2.405713e+01  2.581173e+01    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=1.0)    20.0  1.515694e+01  1.570561e+01    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=1.0)    30.0  9.001882e+00  9.915172e+00    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=1.0)    40.0  5.024078e+00  5.256550e+00    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=1.0)    50.0  2.497341e+00  2.537650e+00    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=1.0)    60.0  6.068400e-01  6.171000e-01    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=1.0)    70.0  2.082000e-02  2.082000e-02    True          False
                             L_lambda(x_RO) <= L*_RO (lambda=1.0)    80.0 -2.670525e-16  0.000000e+00    True          False
```

## Summary (raw units; divide by 10 for GW)

```
 budget    L_SO_star  L_SO_star_gap  L_SO_xbar        L0_xSO    L_slow_xSO        L0_xRO    L_slow_xRO   max_xRO  L_RO_star    L0_xMV  L_slow_xMV       WS_slow   L_star_slow  L0_xslow  L_star_slow_solver  slow_gap  delta_mis  delta_mis_pct  delta_rev  risk_shift  jaccard_slow_vs_so
      0 4.462125e+01       0.000017  44.620605  4.462061e+01  4.645392e+01  4.462061e+01  4.645392e+01 56.034613  56.034613 44.620605   46.453921  4.645644e+01  4.645392e+01 44.620605        4.645510e+01  0.003627   0.000000       0.000000   0.000000    1.833316            1.000000
     10 2.220144e+01       0.017708  31.212185  2.220200e+01  2.263053e+01  2.345128e+01  2.405713e+01 25.790948  25.811729 31.212185   32.924879  1.476931e+01  2.261129e+01 22.284593        2.261116e+01  0.000006   0.019235       0.085069   0.082596    0.409294            1.000000
     20 1.374453e+01       0.047076  26.404120  1.374453e+01  1.418638e+01  1.512784e+01  1.515694e+01 15.703523  15.705609 26.404120   28.398696  6.960547e+00  1.384949e+01 13.659318        1.384936e+01  0.001225   0.336898       2.432568  -0.085216    0.104953            0.892857
     30 8.302299e+00       0.000000  23.523906  8.302299e+00  8.477090e+00  8.765967e+00  9.001882e+00  9.915172   9.915172 23.523906   26.006376  3.126096e+00  8.388351e+00  8.388079        8.388351e+00  0.004050   0.088739       1.057883   0.085780    0.086052            0.972222
     40 4.796114e+00       0.003465  22.004056  4.796114e+00  4.988519e+00  4.996731e+00  5.024078e+00  5.256550   5.256550 22.004056   24.433833  1.079772e+00  4.787697e+00  4.878058        4.787697e+00  0.004956   0.200822       4.194553   0.081944   -0.008418            0.955556
     50 2.351514e+00       0.000129  21.178435  2.351514e+00  2.486720e+00  2.468297e+00  2.497341e+00  2.537650   2.537650 21.178435   23.662955  1.979737e-01  2.334437e+00  2.488921        2.334437e+00  0.000000   0.152282       6.523306   0.137407   -0.017076            0.925926
     60 6.042750e-01       0.000000  21.152050  6.042750e-01  6.068400e-01  6.042750e-01  6.068400e-01  0.617100   0.617100 21.147045   23.636605  7.301250e-03  5.703394e-01  0.746591        5.703394e-01  0.000000   0.036501       6.399808   0.142316   -0.033936            0.966102
     70 2.082000e-02       0.000000  21.152049  2.082000e-02  2.082000e-02  2.082000e-02  2.082000e-02  0.020820   0.020820 21.147045   23.636605 -3.410605e-13  1.691625e-02  0.199440        1.691625e-02  0.000000   0.003904      23.076923   0.178620   -0.003904            0.969697
     80 1.023182e-12       0.000000  21.152049 -2.670525e-16 -2.670525e-16 -2.670525e-16 -2.670525e-16  0.000000   0.000000 21.147045   23.636605 -3.410605e-13 -2.670525e-16  0.183825        1.136868e-13  0.000000   0.000000            NaN   0.183825    0.000000            0.986111
```

## Near-optimal budget

```
 restoration_h  voll  I_uniform  cost_uniform  I_slow    cost_slow  cost_uniform_plan_under_slow    regret_usd
             6   250         20  4.061680e+07      20 4.077423e+07                  4.127958e+07 505347.279516
             6   500         40  5.438834e+07      40 5.436309e+07                  5.496556e+07 602467.500000
             6  1000         60  6.362565e+07      60 6.342204e+07                  6.364104e+07 219003.750000
             6  3000         70  7.037476e+07      60 7.026611e+07                  7.037476e+07 108651.250000
             6  5000         70  7.062460e+07      70 7.050749e+07                  7.062460e+07 117112.500000
            12   250         40  5.438834e+07      40 5.436309e+07                  5.496556e+07 602467.500000
            12   500         60  6.362565e+07      60 6.342204e+07                  6.364104e+07 219003.750000
            12  1000         60  6.725130e+07      60 6.684407e+07                  6.728208e+07 438007.500000
            12  3000         70  7.074952e+07      70 7.060898e+07                  7.074952e+07 140535.000000
            12  5000         70  7.124920e+07      70 7.101497e+07                  7.124920e+07 234225.000000
            24   250         60  6.362565e+07      60 6.342204e+07                  6.364104e+07 219003.750000
            24   500         60  6.725130e+07      60 6.684407e+07                  6.728208e+07 438007.500000
            24  1000         70  7.049968e+07      70 7.040599e+07                  7.049968e+07  93690.000000
            24  3000         70  7.149904e+07      70 7.121797e+07                  7.149904e+07 281070.000000
            24  5000         70  7.249840e+07      70 7.202995e+07                  7.249840e+07 468450.000000
            48   250         60  6.725130e+07      60 6.684407e+07                  6.728208e+07 438007.500000
            48   500         70  7.049968e+07      70 7.040599e+07                  7.049968e+07  93690.000000
            48  1000         70  7.099936e+07      70 7.081198e+07                  7.099936e+07 187380.000000
            48  3000         70  7.299808e+07      70 7.243594e+07                  7.299808e+07 562140.000000
            48  5000         70  7.499680e+07      70 7.405990e+07                  7.499680e+07 936900.000000
```
