# Supplementary Figure S3. Final-layer bias of the released model against the log-odds of each
# label's prevalence in the training split.
#
# A model whose outputs lie on the natural prevalence scale has a final-layer bias approximating the
# log-odds of the label's prevalence, and would therefore fall on the identity line. The axes are
# deliberately given the same range so that the identity line is a true diagonal: the observed
# biases lie close to zero for every label across prevalences spanning 0.8% to 52%, which is the
# point of the figure and is invisible if the vertical axis is scaled to the biases alone.
here <- local({
  a <- commandArgs(trailingOnly = FALSE)
  f <- sub("^--file=", "", a[grep("^--file=", a)])
  # R encodes spaces in --file= as ~+~; decode before using the path.
  if (length(f)) { p <- dirname(gsub("~\\+~", " ", f)); if (dir.exists(p)) return(normalizePath(p)) }
  getwd()
})
source(file.path(here, "theme.R"))

d <- read_fig("output_biases.csv") %>%
  mutate(is_composite = label == "Structural heart disease",
         short = gsub(" \\(.*\\)$", "", label))

lim <- range(c(d$logit_train_prevalence, d$output_bias, 0.4))
lim <- c(floor(lim[1]), ceiling(lim[2]))

p <- ggplot(d, aes(logit_train_prevalence, output_bias)) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed",
              colour = REF, linewidth = 0.4) +
  annotate("text", x = lim[1] + 0.35, y = lim[1] + 0.85,
           label = "Outputs on the natural\nprevalence scale would\nlie on this line",
           hjust = 0, vjust = 0, size = ANNOT, colour = "grey40", lineheight = 1.05) +
  geom_hline(yintercept = 0, colour = "grey85", linewidth = 0.3) +
  geom_segment(aes(xend = logit_train_prevalence, yend = logit_train_prevalence),
               colour = "grey80", linewidth = 0.3) +
  geom_point(aes(colour = is_composite), size = 2) +
  ggrepel::geom_text_repel(aes(label = short), size = ANNOT, colour = "grey25",
                           min.segment.length = 0.15, segment.colour = "grey70",
                           segment.linewidth = 0.25, max.overlaps = 20,
                           box.padding = 0.45, point.padding = 0.25, nudge_y = 0.9,
                           force = 4, seed = 1) +
  scale_colour_manual(values = c("TRUE" = PAL[2], "FALSE" = PAL[1]), guide = "none") +
  coord_equal(xlim = lim, ylim = lim) +
  labs(x = "Log-odds of label prevalence in the training split",
       y = "Final-layer bias of the released model") +
  theme_ehj()

save_fig(p, "figureS3_output_bias", width = 13, height = 13)
