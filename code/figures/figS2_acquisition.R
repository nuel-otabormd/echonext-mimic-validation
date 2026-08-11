# Supplementary Figure S2. Composite discrimination by electrocardiogram acquisition setting.
here <- local({
  a <- commandArgs(trailingOnly = FALSE)
  f <- sub("^--file=", "", a[grep("^--file=", a)])
  # R encodes spaces in --file= as ~+~; decode before using the path.
  if (length(f)) { p <- dirname(gsub("~\\+~", " ", f)); if (dir.exists(p)) return(normalizePath(p)) }
  getwd()
})
source(file.path(here, "theme.R"))

d <- read_fig("acquisition.csv") %>%
  mutate(setting = gsub(" \\| ", "\n", setting),
         lab = sprintf("%s\n(n = %s)", setting, comma(n))) %>%
  arrange(auroc) %>% mutate(lab = factor(lab, levels = lab))

overall <- 0.790
p <- ggplot(d, aes(auroc, lab)) +
  geom_vline(xintercept = overall, linetype = "dashed", colour = REF, linewidth = 0.35) +
  geom_errorbar(aes(xmin = ci_low, xmax = ci_high), orientation = "y", width = 0.18,
                colour = PAL[1], linewidth = 0.45) +
  geom_point(aes(size = n), colour = PAL[1]) +
  scale_size_continuous(range = c(1.2, 3.4), guide = "none") +
  labs(x = "Composite AUROC (95% CI)", y = NULL,
       subtitle = "Dashed line is the overall cohort estimate") +
  theme_ehj() +
  theme(axis.text.y = element_text(lineheight = 0.95))

save_fig(p, "figureS2_acquisition", width = 16, height = 10)
