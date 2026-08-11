# Figure 1. Cohort assembly.
#
# Every count is read from results/figure_data/cohort_flow.csv, which is written by
# sql/05_cohort_flow.sql, so no count in this diagram is typed by hand.
#
# Box heights AND vertical positions are computed from the number of text lines, so adding or
# removing a line reflows the diagram rather than overflowing a box.
here <- local({
  a <- commandArgs(trailingOnly = FALSE)
  f <- sub("^--file=", "", a[grep("^--file=", a)])
  # R encodes spaces in --file= as ~+~; decode before using the path.
  if (length(f)) { p <- dirname(gsub("~\\+~", " ", f)); if (dir.exists(p)) return(normalizePath(p)) }
  getwd()
})
source(file.path(here, "theme.R"))

fl <- read_fig("cohort_flow.csv")
N  <- setNames(fl$n, fl$stage)
NP <- setNames(fl$n_patients, fl$stage)

# The flow must reconcile before it is drawn. A figure that does not add up is worse than no figure.
stopifnot(N["check_echo_excl_sums"] == 0,
          N["check_excl_sums_to_paired"] == 0,
          N["check_eligible_patients_equals_cohort"] == 0)

k  <- function(x) formatC(x, big.mark = ",", format = "d")
pc <- function(a, b) sprintf("%.1f%%", 100 * a / b)

echo_excl <- N["echo_excl_nontte"] + N["echo_excl_prosthetic"] + N["echo_excl_incomplete"]
ecg_excl  <- N["excl_paced"] + N["excl_poorqual"] + N["excl_nomeas"] + N["excl_age"] + N["excl_sex"]
lost_pts  <- NP["paired"] - NP["eligible_ecgs"]

# One text line occupies LH grid units. The panel is scaled at the end so that LH corresponds to
# 8 pt type at the line height passed to geom_text below; the two must stay consistent.
LH   <- 2.0     # grid units per line of text
PAD  <- 1.7     # grid units of padding above and below the text block inside a box
GAP  <- 6.5     # vertical gap between stacked boxes, leaving room for an arrow
TOP  <- 99

B <- tibble::tribble(
  ~id,  ~x, ~w, ~style,   ~head, ~body,
  "A",  30, 28, "source", "MIMIC-IV-ECG v1.0",
       paste0(k(N["ecg_source"]), " ECGs from ", k(NP["ecg_source"]), " patients"),
  "B",  81, 19, "source", "MIMIC-IV-ECHO v1.0",
       paste0(k(N["echo_source"]), " studies from ", k(NP["echo_source"]), " patients"),
  "B2", 81, 19, "excl",   paste0("Excluded ", k(echo_excl), " studies"),
       paste0("Transoesophageal or stress ", k(N["echo_excl_nontte"]), "\n",
              "Prosthetic valve ", k(N["echo_excl_prosthetic"]), "\n",
              "LVEF or valve not fully assessed ", k(N["echo_excl_incomplete"])),
  "B3", 81, 19, "source", paste0(k(N["echo_eligible"]), " label-eligible studies"),
       paste0("in ", k(NP["echo_eligible"]), " patients"),
  "C",  30, 28, "main",   "ECGs paired with a label-eligible echocardiogram",
       paste0("recorded within the following 365 days\n",
              k(N["paired"]), " ECGs from ", k(NP["paired"]), " patients"),
  "D",  81, 19, "excl",   paste0("Excluded ", k(ecg_excl), " ECGs"),
       paste0("Ventricular pacing ", k(N["excl_paced"]), "\n",
              "Poor quality or lead reversal ", k(N["excl_poorqual"]), "\n",
              "No valid ECG measurements ", k(N["excl_nomeas"]), "\n",
              "Age under 18 years ", k(N["excl_age"]), "\n\n",
              # Set apart by a blank line: this is a patient count, not one of the ECG counts above,
              # and must not read as a fifth addend of the 9,137.
              k(lost_pts), " patients thereby retained no ECG"),
  "E",  30, 28, "main",   "Eligible ECGs",
       paste0(k(N["eligible_ecgs"]), " ECGs from ", k(NP["eligible_ecgs"]), " patients"),
  "F",  30, 28, "final",  "Analytic cohort",
       paste0(k(N["cohort"]), " patients, the most recent eligible ECG of each\n",
              k(N["cohort_shd"]), " (", pc(N["cohort_shd"], N["cohort"]),
              ") with structural heart disease")
) %>%
  mutate(nline = 1 + lengths(strsplit(body, "\n", fixed = TRUE)),
         h     = nline * LH / 2 + PAD)

# unname() is load-bearing: hh["A"] carries the name "A", so c(A = TOP - hh["A"]) would build an
# element named "A.A" and every later lookup by id would silently return NA.
hh <- setNames(B$h, B$id)
h_ <- function(id) unname(hh[id])

# ---- vertical layout, derived ------------------------------------------------------------------
# Right column stacks from the top. The left column's join box is centred on the label box it
# receives, so that feed arrow is horizontal.
yc <- c(A = TOP - h_("A"), B = TOP - h_("B"))
yc["B2"] <- yc[["B"]]  - h_("B")  - GAP - h_("B2")
yc["B3"] <- yc[["B2"]] - h_("B2") - GAP - h_("B3")
yc["C"]  <- yc[["B3"]]

# The stem gap between C and E must be wide enough that the exclusion box D, centred on that stem,
# clears the label box above it. Solving D_top = B3_bottom - CLEAR for the gap gives:
CLEAR <- 1.8
gapCE <- 2 * (h_("D") - h_("C") + h_("B3") + CLEAR)
yc["E"] <- yc[["C"]] - h_("C") - gapCE - h_("E")
yc["D"] <- (yc[["C"]] - h_("C") + yc[["E"]] + h_("E")) / 2
yc["F"] <- yc[["E"]] - h_("E") - GAP - h_("F")

B <- B %>%
  mutate(y      = as.numeric(yc[id]),
         xmin   = x - w, xmax = x + w, ymin = y - h, ymax = y + h,
         head_y = y + nline * LH / 2,      # geom_text vjust = 1 anchors the top of the line
         body_y = head_y - LH)

# No box may overlap another in the same column.
stopifnot(!any(duplicated(B$id)), all(B$h > 0))

ed <- function(id, side) {
  b <- B[B$id == id, ]
  switch(side, top = b$ymax, bottom = b$ymin, left = b$xmin, right = b$xmax)
}
A_ <- tibble::tribble(
  ~x,               ~y,                 ~xend,            ~yend,
  30,               ed("A", "bottom"),  30,               ed("C", "top"),
  81,               ed("B", "bottom"),  81,               ed("B2", "top"),
  81,               ed("B2", "bottom"), 81,               ed("B3", "top"),
  ed("B3", "left"), unname(yc["B3"]),   ed("C", "right"), unname(yc["B3"]),
  30,               ed("C", "bottom"),  30,               ed("E", "top"),
  30,               ed("E", "bottom"),  30,               ed("F", "top")
)
# Each exclusion branch leaves the stem at the vertical centre of the box it feeds.
D_ <- tibble::tibble(x = 30, y = unname(yc["D"]), xend = ed("D", "left"), yend = unname(yc["D"]))

FILL <- c(source = "white", main = "white", excl = "grey97", final = "#eaf0f4")
LINE <- c(source = "grey30", main = "grey30", excl = "grey65", final = PAL[1])

YLIM <- c(min(B$ymin) - 2, 100)

p <- ggplot() +
  geom_rect(data = B, aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax,
                          fill = style, colour = style), linewidth = 0.4) +
  geom_segment(data = A_, aes(x, y, xend = xend, yend = yend), colour = "grey45",
               linewidth = 0.35, arrow = arrow(length = unit(4, "pt"), type = "closed")) +
  geom_segment(data = D_, aes(x, y, xend = xend, yend = yend), colour = "grey65",
               linewidth = 0.35, arrow = arrow(length = unit(4, "pt"), type = "closed")) +
  geom_text(data = B, aes(x, head_y, label = head), fontface = "bold", size = ANNOT,
            colour = "grey15", vjust = 1, lineheight = 1.22) +
  geom_text(data = B, aes(x, body_y, label = body), size = ANNOT,
            colour = "grey30", vjust = 1, lineheight = 1.22) +
  scale_fill_manual(values = FILL, guide = "none") +
  scale_colour_manual(values = LINE, guide = "none") +
  coord_cartesian(xlim = c(0, 100), ylim = YLIM, expand = FALSE) +
  theme_void()

# Height is set so that one grid unit renders at LH/2.0 x 4.9 pt, keeping the computed line spacing
# equal to 8 pt type at a line height of 1.22.
save_fig(p, "figure1_cohort", width = 18, height = diff(YLIM) * 0.1724)
