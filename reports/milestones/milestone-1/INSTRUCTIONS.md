# Milestone 1: course instructions (transcribed)

Transcribed from the course handout "Signal Research Project Milestone 1" so it sits next to the plan. Group deliverable, due **Mon 2026-11-09**.

> This milestone should demonstrate your ability to access the historical data for your research, read it and build a research pipeline. The task will vary on the research topics.

## Overall plan

- Combine each group member's signal research write-up into one document.
- Clean up the document and incorporate feedback where needed.
- Confirm you have the data your research requires and update your data chapter.
- Construct your features and run systematic feature-quality and collinearity surveys, as we discussed in the lecture.
- Implement a simple optimization procedure of your choice. Come up with a combined signal that beats the best standalone feature out of sample. Document the procedure.
- Compare your metric against the baseline.
- Design an iterative improvement loop and run it several times.
- Measure the improvement at each iteration.
- Present the first version of the final plot you will show on your last slide.

## Suggested exercises: Relative Value (Cross Asset trading) and Market Regime (our topic)

- Calculate your favorite price-based features for 5 instruments.
- Calculate cross-correlation matrices for different EMA horizons. [submit]
- Pick your favorite EMA duration. Average the 5-instrument correlation matrix over time (e.g., daily matrices) for this duration. [submit]
- Find a high-volatility day.
- Calculate the averaged cross-correlation matrix for that day and compare it with the long-run average. [submit]
- Create a volume-weighted index of the 5 instruments. Plot return-distribution histograms for the index and each instrument on one plot. [submit]
- Come up with an improvement loop, describe it, and run it several times.
- Plot the metric across iterations of the improvement loop. [submit]
- Present the first version of the final plot you will show on your last slide [submit]

## Suggested exercises: Price predicting (the parts that apply to a spread target)

- Calculate your favorite price-based, trade-based, and book-based features.
- Plot each feature's distribution; report mean, std, skew, and kurtosis. [submit]
- Calculate the feature cross-correlation matrix. [submit]
- Calculate the correlation of features with future returns at several horizons. [submit]
- Calculate the correlation of BTC returns and trade-based features with the corresponding ETH features. [submit]
- Find a combination of features that predicts at least one future-return horizon better than the best standalone feature. [submit]

(The volatility-predicting list from the handout is left out; it isn't our topic.)
