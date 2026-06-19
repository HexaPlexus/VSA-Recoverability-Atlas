# Oracle Portfolio Complementarity Report

- Build verdict: `STOP_PORTFOLIO_LINE`
- Scientific verdict: `ORACLE_COMPLEMENTARITY_NOT_SUPPORTED`
- Portfolio verdict: `DOMINANT_SINGLE_METHOD`
- Protocol hash: `e7b56d4a5c780d2e45270b203b4d8df6efd73585f0b6f34f6fb2a0ec1a3ad1fd`
- Best fixed single method: `BCF_NATIVE`
- Gate outcomes: `{"best_single_method": "BCF_NATIVE", "gate_contract_parity": true, "gate_cost_aware_value": true, "gate_oracle_gain": false, "gate_oracle_gain_value": 0.0, "gate_rescue_asymmetry": true, "gate_rescue_row": {"failed_method": "MAP_D512_FAST", "rescue_method": "MAP_D1024_ROBUST", "rescue_rate_given_failure": 0.6548672566371682, "rescued_trial_count": 74, "reverse_rescue_count": 8, "schema_version": "oracle-portfolio-v0.1", "subset": "FINAL_NON_EASY", "verifier_accepted_rescue_count": 74, "verifier_accepted_rescue_rate_given_failure": 0.6548672566371682}, "gate_static_gain_fraction": 1.0, "gate_static_residual_regret": 0.0, "gate_static_route_sufficiency": true, "gate_verifier_gain_value": 0.0, "gate_verifier_viability": false}`

## Constraints

- No router, no hardware model, no new substrate implementation.
- Common clean-U1 F=3 semantic contract only.
- Dual-representation costs counted explicitly.

## Main interpretation

The direct oracle did not achieve the prospectively meaningful recovery improvement over the best fixed method on hard or pooled non-easy cells. This does not justify a practical router, FPGA model, or Lava seam.

