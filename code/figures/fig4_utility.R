# Figure 4. Clinical utility of the composite score.
#   A  Decision curve: net benefit against threshold probability.
#   B  Cumulative diagnostic yield against the proportion of the cohort imaged.
here <- local({
  a <- commandArgs(trailingOnly = FALSE)
  f <- sub("^--file=", "", a[grep("^--file=", a)])
  # R encodes spaces in --file= as ~+~; decode before using the path.
  if (length(f)) { p <- dirname(gsub("~\\+~", " ", f)); if (dir.exists(p)) return(normalizePath(p)) }
  getwd()
})
source(file.path(here, "theme.R"))

dc <- read_fig("decision_curve.csv") %>%
  mutate(strategy = factor(strategy, levels = c("Model", "Model, prior shift", "Image all")))

# The two model curves overlap almost exactly, which is the point: the composite is already
# calibrated, so the prior shift has nothing to correct. Drawing the corrected curve thinner and on
# top keeps both visible rather than one hiding the other.
pA <- ggplot(dc, aes(threshold, net_benefit, colour = strategy, linetype = strategy)) +
  geom_hline(yintercept = 0, colour = REF, linewidth = 0.35) +
  geom_line(aes(linewidth = strategy)) +
  scale_linewidth_manual(values = c("Model" = 1.1, "Model, prior shift" = 0.45,
                                    "Image all" = 0.55), guide = "none") +
  scale_colour_manual(values = c("Model" = PAL[1], "Model, prior shift" = PAL[3], "Image all" = REF)) +
  scale_linetype_manual(values = c("Model" = "solid", "Model, prior shift" = "solid",
                                   "Image all" = "dashed")) +
  scale_x_continuous(labels = percent_format(accuracy = 1)) +
  coord_cartesian(ylim = c(-0.05, 0.50)) +
  labs(title = "A", x = "Threshold probability", y = "Net benefit",
       subtitle = "The two model curves overlap; imaging no patient corresponds to zero") +
  theme_ehj()

cg <- read_fig("cumulative_gain.csv")
mark <- cg %>% filter(abs(proportion_imaged - 0.10) == min(abs(proportion_imaged - 0.10)))

pB <- ggplot(cg, aes(proportion_imaged)) +
  geom_line(aes(y = yield_unprioritised, colour = "Unprioritised referral"),
            linetype = "dashed", linewidth = 0.5) +
  geom_line(aes(y = yield_model, colour = "Ranked by model score"), linewidth = 0.7) +
  geom_segment(data = mark, aes(x = proportion_imaged, xend = proportion_imaged,
                                y = yield_unprioritised, yend = yield_model),
               colour = "grey40", linewidth = 0.3) +
  geom_point(data = mark, aes(y = yield_model), colour = PAL[1], size = 1.4) +
  geom_text(data = mark, aes(y = yield_model,
                             label = sprintf("%.0f%% of cases at %.0f%% capacity",
                                             100 * yield_model, 100 * proportion_imaged)),
            hjust = -0.08, vjust = 0.4, size = ANNOT, colour = "grey20") +
  scale_colour_manual(values = c("Ranked by model score" = PAL[1],
                                 "Unprioritised referral" = REF)) +
  scale_x_continuous(labels = percent_format(accuracy = 1), expand = c(0.01, 0)) +
  scale_y_continuous(labels = percent_format(accuracy = 1), expand = c(0.01, 0)) +
  labs(title = "B", x = "Proportion of cohort imaged",
       y = "Structural heart disease identified",
       subtitle = "Unprioritised referral is a random ordering of the same cohort") +
  theme_ehj()

save_fig(pA / pB, "figure4_utility", width = 12, height = 17)
