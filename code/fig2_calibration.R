#!/usr/bin/env Rscript
# Figure 2 — calibration (A: Any-SHD reliability before/after recalibration;
# B: per-condition over-prediction). Reads CSVs from fig2_calibration.py.
# Run: python3 code/fig2_calibration.py  &&  Rscript code/fig2_calibration.R
suppressMessages({library(ggplot2); library(patchwork)})
navy<-"#1f3b5c"; orange<-"#d8862b"; grey<-"#9aa6b2"
fig <- file.path(Sys.getenv("ECHONEXT_DATA", path.expand("~/Desktop/RESEARCH")), "EchoNext-repo/results_full/figs")
repo<- file.path(Sys.getenv("ECHONEXT_DATA", path.expand("~/Desktop/RESEARCH")), "echonext-mimic-validation/results/figures")
rel<-read.csv(file.path(fig,"reliability.csv"), check.names=FALSE, encoding="UTF-8")
cil<-read.csv(file.path(fig,"cil.csv"), encoding="UTF-8"); cil<-cil[order(cil$cil),]
cil$label<-factor(cil$label, levels=cil$label); cil$grp<-ifelse(cil$is_shd==1,"Composite","Component")

pA<-ggplot(rel, aes(pred, obs, color=method, shape=method))+
  geom_abline(slope=1,intercept=0,linetype="dashed",color="grey55",linewidth=0.4)+
  geom_line(linewidth=0.8)+geom_point(size=2.1)+
  scale_color_manual(values=c("Original (slope 0.94)"=navy,"Recalibrated (out-of-fold Platt)"=orange))+
  scale_shape_manual(values=c("Original (slope 0.94)"=16,"Recalibrated (out-of-fold Platt)"=15))+
  coord_equal(xlim=c(0,1),ylim=c(0,1),expand=FALSE)+
  labs(x="Predicted probability",y="Observed frequency",title="Any-SHD calibration",color=NULL,shape=NULL)+
  theme_classic(base_size=11,base_family="Helvetica")+
  theme(legend.position=c(0.03,0.99),legend.justification=c(0,1),legend.background=element_blank(),
        legend.key.height=unit(12,"pt"),plot.title=element_text(size=11),plot.margin=margin(6,12,6,6))

pB<-ggplot(cil, aes(cil, label, fill=grp))+
  geom_col(width=0.72)+geom_vline(xintercept=0,color="black",linewidth=0.4)+
  scale_fill_manual(values=c("Composite"=navy,"Component"=grey),guide="none")+
  labs(x="Calibration-in-the-large",y=NULL,title="Per-condition over-prediction")+
  theme_classic(base_size=11,base_family="Helvetica")+
  theme(plot.title=element_text(size=11),plot.margin=margin(6,8,6,6))

p<-pA+pB+plot_layout(widths=c(1,1.15))+plot_annotation(tag_levels="A")&
  theme(plot.tag=element_text(face="bold",size=15,family="Helvetica"))
for (d in c(repo, fig)) { if(!dir.exists(d)) dir.create(d,recursive=TRUE)
  ggsave(file.path(d,"fig3_calibration.png"), p, width=10, height=4.7, dpi=300, bg="white")
  ggsave(file.path(d,"fig3_calibration.pdf"), p, width=10, height=4.7, bg="white") }
cat("saved fig3_calibration (R/ggplot2)\n")
