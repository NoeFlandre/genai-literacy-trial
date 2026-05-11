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
| C vs A | 0.6599190283400804 | 0.8494565245885356 | 0.21677843280179307 | 1.9692303129268283 | 0.020989505247376312 | 32 |
| C vs B | 0.6150472334682857 | 0.6599111915278034 | -0.013424313147800106 | 1.7108336450309234 | 0.07246376811594203 | 32 |
| B vs A | 0.04487179487179471 | 0.05509215528733113 | -0.7605302552346401 | 0.8795489215490018 | 0.896551724137931 | 26 |
| C vs pooled A+B | 0.6374831309041835 | 0.7698062634970416 | 0.17571718454776897 | 1.6686738149900378 | 0.013993003498250875 | 45 |

## Learning Outcomes

| metric | method | correlation | p_value | ci_low | ci_high | n |
| --- | --- | --- | --- | --- | --- | --- |
| mean_prompt_score vs midterm_points | pearson | 0.2887452333645937 | 0.054398388186974816 | -0.005237693286958159 | 0.5367872208715337 | 45 |
| mean_prompt_score vs midterm_points | spearman | 0.22907624378355032 | 0.13011313395958726 | -0.08433168880468749 | 0.5032409906645393 | 45 |
| mean_prompt_score vs final_points | pearson | 0.45083562044288217 | 0.0018836739698695657 | 0.18128787455283193 | 0.6573785571662835 | 45 |
| mean_prompt_score vs final_points | spearman | 0.43010029288537976 | 0.003189561014732064 | 0.17429923453041288 | 0.6309697654949358 | 45 |

Adjusted learning-outcome models:

| model | term | estimate | ci_low | ci_high | p_value | n | r_squared | adj_r_squared | stability | std_beta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| final_points | Intercept | 1.374678562212819 | -0.5721882166936583 | 3.3215453411192963 | 0.1663809701838005 | 32 | 0.3950819697162049 | 0.27875157927701355 | standard | nan |
| final_points | group[T.B] | -0.16343094875670328 | -0.8654577760930959 | 0.5385958785796894 | 0.6481907202623595 | 32 | 0.3950819697162049 | 0.27875157927701355 | standard | nan |
| final_points | group[T.C] | -0.0829511743582434 | -0.7475277644108109 | 0.5816254156943241 | 0.8067360082931219 | 32 | 0.3950819697162049 | 0.27875157927701355 | standard | nan |
| final_points | mean_prompt_score | 0.33024036388636724 | -0.044269828828168545 | 0.704750556600903 | 0.08393768116341052 | 32 | 0.3950819697162049 | 0.27875157927701355 | standard | 0.3976625347187168 |
| final_points | midterm_points | 0.2930104445162164 | -0.2397659784355004 | 0.8257868674679332 | 0.28106983069976166 | 32 | 0.3950819697162049 | 0.27875157927701355 | standard | 0.34554585824272105 |
| final_points | prior_chatgpt_use_score | -0.09692507535703163 | -0.28158136136297024 | 0.08773121064890699 | 0.3035857065947686 | 32 | 0.3950819697162049 | 0.27875157927701355 | standard | -0.16413510818529262 |
| grade_change | Intercept | 0.006959833289353734 | -1.3520994283368557 | 1.366019094915563 | 0.9919916821314856 | 32 | 0.07610646020708278 | -0.06076665679927529 | standard | nan |
| grade_change | group[T.B] | 0.13398696874775465 | -0.8201970678560213 | 1.0881710053515306 | 0.78314794482086 | 32 | 0.07610646020708278 | -0.06076665679927529 | standard | nan |
| grade_change | group[T.C] | 0.16251347564792873 | -0.39617553642974535 | 0.7212024877256028 | 0.5685953645421726 | 32 | 0.07610646020708278 | -0.06076665679927529 | standard | nan |
| grade_change | mean_prompt_score | 0.13938185853459845 | -0.24427889375245576 | 0.5230426108216526 | 0.47643739091182846 | 32 | 0.07610646020708278 | -0.06076665679927529 | standard | 0.16442193428840335 |
| grade_change | prior_chatgpt_use_score | -0.1404055723294399 | -0.3901967206784607 | 0.10938557601958085 | 0.2706008972422609 | 32 | 0.07610646020708278 | -0.06076665679927529 | standard | -0.23292637194151558 |

Targeted perceived-usefulness models:

| model | term | estimate | ci_low | ci_high | p_value | n | r_squared | adj_r_squared | stability | std_beta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| final_points | perceived_usefulness_z | -0.029823436286986978 | -0.46443477307754255 | 0.4047879005035686 | 0.8930115115809609 | 32 | 0.27298994089267115 | 0.13318031414126175 | standard | -0.029823436286986978 |
| grade_change | perceived_usefulness_z | 0.25673746647269474 | -0.08330752949748868 | 0.5967824624428781 | 0.13892851065405595 | 32 | 0.10075006590452618 | -0.0324721465540625 | standard | 0.25673746647269474 |

## Calibration: Beliefs vs Actual Prompt Skill

| model | term | estimate | ci_low | ci_high | p_value | n | r_squared | adj_r_squared | stability | std_beta | dimension | fdr_p_value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| trust | trust_z | -0.29413939993547494 | -0.7171769587179998 | 0.12889815884704994 | 0.1729552051973735 | 32 | 0.2570288684742611 | 0.14695907121118867 | standard | -0.29413939993547494 | trust | 0.4006467854319993 |
| perceived_usefulness | perceived_usefulness_z | -0.34618000024021894 | -0.8499909009062785 | 0.1576309004258406 | 0.17806523796977747 | 32 | 0.2544687172518594 | 0.1440196383262089 | standard | -0.34618000024021894 | perceived_usefulness | 0.4006467854319993 |
| perceived_ease_of_use | perceived_ease_of_use_z | -0.4127830254166533 | -0.8129590453014799 | -0.01260700553182665 | 0.043206319639979014 | 32 | 0.3131137117195273 | 0.2113527801224202 | standard | -0.4127830254166533 | perceived_ease_of_use | 0.19442843837990556 |
| behavioral_intention | behavioral_intention_z | -0.2994281930925104 | -0.9593954303725791 | 0.3605390441875583 | 0.3738747542699479 | 32 | 0.23961983010320909 | 0.12697091604442523 | standard | -0.2994281930925104 | behavioral_intention | 0.6729745576859061 |
| hedonic_motivation | hedonic_motivation_z | 0.036658509591454086 | -0.2749541594095347 | 0.3482711785924429 | 0.8176468180995744 | 32 | 0.1763543585171996 | 0.05433278200122915 | standard | 0.036658509591454086 | hedonic_motivation | 0.8349261363266525 |
| locus_of_control | locus_of_control_z | -0.5430931694238887 | -0.9618843343515064 | -0.12430200449627113 | 0.01103136462389088 | 32 | 0.4083688637927061 | 0.32071980657681065 | standard | -0.5430931694238887 | locus_of_control | 0.09928228161501793 |
| facilitating_conditions | facilitating_conditions_z | -0.12403484224231792 | -0.5241528161798887 | 0.27608313169525284 | 0.5434658284230907 | 32 | 0.18302036845140046 | 0.06198634896271904 | standard | -0.12403484224231792 | facilitating_conditions | 0.6987417794011165 |
| social_influence | social_influence_z | -0.12226964971234355 | -0.4879385145048626 | 0.24339921508017548 | 0.512237120721269 | 32 | 0.18731473636822338 | 0.06691691953388612 | standard | -0.12226964971234355 | social_influence | 0.6987417794011165 |
| attitude | attitude_z | -0.07856930703060294 | -0.8175423629416834 | 0.6604037488804775 | 0.8349261363266525 | 32 | 0.17974617488151845 | 0.05822708967878043 | standard | -0.07856930703060294 | attitude | 0.8349261363266525 |

## Secondary Pre/Post Survey Change

| dimension | pre_mean | post_mean | change | ci_low | ci_high | n | phase_p_value | interaction_p_value | fdr_p_value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| perceived_usefulness | 3.761111111111111 | 3.8444444444444446 | 0.08333333333333333 | -0.17222222222222222 | 0.3111111111111111 | 45 | 0.49654461507172737 | nan | 0.744816922607591 |
| perceived_ease_of_use | 3.803703703703703 | 3.7888888888888896 | -0.01481481481481482 | -0.24074074074074067 | 0.174074074074074 | 45 | 0.8896729998916534 | nan | 0.9264640142943755 |
| behavioral_intention | 3.8592592592592596 | 3.977777777777778 | 0.11851851851851854 | -0.177962962962963 | 0.38537037037037025 | 45 | 0.435597692267614 | nan | 0.744816922607591 |
| hedonic_motivation | 3.7851851851851843 | 3.6962962962962957 | -0.08888888888888889 | -0.3703703703703703 | 0.126111111111111 | 45 | 0.4901935624488351 | nan | 0.744816922607591 |
| locus_of_control | 3.088888888888889 | 3.077777777777778 | -0.011111111111111112 | -0.2722222222222222 | 0.2111111111111111 | 45 | 0.9264640142943756 | nan | 0.9264640142943755 |
| trust | 3.1666666666666665 | 3.3962962962962964 | 0.22962962962962966 | 0.010925925925925927 | 0.4481481481481481 | 45 | 0.04175767529380268 | nan | 0.3758190776442241 |
| facilitating_conditions | 3.933333333333333 | 4.066666666666666 | 0.13333333333333333 | -0.2 | 0.4444444444444444 | 45 | 0.40221799249071205 | nan | 0.744816922607591 |
| social_influence | 3.2888888888888888 | 3.511111111111111 | 0.2222222222222222 | -0.13388888888888886 | 0.6 | 45 | 0.2361411829906664 | nan | 0.744816922607591 |
| attitude | 3.8962962962962964 | 3.837037037037036 | -0.05925925925925925 | -0.2668518518518519 | 0.12592592592592594 | 45 | 0.5830141762339018 | nan | 0.7495896551578738 |

## Small-Sample Sensitivity

| detectable_d_a_vs_b_80_power | detectable_d_c_vs_pooled_ab_80_power | detectable_r_n45_80_power | interpretation |
| --- | --- | --- | --- |
| 1.0988721304731635 | 0.8455642631813689 | 0.40723664075787896 | Powered only for relatively large effects; do not claim sample-size adequacy. |

## Manuscript-Ready Quantitative Paragraphs

The quantitative pipeline retained 45 participants and 90 paired survey rows. Prompt analyses used 144 scored assignment observations for assignment-level models. Prompt-grade relationships were evaluated at the participant level, and the old duplicated n=90 prompt-grade p-values were not used.
At the participant level, mean prompt quality was higher for Group C than pooled Groups A and B (mean difference=0.637, Hedges g=0.77, 95% CI for g [0.176, 1.67], n=45).
Mean prompt quality was associated with final grade in the participant-level descriptive analysis (Pearson r=0.451, 95% CI [0.181, 0.657], p=0.00188, n=45).
The targeted adjusted model did not support a strong participant-level negative association between pre-test perceived usefulness and final grade (standardized beta=-0.0298, 95% CI [-0.464, 0.405], p=0.893, n=32).
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
