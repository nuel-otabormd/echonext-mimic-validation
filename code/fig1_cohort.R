#!/usr/bin/env Rscript
# Figure 1 — cohort flow diagram (classic monochrome CONSORT style: sharp rectangles,
# thin grey rules, black text, no fill colour). Graphviz via DiagrammeR. Vector PDF + PNG.
suppressMessages({library(DiagrammeR); library(DiagrammeRsvg); library(rsvg)})

outdir <- file.path(Sys.getenv("ECHONEXT_DATA", path.expand("~/Desktop/RESEARCH")), "echonext-mimic-validation/results/figures")
work   <- file.path(Sys.getenv("ECHONEXT_DATA", path.expand("~/Desktop/RESEARCH")), "EchoNext-repo/results_full/figs")

dot <- '
digraph cohort {
  graph [rankdir=TB, splines=ortho, nodesep=0.55, ranksep=0.42, bgcolor=white]
  node [shape=box, style=filled, fillcolor=white, color="#333333",
        fontname="Helvetica", fontsize=12, penwidth=1.1, margin="0.26,0.17", width=4.3]
  edge [color="#666666", penwidth=1.1, arrowsize=0.8]

  A [label=<MIMIC-IV ECG&#8211;echocardiogram pairs within 1 year<br/><b>233,735 ECGs</b>>]
  j1 [shape=point, width=0.02, color="#666666"]
  B [label=<Eligible ECGs<br/><b>224,598 ECGs</b>>]
  sel [shape=plaintext, margin="0.02,0.06", fontsize=10, fontcolor="#555555",
       label=<Restricted to one ECG per patient (most recent)>]
  C [label=<Primary analytic cohort<br/><b>45,878 patients</b>>]
  EX [shape=box, style=filled, fillcolor=white, color="#777777", penwidth=1.0, fontsize=11, width=3.1,
      label=<<b>Excluded (n = 9,137)</b><br align="left"/> <br align="left"/>Ventricular pacing: 7,436<br align="left"/>Poor quality / lead reversal: 1,101<br align="left"/>No valid ECG measurements: 595<br align="left"/>Age &lt; 18 years: 5<br align="left"/>>]

  A   -> j1 [arrowhead=none]
  j1  -> B
  j1  -> EX [minlen=2]
  B   -> sel [arrowhead=none]
  sel -> C
  {rank=same; j1; EX}
}'

svg <- export_svg(grViz(dot))
for (d in c(outdir, work)) {
  if (!dir.exists(d)) dir.create(d, recursive = TRUE)
  rsvg_png(charToRaw(svg), file.path(d, "fig1_cohort_flow.png"), width = 1750)
  rsvg_pdf(charToRaw(svg), file.path(d, "fig1_cohort_flow.pdf"))
}
cat("saved fig1_cohort_flow (R/Graphviz, monochrome)\n")
