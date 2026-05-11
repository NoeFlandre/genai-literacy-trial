# Quantitative Report

## Executive Summary

- This report is generated from aggregate analysis tables produced by the quantitative pipeline.
- Participant-level analyses use one row per participant.
- The old n=90 prompt-grade p-values are not used.
- Model-specific sample sizes are reported in each table.
- Small-sample uncertainty should be interpreted using confidence intervals and effect sizes.

## Data Verification

| metric | observed | expected | status |
| --- | --- | --- | --- |
| missing_prompt_scores | 36 | 36 | pass |
| post_responses | 45 | 45 | pass |
| pre_responses | 55 | 55 | pass |
| prompt_assignment_rows | 180 | 180 | pass |
| retained_participants | 45 | 45 | pass |
| retained_survey_rows | 90 | 90 | pass |
| scored_prompt_observations | 144 | 144 | pass |

## Unit-of-Analysis Audit

participant-level analyses use one row per participant; old n=90 prompt-grade p-values are not used.

## Missingness

| group | assignment | n | scored | missing |
| --- | --- | --- | --- | --- |
| A | 1 | 13 | 13 | 0 |
| A | 2 | 13 | 9 | 4 |
| A | 3 | 13 | 10 | 3 |
| A | 4 | 13 | 12 | 1 |
| B | 1 | 13 | 11 | 2 |
| B | 2 | 13 | 9 | 4 |
| B | 3 | 13 | 12 | 1 |
| B | 4 | 13 | 12 | 1 |
| C | 1 | 19 | 19 | 0 |
| C | 2 | 19 | 10 | 9 |
| C | 3 | 19 | 12 | 7 |
| C | 4 | 19 | 15 | 4 |

## Baseline Balance

| metric | group | n | value | mean | sd | ci_low | ci_high | gender | major | prior_chatgpt_use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| retained_n | all | 45 | 45.0 | nan | nan | nan | nan | nan | nan | nan |
| midterm_points | A | 13 | nan | 2.661538461538462 | 1.1056962071763214 | 2.023076923076923 | 3.1923076923076925 | nan | nan | nan |
| midterm_points | B | 13 | nan | 2.5846153846153848 | 0.8792479303796643 | 2.0461538461538464 | 2.969230769230769 | nan | nan | nan |
| midterm_points | C | 19 | nan | 2.7526315789473683 | 0.6414986109386811 | 2.4577631578947363 | 3.015789473684211 | nan | nan | nan |
| final_points | A | 13 | nan | 2.692307692307693 | 0.9367154837173864 | 2.176923076923077 | 3.1692307692307695 | nan | nan | nan |
| final_points | B | 13 | nan | 2.661538461538461 | 0.7320501594135718 | 2.269230769230769 | 3.023076923076923 | nan | nan | nan |
| final_points | C | 19 | nan | 2.878947368421053 | 0.5421960975395659 | 2.6473684210526316 | 3.1159210526315775 | nan | nan | nan |
| mean_prompt_score | A | 13 | nan | 2.9102564102564106 | 0.554298792166419 | 2.6282051282051286 | 3.198717948717949 | nan | nan | nan |
| mean_prompt_score | B | 13 | nan | 2.9551282051282053 | 0.9680159313280146 | 2.4615384615384617 | 3.480769230769231 | nan | nan | nan |
| mean_prompt_score | C | 19 | nan | 3.570175438596491 | 0.8665879406438771 | 3.1710526315789473 | 3.929824561403509 | nan | nan | nan |
| suppressed | suppressed | 1 | nan | nan | nan | nan | nan | suppressed | nan | nan |
| gender | A | 12 | nan | nan | nan | nan | nan | Male | nan | nan |
| gender | B | 13 | nan | nan | nan | nan | nan | Male | nan | nan |
| suppressed | suppressed | 3 | nan | nan | nan | nan | nan | suppressed | nan | nan |
| gender | C | 16 | nan | nan | nan | nan | nan | Male | nan | nan |
| major | A | 10 | nan | nan | nan | nan | nan | nan | Computer Science | nan |
| suppressed | suppressed | 3 | nan | nan | nan | nan | nan | nan | suppressed | nan |
| major | B | 9 | nan | nan | nan | nan | nan | nan | Computer Science | nan |
| suppressed | suppressed | 2 | nan | nan | nan | nan | nan | nan | suppressed | nan |
| suppressed | suppressed | 1 | nan | nan | nan | nan | nan | nan | suppressed | nan |
| suppressed | suppressed | 1 | nan | nan | nan | nan | nan | nan | suppressed | nan |
| major | C | 18 | nan | nan | nan | nan | nan | nan | Computer Science | nan |
| suppressed | suppressed | 1 | nan | nan | nan | nan | nan | nan | suppressed | nan |
| suppressed | suppressed | 1 | nan | nan | nan | nan | nan | nan | nan | suppressed |
| suppressed | suppressed | 2 | nan | nan | nan | nan | nan | nan | nan | suppressed |
| suppressed | suppressed | 2 | nan | nan | nan | nan | nan | nan | nan | suppressed |
| suppressed | suppressed | 3 | nan | nan | nan | nan | nan | nan | nan | suppressed |
| prior_chatgpt_use | A | 5 | nan | nan | nan | nan | nan | nan | nan | Several times per semester |
| suppressed | suppressed | 2 | nan | nan | nan | nan | nan | nan | nan | suppressed |
| suppressed | suppressed | 2 | nan | nan | nan | nan | nan | nan | nan | suppressed |
| suppressed | suppressed | 1 | nan | nan | nan | nan | nan | nan | nan | suppressed |
| suppressed | suppressed | 2 | nan | nan | nan | nan | nan | nan | nan | suppressed |
| prior_chatgpt_use | B | 6 | nan | nan | nan | nan | nan | nan | nan | Several times per semester |
| suppressed | suppressed | 2 | nan | nan | nan | nan | nan | nan | nan | suppressed |
| suppressed | suppressed | 4 | nan | nan | nan | nan | nan | nan | nan | suppressed |
| prior_chatgpt_use | C | 5 | nan | nan | nan | nan | nan | nan | nan | Several days each week |
| prior_chatgpt_use | C | 8 | nan | nan | nan | nan | nan | nan | nan | Several times per semester |

## Primary Analysis: Prompt Quality Over Assignments

| model | term | estimate | ci_low | ci_high | p_value | n | r_squared | adj_r_squared | stability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| prompt_trajectory_mixedlm | Intercept | 2.8461538461538356 | 2.2874556652447846 | 3.4048520270628866 | 1.780781059856948e-23 | 144 | nan | nan | standard |
| prompt_trajectory_mixedlm | group[T.B] | -0.007327679132062616 | -0.8295755991413373 | 0.8149202408772119 | 0.9860642697745587 | 144 | nan | nan | standard |
| prompt_trajectory_mixedlm | group[T.C] | 1.0485829959514295 | 0.32352049282952366 | 1.7736454990733352 | 0.004589840062963138 | 144 | nan | nan | standard |
| prompt_trajectory_mixedlm | C(assignment)[T.2] | 0.5547336283605385 | -0.21149329891730162 | 1.3209605556383788 | 0.15590589437828456 | 144 | nan | nan | standard |
| prompt_trajectory_mixedlm | C(assignment)[T.3] | -0.4637052474438635 | -1.2047874672384826 | 0.2773769723507556 | 0.22005714423893474 | 144 | nan | nan | standard |
| prompt_trajectory_mixedlm | C(assignment)[T.4] | 0.15906509423321497 | -0.5391913701197459 | 0.857321558586176 | 0.6552460989696296 | 144 | nan | nan | standard |
| prompt_trajectory_mixedlm | group[T.B]:C(assignment)[T.2] | -0.7049892106584462 | -1.8108884886278638 | 0.40091006731097145 | 0.21150462603558673 | 144 | nan | nan | standard |
| prompt_trajectory_mixedlm | group[T.C]:C(assignment)[T.2] | -1.4263363105668745 | -2.4639302505154603 | -0.38874237061828887 | 0.007054104141712823 | 144 | nan | nan | standard |
| prompt_trajectory_mixedlm | group[T.B]:C(assignment)[T.3] | 0.7331746028314103 | -0.3096783641038514 | 1.776027569766672 | 0.16821974153666974 | 144 | nan | nan | standard |
| prompt_trajectory_mixedlm | group[T.C]:C(assignment)[T.3] | -0.12054416810961996 | -1.111336300684332 | 0.870247964465092 | 0.8115259514223697 | 144 | nan | nan | standard |
| prompt_trajectory_mixedlm | group[T.B]:C(assignment)[T.4] | 0.11040426115433148 | -0.9048042493463204 | 1.1256127716549833 | 0.8312125157152845 | 144 | nan | nan | standard |
| prompt_trajectory_mixedlm | group[T.C]:C(assignment)[T.4] | -0.15513996976127048 | -1.0811254980078853 | 0.7708455584853442 | 0.7426295673576363 | 144 | nan | nan | standard |
| prompt_trajectory_mixedlm | Group Var | 0.34292226224007516 | -0.006673417434619799 | 0.6925179419147701 | 0.05453654912322342 | 144 | nan | nan | standard |

## Participant-Level Robustness

| contrast | mean_difference | hedges_g | ci_low | ci_high | p_value | n |
| --- | --- | --- | --- | --- | --- | --- |
| C vs A | 0.6599190283400804 | 0.8494565245885356 | 0.21677843280179307 | 1.9692303129268283 | nan | 32 |
| C vs B | 0.6150472334682857 | 0.6599111915278034 | -0.013424313147800106 | 1.7108336450309234 | nan | 32 |
| B vs A | 0.04487179487179471 | 0.05509215528733113 | -0.7605302552346401 | 0.8795489215490018 | nan | 26 |
| C vs pooled A+B | 0.6374831309041835 | 0.7698062634970416 | 0.17571718454776897 | 1.6686738149900378 | nan | 45 |

## Learning Outcomes

| metric | method | correlation | p_value | ci_low | ci_high | n |
| --- | --- | --- | --- | --- | --- | --- |
| mean_prompt_score vs midterm_points | pearson | 0.2887452333645937 | 0.054398388186974816 | -0.005237693286958159 | 0.5367872208715337 | 45 |
| mean_prompt_score vs midterm_points | spearman | 0.22907624378355032 | 0.13011313395958726 | -0.08433168880468749 | 0.5032409906645393 | 45 |
| mean_prompt_score vs final_points | pearson | 0.45083562044288217 | 0.0018836739698695657 | 0.18128787455283193 | 0.6573785571662835 | 45 |
| mean_prompt_score vs final_points | spearman | 0.43010029288537976 | 0.003189561014732064 | 0.17429923453041288 | 0.6309697654949358 | 45 |

Targeted perceived-usefulness models:

| model | term | std_beta | ci_low | ci_high | p_value | n | r_squared | adj_r_squared | stability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| final_points | perceived_usefulness_z | -0.021644458760359697 | -0.33706509189688405 | 0.29377617437616466 | 0.8930115115809637 | 32 | 0.27298994089267115 | 0.13318031414126175 | standard |
| grade_change | perceived_usefulness_z | 0.20790727628267774 | -0.06746285140857622 | 0.4832774039739317 | 0.13892851065405606 | 32 | 0.10075006590452595 | -0.03247214655406272 | standard |

## Calibration: Beliefs vs Actual Prompt Skill

| model | term | std_beta | ci_low | ci_high | p_value | n | r_squared | adj_r_squared | stability | dimension | fdr_p_value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| trust | trust_z | -0.2573730386094896 | -0.6275324323312557 | 0.11278635511227636 | 0.17295520519737517 | 32 | 0.2570288684742612 | 0.14695907121118879 | standard | trust | 0.40064678543199783 |
| perceived_usefulness | perceived_usefulness_z | -0.3049780159947459 | -0.7488258662895056 | 0.13886983430001387 | 0.1780652379697768 | 32 | 0.2544687172518594 | 0.1440196383262089 | standard | perceived_usefulness | 0.40064678543199783 |
| perceived_ease_of_use | perceived_ease_of_use_z | -0.38043621874467304 | -0.7492533513862285 | -0.011619086103117515 | 0.04320631963997885 | 32 | 0.3131137117195273 | 0.2113527801224202 | standard | perceived_ease_of_use | 0.1944284383799048 |
| behavioral_intention | behavioral_intention_z | -0.26918609618795813 | -0.8624969744341058 | 0.32412478205818945 | 0.3738747542699502 | 32 | 0.23961983010320909 | 0.12697091604442523 | standard | behavioral_intention | 0.6729745576859104 |
| hedonic_motivation | hedonic_motivation_z | 0.029940725749463472 | -0.22456796995571324 | 0.2844494214546402 | 0.8176468180995695 | 32 | 0.1763543585171996 | 0.05433278200122915 | standard | hedonic_motivation | 0.8349261363266501 |
| locus_of_control | locus_of_control_z | -0.45353999810550677 | -0.8032747302682411 | -0.1038052659427724 | 0.011031364623890701 | 32 | 0.4083688637927061 | 0.32071980657681065 | standard | locus_of_control | 0.09928228161501632 |
| facilitating_conditions | facilitating_conditions_z | -0.10093828177890235 | -0.4265501829833464 | 0.2246736194255417 | 0.5434658284230945 | 32 | 0.18302036845140046 | 0.06198634896271904 | standard | facilitating_conditions | 0.6987417794011216 |
| social_influence | social_influence_z | -0.10565808846731703 | -0.42164716144566916 | 0.21033098451103513 | 0.512237120721268 | 32 | 0.1873147363682236 | 0.06691691953388634 | standard | social_influence | 0.6987417794011216 |
| attitude | attitude_z | -0.07314424784292578 | -0.76109263880621 | 0.6148041431203586 | 0.8349261363266501 | 32 | 0.17974617488151867 | 0.05822708967878065 | standard | attitude | 0.8349261363266501 |

## Secondary Pre/Post Survey Change

| dimension | pre_mean | post_mean | change | ci_low | ci_high | n | phase_p_value | interaction_p_value | fdr_p_value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| perceived_usefulness | 3.761111111111111 | 3.8444444444444446 | 0.08333333333333333 | -0.17222222222222222 | 0.3111111111111111 | 45 | nan | nan | 1.0 |
| perceived_ease_of_use | 3.803703703703703 | 3.7888888888888896 | -0.01481481481481482 | -0.24074074074074067 | 0.174074074074074 | 45 | nan | nan | 1.0 |
| behavioral_intention | 3.8592592592592596 | 3.977777777777778 | 0.11851851851851854 | -0.177962962962963 | 0.38537037037037025 | 45 | nan | nan | 1.0 |
| hedonic_motivation | 3.7851851851851843 | 3.6962962962962957 | -0.08888888888888889 | -0.3703703703703703 | 0.126111111111111 | 45 | nan | nan | 1.0 |
| locus_of_control | 3.088888888888889 | 3.077777777777778 | -0.011111111111111112 | -0.2722222222222222 | 0.2111111111111111 | 45 | nan | nan | 1.0 |
| trust | 3.1666666666666665 | 3.3962962962962964 | 0.22962962962962966 | 0.010925925925925927 | 0.4481481481481481 | 45 | nan | nan | 1.0 |
| facilitating_conditions | 3.933333333333333 | 4.066666666666666 | 0.13333333333333333 | -0.2 | 0.4444444444444444 | 45 | nan | nan | 1.0 |
| social_influence | 3.2888888888888888 | 3.511111111111111 | 0.2222222222222222 | -0.13388888888888886 | 0.6 | 45 | nan | nan | 1.0 |
| attitude | 3.8962962962962964 | 3.837037037037036 | -0.05925925925925925 | -0.2668518518518519 | 0.12592592592592594 | 45 | nan | nan | 1.0 |

## Small-Sample Sensitivity

| detectable_d_a_vs_b_80_power | detectable_d_c_vs_pooled_ab_80_power | detectable_r_n45_80_power | interpretation |
| --- | --- | --- | --- |
| 1.0988721304731635 | 0.8455642631813689 | 0.40723664075787896 | Powered only for relatively large effects; do not claim sample-size adequacy. |

## Manuscript-Ready Quantitative Paragraphs

The quantitative pipeline retained 45 participants and 90 paired survey rows. Prompt analyses used 144 scored assignment observations for assignment-level models. Prompt-grade relationships were evaluated at the participant level, and the old duplicated n=90 prompt-grade p-values were not used.
At the participant level, mean prompt quality was higher for Group C than pooled Groups A and B (mean difference=0.637, Hedges g=0.77, 95% CI for g [0.176, 1.67], n=45).
Mean prompt quality was associated with final grade in the participant-level descriptive analysis (Pearson r=0.451, 95% CI [0.181, 0.657], p=0.00188, n=45).
The targeted adjusted model did not support a strong participant-level negative association between pre-test perceived usefulness and final grade (standardized beta=-0.0216, 95% CI [-0.337, 0.294], p=0.893, n=32).
Small-sample sensitivity indicates that the study is powered only for relatively large effects (approximate 80% detectable d for A vs B=1.1).

## Files Generated

- `table_data_verification.csv`
- `table_missingness_prompt_by_group_assignment.csv`
- `table_baseline_balance.csv`
- `table_prompt_trajectory_model.csv`
- `table_prompt_trajectory_estimated_means.csv`
- `table_participant_training_contrasts.csv`
- `table_learning_outcome_models.csv`
- `table_prompt_grade_correlations.csv`
- `table_calibration_models.csv`
- `table_survey_reliability.csv`
- `table_prepost_survey_change.csv`
- `table_small_sample_sensitivity.csv`
- `table_perceived_usefulness_models.csv`
- `fig_prompt_quality_trajectory.pdf`
- `fig_prompt_quality_trajectory.png`
- `fig_prompt_quality_learning_outcome.pdf`
- `fig_prompt_quality_learning_outcome.png`
- `fig_calibration_forest.pdf`
- `fig_calibration_forest.png`

## Privacy Verification

No raw identifiers, participant-level rows, raw survey responses, individual grades, or raw transcripts were written to public outputs.
