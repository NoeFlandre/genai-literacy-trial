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
| group_count_A | 13 | 13 | pass |
| group_count_B | 13 | 13 | pass |
| group_count_C | 19 | 19 | pass |
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
| gender | A | 12 | nan | nan | nan | nan | nan | Male | nan | nan |
| gender | B | 13 | nan | nan | nan | nan | nan | Male | nan | nan |
| gender | C | 16 | nan | nan | nan | nan | nan | Male | nan | nan |
| gender | A | suppressed | nan | nan | nan | nan | nan | Other/suppressed | nan | nan |
| gender | C | suppressed | nan | nan | nan | nan | nan | Other/suppressed | nan | nan |
| major | A | 10 | nan | nan | nan | nan | nan | nan | Computer Science | nan |
| major | B | 9 | nan | nan | nan | nan | nan | nan | Computer Science | nan |
| major | C | 18 | nan | nan | nan | nan | nan | nan | Computer Science | nan |
| major | A | suppressed | nan | nan | nan | nan | nan | nan | Other/suppressed | nan |
| major | B | suppressed | nan | nan | nan | nan | nan | nan | Other/suppressed | nan |
| major | C | suppressed | nan | nan | nan | nan | nan | nan | Other/suppressed | nan |
| prior_chatgpt_use | A | 5 | nan | nan | nan | nan | nan | nan | nan | Several times per semester |
| prior_chatgpt_use | B | 6 | nan | nan | nan | nan | nan | nan | nan | Several times per semester |
| prior_chatgpt_use | C | 5 | nan | nan | nan | nan | nan | nan | nan | Several days each week |
| prior_chatgpt_use | C | 8 | nan | nan | nan | nan | nan | nan | nan | Several times per semester |
| prior_chatgpt_use | A | suppressed | nan | nan | nan | nan | nan | nan | nan | Other/suppressed |
| prior_chatgpt_use | B | suppressed | nan | nan | nan | nan | nan | nan | nan | Other/suppressed |
| prior_chatgpt_use | C | suppressed | nan | nan | nan | nan | nan | nan | nan | Other/suppressed |

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

| contrast | mean_difference | mean_difference_ci_low | mean_difference_ci_high | hedges_g | hedges_g_ci_low | hedges_g_ci_high | p_value | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C vs A | 0.6599190283400804 | 0.18077766531713874 | 1.1124240890688262 | 0.8494565245885356 | 0.21677843280179307 | 1.9692303129268283 | 0.020989505247376312 | 32 |
| C vs B | 0.6150472334682857 | -0.021634615384616026 | 1.2328525641025636 | 0.6599111915278034 | -0.013424313147800106 | 1.7108336450309234 | 0.07246376811594203 | 32 |
| B vs A | 0.04487179487179471 | -0.5262820512820516 | 0.647596153846154 | 0.05509215528733113 | -0.7605302552346401 | 0.8795489215490018 | 0.896551724137931 | 26 |
| C vs pooled A+B | 0.6374831309041835 | 0.1549426450742232 | 1.0751602564102565 | 0.7698062634970416 | 0.17571718454776897 | 1.6686738149900378 | 0.013993003498250875 | 45 |

Omnibus training-effect tests:

| test | statistic | p_value |
| --- | --- | --- |
| welch_anova | 3.5901062186610364 | 0.042067911466339494 |
| kruskal_wallis | 8.417069252701523 | 0.014868139762776528 |
| permutation_anova | 3.3027352386976063 | 0.03796203796203796 |

Scored assignment distribution by group:

| group | scored_assignments | n |
| --- | --- | --- |
| A | 2 | 1 |
| A | 3 | 6 |
| A | 4 | 6 |
| B | 2 | 2 |
| B | 3 | 4 |
| B | 4 | 7 |
| C | 1 | 1 |
| C | 2 | 5 |
| C | 3 | 7 |
| C | 4 | 6 |

Missing-prompt sensitivity, at least three scored assignments:

| model | term | estimate | ci_low | ci_high | p_value | n | r_squared | adj_r_squared | stability | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| min3_scored_assignments | Intercept | 0.9797177363689489 | -1.697965309241749 | 3.657400781979647 | 0.473302034773077 | 36 | 0.5609622625260904 | 0.4701268685659712 | standard | run |
| min3_scored_assignments | group[T.B] | -0.18134022281595652 | -0.7634602684985012 | 0.4007798228665882 | 0.5414896698894691 | 36 | 0.5609622625260904 | 0.4701268685659712 | standard | run |
| min3_scored_assignments | group[T.C] | -0.10105386841691844 | -0.6579496309885836 | 0.45584189415474674 | 0.7221000517073881 | 36 | 0.5609622625260904 | 0.4701268685659712 | standard | run |
| min3_scored_assignments | mean_prompt_score | 0.34796296028521173 | -0.06832207554907616 | 0.7642479961194997 | 0.10136158400429784 | 36 | 0.5609622625260904 | 0.4701268685659712 | standard | run |
| min3_scored_assignments | midterm_points | 0.5317877738302725 | 0.2943585252459223 | 0.7692170224146228 | 1.1341548181384073e-05 | 36 | 0.5609622625260904 | 0.4701268685659712 | standard | run |
| min3_scored_assignments | prior_chatgpt_use_score | -0.09212076075535752 | -0.3030527841676346 | 0.11881126265691952 | 0.39200941933267763 | 36 | 0.5609622625260904 | 0.4701268685659712 | standard | run |
| min3_scored_assignments | scored_assignments | -0.11141660298969702 | -0.6308014139027032 | 0.4079682079233091 | 0.6741607064265547 | 36 | 0.5609622625260904 | 0.4701268685659712 | standard | run |

Missing-prompt sensitivity, all four scored assignments:

| model | status | n |
| --- | --- | --- |
| all4_scored_assignments | not_run_small_n | 19 |

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
| final_points | Intercept | 1.1435457475586652 | -0.05960989158135099 | 2.3467013866986814 | 0.062482203718806945 | 45 | 0.4395618991919227 | 0.3677108606267846 | standard | nan |
| final_points | group[T.B] | -0.0035650395777174215 | -0.5768557301758019 | 0.569725651020367 | 0.99027550928022 | 45 | 0.4395618991919227 | 0.3677108606267846 | standard | nan |
| final_points | group[T.C] | 0.012521747234972042 | -0.4261201260570112 | 0.45116362052695536 | 0.9553813469175843 | 45 | 0.4395618991919227 | 0.3677108606267846 | standard | nan |
| final_points | mean_prompt_score | 0.25582608780811134 | -0.029256556253143273 | 0.5409087318693659 | 0.07860757267438812 | 45 | 0.4395618991919227 | 0.3677108606267846 | standard | 0.30805577285504626 |
| final_points | midterm_points | 0.40979365185129896 | 0.055432090208506146 | 0.7641552134940918 | 0.02341728058288702 | 45 | 0.4395618991919227 | 0.3677108606267846 | standard | 0.4832677530153335 |
| final_points | prior_chatgpt_use_score | -0.09309271819311192 | -0.2472730825666279 | 0.061087646180404034 | 0.23664723588723158 | 45 | 0.4395618991919227 | 0.3677108606267846 | standard | -0.1542162958707832 |
| grade_change | Intercept | 0.09903405056080139 | -0.9564467693830672 | 1.15451487050467 | 0.8540917193223658 | 45 | 0.03730780541396683 | -0.05896141404463662 | standard | nan |
| grade_change | group[T.B] | 0.05010893621778689 | -0.69427167676711 | 0.7944895492026838 | 0.8950337344395976 | 45 | 0.03730780541396683 | -0.05896141404463662 | standard | nan |
| grade_change | group[T.C] | 0.07621476762795129 | -0.38160223154864714 | 0.5340317668045498 | 0.7442097604600415 | 45 | 0.03730780541396683 | -0.05896141404463662 | standard | nan |
| grade_change | mean_prompt_score | 0.08063477075577166 | -0.27675254120140946 | 0.43802208271295273 | 0.6583352190202755 | 45 | 0.03730780541396683 | -0.05896141404463662 | standard | 0.0951208795603405 |
| grade_change | prior_chatgpt_use_score | -0.09845312043876123 | -0.28671696022428383 | 0.08981071934676138 | 0.3053778887328493 | 45 | 0.03730780541396683 | -0.05896141404463662 | standard | -0.1597765433733991 |

Complete-case diagnostics; loss columns are marginal and non-additive:

| model | starting_n | final_n | loss_type | lost_final_grade | lost_midterm_grade | lost_mean_prompt_score | lost_prior_chatgpt_use_score | lost_survey_composite | lost_group |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| final_points | 45 | 45 | marginal_non_additive | 0 | 0 | 0 | 0 | 0 | 0 |
| grade_change | 45 | 45 | marginal_non_additive | 0 | 0 | 0 | 0 | 0 | 0 |
| perceived_usefulness_final_points | 45 | 45 | marginal_non_additive | 0 | 0 | 0 | 0 | 0 | 0 |
| perceived_usefulness_grade_change | 45 | 45 | marginal_non_additive | 0 | 0 | 0 | 0 | 0 | 0 |
| calibration_trust | 45 | 45 | marginal_non_additive | 0 | 0 | 0 | 0 | 0 | 0 |
| calibration_perceived_usefulness | 45 | 45 | marginal_non_additive | 0 | 0 | 0 | 0 | 0 | 0 |
| calibration_perceived_ease_of_use | 45 | 45 | marginal_non_additive | 0 | 0 | 0 | 0 | 0 | 0 |
| calibration_behavioral_intention | 45 | 45 | marginal_non_additive | 0 | 0 | 0 | 0 | 0 | 0 |
| calibration_hedonic_motivation | 45 | 45 | marginal_non_additive | 0 | 0 | 0 | 0 | 0 | 0 |
| calibration_locus_of_control | 45 | 45 | marginal_non_additive | 0 | 0 | 0 | 0 | 0 | 0 |
| calibration_facilitating_conditions | 45 | 45 | marginal_non_additive | 0 | 0 | 0 | 0 | 0 | 0 |
| calibration_social_influence | 45 | 45 | marginal_non_additive | 0 | 0 | 0 | 0 | 0 | 0 |
| calibration_attitude | 45 | 45 | marginal_non_additive | 0 | 0 | 0 | 0 | 0 | 0 |

Prior ChatGPT-use coding:

| prior_chatgpt_use | n | mapped_score | mapped_status |
| --- | --- | --- | --- |
| At least once per week | 5 | 4.0 | mapped |
| I tried it once or twice | 8 | 2.0 | mapped |
| Never | suppressed | 1.0 | mapped |
| Several days each week | 10 | 5.0 | mapped |
| Several times per semester | 19 | 3.0 | mapped |

Targeted perceived-usefulness models:

| model | term | estimate | ci_low | ci_high | p_value | n | r_squared | adj_r_squared | stability | std_beta | std_ci_low | std_ci_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| final_points | perceived_usefulness_z | -0.05101871741598929 | -0.26804868760544326 | 0.16601125277346468 | 0.6449836317911224 | 45 | 0.36716564037816957 | 0.2860330301702426 | standard | -0.07102114720357074 | -0.3731400212382424 | 0.23109772683110097 |
| grade_change | perceived_usefulness_z | 0.15226785806393336 | -0.060479601997334625 | 0.3650153181252014 | 0.16068015924388312 | 45 | 0.05788777729214656 | -0.03632344497863893 | standard | 0.20765163974589673 | -0.08247760680164475 | 0.49778088629343825 |

## Calibration: Beliefs vs Actual Prompt Skill

Survey reliability:

| dimension | n_items | cronbach_alpha |
| --- | --- | --- |
| perceived_usefulness | 4 | 0.8296698773359676 |
| perceived_ease_of_use | 6 | 0.7836627470602953 |
| behavioral_intention | 3 | 0.9722351843210452 |
| hedonic_motivation | 3 | 0.8841718322041228 |
| locus_of_control | 4 | 0.6506311418116029 |
| trust | 6 | 0.5862857142857142 |
| facilitating_conditions | 1 | nan |
| social_influence | 1 | nan |
| attitude | 3 | 0.9132081426542527 |

| model | term | estimate | ci_low | ci_high | p_value | n | r_squared | adj_r_squared | stability | std_beta | std_ci_low | std_ci_high | dimension | fdr_p_value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| trust | trust_z | -0.17473323046590616 | -0.47356069868393774 | 0.12409423775212541 | 0.25177499222476596 | 45 | 0.17705024426346105 | 0.0947552686898071 | standard | -0.20199895869920104 | -0.5474560720932038 | 0.14345815469480178 | trust | 0.5664937325057234 |
| perceived_usefulness | perceived_usefulness_z | -0.2097874991397451 | -0.5427910475891986 | 0.12321604930970842 | 0.21692377205748303 | 45 | 0.1766924973420756 | 0.09436174707628309 | standard | -0.24252316666580823 | -0.627489265275503 | 0.14244293194388652 | perceived_usefulness | 0.5664937325057234 |
| perceived_ease_of_use | perceived_ease_of_use_z | -0.2584649246669142 | -0.541268750109 | 0.024338900775171646 | 0.07324774599539671 | 45 | 0.21855347668452274 | 0.14040882435297497 | standard | -0.2987963165550883 | -0.6257294254041138 | 0.028136792293937132 | perceived_ease_of_use | 0.3296148569792852 |
| behavioral_intention | behavioral_intention_z | -0.1573621218418239 | -0.605663108871215 | 0.2909388651875672 | 0.49146259712525286 | 45 | 0.16242595833639517 | 0.0786685541700346 | standard | -0.18191722699791488 | -0.7001720107176626 | 0.3363375567218328 | behavioral_intention | 0.6699204789541362 |
| hedonic_motivation | hedonic_motivation_z | -0.060642334325163694 | -0.29113831864445183 | 0.16985364999412442 | 0.6060942241955865 | 45 | 0.14223012037051275 | 0.056453132407564 | standard | -0.07010508736151383 | -0.3365681333012976 | 0.19635795857826988 | hedonic_motivation | 0.6699204789541362 |
| locus_of_control | locus_of_control_z | -0.4828225881505007 | -0.7337061272943268 | -0.2319390490066746 | 0.00016199038910304968 | 45 | 0.4320295281782247 | 0.3752324809960471 | standard | -0.558163205606642 | -0.8481951218408664 | -0.26813128937241765 | locus_of_control | 0.001457913501927447 |
| facilitating_conditions | facilitating_conditions_z | -0.06518511326534832 | -0.30619938244348494 | 0.1758291559127883 | 0.5960460215452924 | 45 | 0.14176869509182133 | 0.05594556460100342 | standard | -0.07535673075568208 | -0.3539793560904312 | 0.20326589457906702 | facilitating_conditions | 0.6699204789541362 |
| social_influence | social_influence_z | -0.08413418370396458 | -0.38668449387171816 | 0.218416126463789 | 0.5857306697920943 | 45 | 0.14639940326289858 | 0.06103934358918839 | standard | -0.0972626526384985 | -0.44702352780260307 | 0.25249822252560605 | social_influence | 0.6699204789541362 |
| attitude | attitude_z | -0.08503167318295145 | -0.4760140123061167 | 0.30595066594021375 | 0.6699204789541362 | 45 | 0.14557871953273427 | 0.060136591486007585 | standard | -0.09830018819893793 | -0.5502922057566252 | 0.35369182935874927 | attitude | 0.6699204789541362 |

## Secondary Pre/Post Survey Change

| dimension | analysis_type | pre_mean | post_mean | change | ci_low | ci_high | n | phase_p_value | interaction_p_value | fdr_p_value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| perceived_usefulness | mixed_model | 3.761111111111111 | 3.8444444444444446 | 0.08333333333333333 | -0.17222222222222222 | 0.3111111111111111 | 45 | 0.5458249068939554 | 0.6254588375761287 | 0.7017748802922282 |
| perceived_ease_of_use | mixed_model | 3.803703703703703 | 3.7888888888888896 | -0.01481481481481482 | -0.24074074074074067 | 0.174074074074074 | 45 | 0.41939578608015293 | 0.41939578608015293 | 0.7017748802922282 |
| behavioral_intention | mixed_model | 3.8592592592592596 | 3.977777777777778 | 0.11851851851851854 | -0.177962962962963 | 0.38537037037037025 | 45 | 0.7102265982529943 | 0.7631336740375199 | 0.7431207540803043 |
| hedonic_motivation | mixed_model | 3.7851851851851843 | 3.6962962962962957 | -0.08888888888888889 | -0.3703703703703703 | 0.126111111111111 | 45 | 0.7431207540803043 | 0.8167434646681857 | 0.7431207540803043 |
| locus_of_control | mixed_model | 3.088888888888889 | 3.077777777777778 | -0.011111111111111112 | -0.2722222222222222 | 0.2111111111111111 | 45 | 0.4885118195396083 | 0.4885118195396083 | 0.7017748802922282 |
| trust | mixed_model | 3.1666666666666665 | 3.3962962962962964 | 0.22962962962962966 | 0.010925925925925927 | 0.4481481481481481 | 45 | 0.10541038421680092 | 0.10541038421680092 | 0.3009772101586361 |
| facilitating_conditions | mixed_model | 3.933333333333333 | 4.066666666666666 | 0.13333333333333333 | -0.2 | 0.4444444444444444 | 45 | 0.05523396632362869 | 0.12133481100066018 | 0.2485528484563291 |
| social_influence | mixed_model | 3.2888888888888888 | 3.511111111111111 | 0.2222222222222222 | -0.13388888888888886 | 0.6 | 45 | 0.13376764895939383 | 0.13376764895939383 | 0.3009772101586361 |
| attitude | mixed_model | 3.8962962962962964 | 3.837037037037036 | -0.05925925925925925 | -0.2668518518518519 | 0.12592592592592594 | 45 | 0.002464603843315182 | 0.002464603843315182 | 0.022181434589836638 |

## Small-Sample Sensitivity

| detectable_d_a_vs_b_80_power | detectable_d_c_vs_pooled_ab_80_power | detectable_r_n45_80_power | interpretation |
| --- | --- | --- | --- |
| 1.0988721304731635 | 0.8455642631813689 | 0.40723664075787896 | Powered only for relatively large effects; do not claim sample-size adequacy. |

## Manuscript-Ready Quantitative Paragraphs

The quantitative pipeline retained 45 participants and 90 paired survey rows. Prompt analyses used 144 scored assignment observations for assignment-level models. Prompt-grade relationships were evaluated at the participant level, and the old duplicated n=90 prompt-grade p-values were not used.
At the participant level, mean prompt quality was higher for Group C than pooled Groups A and B (mean difference=0.637, Hedges g=0.77, 95% CI for g [0.176, 1.67], n=45).
Mean prompt quality was associated with final grade in the participant-level descriptive analysis (Pearson r=0.451, 95% CI [0.181, 0.657], p=0.00188, n=45).
The targeted adjusted model did not support a strong participant-level negative association between pre-test perceived usefulness and final grade (standardized beta=-0.071, 95% CI [-0.373, 0.231], p=0.645, n=45).
Small-sample sensitivity indicates that the study is powered only for relatively large effects (approximate 80% detectable d for A vs B=1.1).

## Files Generated

- `table_data_verification.csv`
- `table_missingness_prompt_by_group_assignment.csv`
- `table_baseline_balance.csv`
- `table_prompt_trajectory_model.csv`
- `table_prompt_trajectory_estimated_means.csv`
- `table_participant_training_contrasts.csv`
- `table_participant_training_tests.csv`
- `table_learning_outcome_models.csv`
- `table_prompt_grade_correlations.csv`
- `table_calibration_models.csv`
- `table_survey_reliability.csv`
- `table_prepost_survey_change.csv`
- `table_small_sample_sensitivity.csv`
- `table_perceived_usefulness_models.csv`
- `table_complete_case_diagnostics.csv`
- `table_prior_use_mapping.csv`
- `table_scored_assignment_distribution_by_group.csv`
- `table_prompt_sensitivity_min3_assignments.csv`
- `table_prompt_sensitivity_all4_assignments.csv`
- `fig_prompt_quality_trajectory.pdf`
- `fig_prompt_quality_trajectory.png`
- `fig_prompt_quality_learning_outcome.pdf`
- `fig_prompt_quality_learning_outcome.png`
- `fig_calibration_forest.pdf`
- `fig_calibration_forest.png`

## Privacy Verification

No raw identifiers, participant-level rows, raw survey responses, individual grades, or raw transcripts were written to public outputs.
