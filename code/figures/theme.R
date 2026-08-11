# Shared plotting style for all figures.
#
# Figures are written as vector PDF, which is resolution independent and is the format preferred by
# the journal for charts. A 600 dpi PNG is written alongside each one for convenience only; the PDF
# is the file to submit.

suppressPackageStartupMessages({
  library(ggplot2); library(dplyr); library(readr); library(scales); library(patchwork)
})

FIG_DIR  <- Sys.getenv("ECHONEXT_FIG_OUT", file.path(dirname(dirname(getwd())), "results", "figures"))
DATA_DIR <- Sys.getenv("ECHONEXT_FIG_DATA", file.path(dirname(dirname(getwd())), "results", "figure_data"))

# Resolve relative to the repository root regardless of where Rscript is invoked from.
repo_root <- function() {
  a <- commandArgs(trailingOnly = FALSE)
  f <- sub("^--file=", "", a[grep("^--file=", a)])
  # R encodes spaces in --file= as ~+~; decode before using the path.
  if (length(f)) {
    p <- file.path(dirname(gsub("~\\+~", " ", f)), "..", "..")
    if (dir.exists(p)) return(normalizePath(p))
  }
  normalizePath(".")
}
FIG_DIR  <- file.path(repo_root(), "results", "figures")
DATA_DIR <- file.path(repo_root(), "results", "figure_data")
dir.create(FIG_DIR, showWarnings = FALSE, recursive = TRUE)

# Colour-blind safe. Grey is reserved for reference lines and null strategies.
PAL <- c("#1b4965", "#c1666b", "#4c956c", "#e09f3e", "#5b5f97", "#8d99ae")
REF <- "grey55"

# Typography is fixed here and must not be overridden per figure: every panel in every figure uses
# the same sizes so that the set reads as one piece of work. BASE_PT is the axis-text size in points.
# ANNOT is the equivalent for in-panel text drawn by geom_text/geom_label, whose __TEXT	__DATA	__OBJC	others	dec	hex argument is
# in millimetres (points = mm x 2.845), so ANNOT below is 8 pt.
BASE_PT <- 9
ANNOT   <- 8 / 2.845

theme_ehj <- function(base_size = BASE_PT) {
  theme_minimal(base_size = base_size) +
    theme(
      panel.grid.minor  = element_blank(),
      panel.grid.major  = element_line(colour = "grey92", linewidth = 0.3),
      panel.border      = element_rect(colour = "grey30", fill = NA, linewidth = 0.4),
      axis.title        = element_text(colour = "grey20"),
      axis.text         = element_text(colour = "grey30"),
      plot.title        = element_text(face = "bold", size = base_size + 1, hjust = 0),
      plot.subtitle     = element_text(colour = "grey35", size = base_size - 1),
      strip.text        = element_text(face = "bold", size = base_size, colour = "grey20"),
      legend.text       = element_text(size = base_size - 1),
      legend.title      = element_blank(),
      legend.key.height = unit(9, "pt"),
      legend.position   = "bottom",
      plot.margin       = margin(6, 8, 6, 6)
    )
}

# width and height in centimetres
save_fig <- function(plot, name, width, height) {
  pdf_path <- file.path(FIG_DIR, paste0(name, ".pdf"))
  # The base PDF device is used rather than cairo_pdf: cairo reports as available on some builds
  # but fails to load, and silently produces no file. Both write true vector output.
  ggsave(pdf_path, plot, width = width, height = height, units = "cm",
         device = grDevices::pdf, useDingbats = FALSE)
  ggsave(file.path(FIG_DIR, paste0(name, ".png")), plot,
         width = width, height = height, units = "cm", dpi = 600)
  cat(sprintf("  %-28s %.1f x %.1f cm\n", paste0(name, ".pdf"), width, height))
}

read_fig <- function(f) suppressMessages(read_csv(file.path(DATA_DIR, f), show_col_types = FALSE))
