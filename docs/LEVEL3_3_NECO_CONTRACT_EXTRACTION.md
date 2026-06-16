# Level 3.3 NeCo Contract Extraction

- Paper: [Linear Codes for Hyperdimensional Computing](https://arxiv.org/abs/2403.03278)
- Status: `UNAMBIGUOUS_PAPER_CONTRACT`
- Checkpoint: `a3ca3b3536837447a6d8177e1b0b36a5258772fa`

## Author status

- Official/public NeCo implementation: unavailable in the audited repo context.
- Author correspondence summary: the relevant clean algebra is expected to require little beyond Gaussian elimination over F2.
- This repository contains an independent paper-specific reproduction, not an official implementation.
- Replacement rule: delete or replace the custom reproduction when a suitable audited upstream appears.

## Extracted contract

- `representation_alphabet_field`: Binary field F_2 represented as real {+1,-1}; Boolean 1 is encoded as real -1 and Boolean 0 as real +1. (Section 'A primer on linear codes', lines 304-305; Tables 1-2.)
- `hypervector_codeword_construction`: An [n,k]_2 linear code is represented by a generator matrix G in F_2^{k x n}; codewords are xG for x in F_2^k. (Section 'A primer on linear codes', lines 340-342.)
- `factor_subcode_construction`: Factor domains are subcodes formed from disjoint subsets of a linearly independent basis so that the global code is a direct sum/product of subcodes. (Subcode discussion and example, lines 368-376.)
- `binding_operation`: Binding for clean recovery is Boolean addition/XOR, implemented as point-wise multiplication in the +/-1 representation. (Section 'A primer on linear codes', line 304; Section 'oplus-recovery', lines 580-584.)
- `recovery_inputs`: Input is an observation c in {+1,-1}^n and linear factor codes C_1,...,C_F. (Section 'oplus-recovery', lines 580-584.)
- `recovery_outputs`: Output is one vector c_i in each factor code C_i such that c equals XOR/bind of the recovered factors. (Section 'oplus-recovery', lines 580-584.)
- `basis_recovery_algorithm`: Find a maximal linearly independent subset B' from the union of factor-code bases, arrange it as matrix B, solve xB = c over F_2, then reconstruct each factor from coefficients in B' intersect B_i. (Theorem and proof in Section 'oplus-recovery', lines 594-606.)
- `uniqueness_condition`: Unique factor recovery requires the factor subcodes to behave as a direct sum/product with trivial intersections. (Remark XORuniqueness, lines 606-608; subcode product discussion lines 368-376.)
- `failure_conditions`: Non-unique decomposition appears when factor subcodes overlap nontrivially; clean noise-free decoding does not cover noisy linear-code decoding. (Remark XORuniqueness lines 606-608; decoding-with-noise caveat near end of preliminaries.)
- `complexity_claim`: The clean XOR-recovery algorithm has complexity at most O(Delta^3 n), where Delta is the sum of factor-code dimensions. (Complexity paragraph immediately after the oplus-recovery proof.)
- `native_benchmark_setup`: The paper reports n in {500,1000,2000}, k in {3,5,7}, F in {3,4,5}, each repeated 10 times, with success defined by factor membership plus exact rebind to the observation. (Experiments subsection 'oplus-recovery', lines 765-773.)
- `dependency_note`: The experiments were implemented with standard Python libraries including galois for F_2 computations. (Experiments subsection 'oplus-recovery', lines 766 and 792.)
