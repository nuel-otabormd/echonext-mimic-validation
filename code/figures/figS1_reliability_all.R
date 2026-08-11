# Supplementary Figure S1. Reliability curves for the remaining component labels.
here <- local({
  a <- commandArgs(trailingOnly = FALSE)
  f <- sub("^--file=", "", a[grep("^--file=", a)])
  # R encodes spaces in --file= as ~+~; decode before using the path.
  if (length(f)) { p <- dirname(gsub("~\\+~", " ", f)); if (dir.exists(p)) return(normalizePath(p)) }
  getwd()
})
source(file.path(here, "theme.R"))

shown <- c("Structural heart disease", "Reduced LVEF (<=45%)", "RV dysfunction", "Aortic stenosis")
d <- read_fig("reliability.csv") %>%
  filter(!label %in% shown) %>%
  mutate(variant = factor(variant, levels = c("As released", "After prior shift")))

p <- ggplot(d, aes(predicted, observed, colour = variant)) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed", colour = REF, linewidth = 0.35) +
  geom_line(linewidth = 0.45) + geom_point(size = 0.9) +
  facet_wrap(~ label, ncol = 4, scales = "free") +
  scale_colour_manual(values = c("As released" = PAL[2], "After prior shift" = PAL[1])) +
  scale_x_continuous(labels = percent_format(accuracy = 1)) +
  scale_y_continuous(labels = percent_format(accuracy = 1)) +
  labs(x = "Predicted probability", y = "Observed frequency") +
  theme_ehj()

save_fig(p, "figureS1_reliability_all", width = 18, height = 13)
