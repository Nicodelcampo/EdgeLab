"""Fail-closed source patch for HFTZonesNQPureV4_V2 export mode."""
from pathlib import Path
import sys
PATH=Path("nt8/HFTZonesNQPureV4_V2.cs")
REPLACEMENTS=[
("                EnableFlowLog            = true;\n                FlowBucketSeconds        = 1;\n\n                MostrarVacios     = true;","                EnableFlowLog            = true;\n                FlowBucketSeconds        = 1;\n                // Safe default for oracle generation: no WPF drawing.\n                ModoExportacionPuro      = true;\n\n                MostrarVacios     = true;"),
("                ProcesarSweeps();\n                DibujarPendientes();\n                return;\n            }\n            if (BarsInProgress != 0) return;\n            if (CurrentBars[0] < 2) return;\n            DibujarPendientes();","                ProcesarSweeps();\n                if (!ModoExportacionPuro) DibujarPendientes();\n                return;\n            }\n            if (BarsInProgress != 0) return;\n            if (ModoExportacionPuro) return;\n            if (CurrentBars[0] < 2) return;\n            DibujarPendientes();"),
("        private void DibujarPendientes()\n        {\n            for (int i = 0; i < zones.Count; i++)","        private void DibujarPendientes()\n        {\n            if (ModoExportacionPuro) return;\n            for (int i = 0; i < zones.Count; i++)"),
("        private void DetectarSolapamientoCluster(int newIdx)\n        {\n            if (newIdx < 0 || newIdx >= zones.Count) return;","        private void DetectarSolapamientoCluster(int newIdx)\n        {\n            if (ModoExportacionPuro) return;\n            if (newIdx < 0 || newIdx >= zones.Count) return;"),
("        private void DetectarVacios()\n        {\n            double binSize = Math.Max(1, VoidBinTicks) * TickSize;","        private void DetectarVacios()\n        {\n            if (ModoExportacionPuro) return;\n            double binSize = Math.Max(1, VoidBinTicks) * TickSize;"),
("        [NinjaScriptProperty]\n        [Display(Name=\"Enable DB Logging\", Order=1, GroupName=\"F. Database\")]\n        public bool EnableDbLogging { get; set; }","        [Display(Name=\"Modo Exportacion Puro (sin render)\", Order=0, GroupName=\"F. Database\", Description=\"Desactiva rectangulos, etiquetas, clusters y vacios durante la exportacion.\")]\n        public bool ModoExportacionPuro { get; set; }\n\n        [NinjaScriptProperty]\n        [Display(Name=\"Enable DB Logging\", Order=1, GroupName=\"F. Database\")]\n        public bool EnableDbLogging { get; set; }")]
def main():
    if not PATH.exists(): print(f"missing: {PATH}",file=sys.stderr); return 2
    text=PATH.read_text(encoding="utf-8-sig"); errors=[]
    for old,_ in REPLACEMENTS:
        n=text.count(old)
        if n!=1: errors.append(f"expected one match, got {n}: {old[:70]!r}")
    if errors:
        print("PATCH REFUSED; source is not audited revision",file=sys.stderr); print("\n".join(errors),file=sys.stderr); return 3
    for old,new in REPLACEMENTS: text=text.replace(old,new)
    PATH.write_text(text,encoding="utf-8"); print(f"patched {PATH}; inspect diff and compile in NT8"); return 0
if __name__=="__main__": raise SystemExit(main())
