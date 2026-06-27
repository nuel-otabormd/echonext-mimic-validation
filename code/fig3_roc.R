#!/usr/bin/env Rscript
# Figure 3 — ROC curves (composite + strongest components) in MIMIC-IV external validation.
# Run: python3 code/fig3_roc.py  &&  Rscript code/fig3_roc.R
suppressMessages(library(ggplot2))
navy<-"#1f3b5c"; teal<-"#2a9d8f"; rust<-"#bb4430"
figd<-file.path(Sys.getenv("ECHONEXT_DATA", path.expand("~/Desktop/RESEARCH")), "EchoNext-repo/results_full/figs")
repo<-file.path(Sys.getenv("ECHONEXT_DATA", path.expand("~/Desktop/RESEARCH")), "echonext-mimic-validation/results/figures")
roc<-read.csv(file.path(figd,"roc.csv")); labs<-unique(roc$label); roc$label<-factor(roc$label, levels=labs)
cols<-setNames(c(navy,teal,rust), labs)   # Any SHD / Reduced LVEF / RV dysfunction (export order)
p<-ggplot(roc, aes(fpr, tpr, color=label))+
  geom_abline(slope=1,intercept=0,linetype="dashed",color="grey55",linewidth=0.4)+
  geom_line(linewidth=1)+ scale_color_manual(values=cols)+
  coord_equal(xlim=c(0,1),ylim=c(0,1),expand=FALSE)+
  labs(x="1 - Specificity", y="Sensitivity", title="ROC - MIMIC-IV external validation", color=NULL)+
  theme_classic(base_size=11, base_family="Helvetica")+
  theme(legend.position=c(0.97,0.04), legend.justification=c(1,0), legend.background=element_blank(),
        legend.key.height=unit(13,"pt"), plot.title=element_text(size=11), plot.margin=margin(8,10,6,6))
for (d in c(repo, figd)) { if(!dir.exists(d)) dir.create(d,recursive=TRUE)
  ggsave(file.path(d,"fig5_roc.png"), p, width=5.4, height=4.9, dpi=300, bg="white")
  ggsave(file.path(d,"fig5_roc.pdf"), p, width=5.4, height=4.9, bg="white") }
cat("saved fig5_roc (R/ggplot2)\n")
