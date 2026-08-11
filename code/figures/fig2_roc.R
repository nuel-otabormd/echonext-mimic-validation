# Figure 2. Receiver operating characteristic curves in MIMIC-IV.
here <- local({
  a <- commandArgs(trailingOnly = FALSE)
  f <- sub("^--file=", "", a[grep("^--file=", a)])
  # R encodes spaces in --file= as ~+~; decode before using the path.
  if (length(f)) { p <- dirname(gsub("~\\+~", " ", f)); if (dir.exists(p)) return(normalizePath(p)) }
  getwd()
})
source(file.path(here, "theme.R"))

d <- read_fig("roc_curves.csv") %>%
  mutate(lab = sprintf("%s (AUROC %.3f)", label, auroc),
         lab = factor(lab, levels = unique(lab[order(-auroc)])))

p <- ggplot(d, aes(fpr, tpr, colour = lab)) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed", colour = REF, linewidth = 0.35) +
  geom_line(linewidth = 0.6) +
  scale_colour_manual(values = PAL[1:3]) +
  scale_x_continuous(labels = percent_format(accuracy = 1), expand = c(0.005, 0)) +
  scale_y_continuous(labels = percent_format(accuracy = 1), expand = c(0.005, 0)) +
  coord_equal() +
  labs(x = "1 - specificity", y = "Sensitivity") +
  theme_ehj() +
  theme(legend.position = c(0.98, 0.02), legend.justification = c(1, 0),
        legend.background = element_rect(fill = alpha("white", 0.85), colour = NA))

save_fig(p, "figure2_roc", width = 9, height = 9.6)
