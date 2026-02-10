# nmr-metabolomics

Open-source NMR spectral quality control tools developed in collaboration with the Collaborative Computing Project for NMR (CCPN) and the University of Liverpool NMR Centre. Includes both standalone QC scripts and CCPN AnalysisMetabolomics pipeline plugins for automated spectral assessment.

## Background

Quantitative NMR metabolomics requires rigorous quality control to ensure reliable metabolite quantification. These tools automate spectral QC checks that are typically performed manually, providing reproducible pass/fail assessments and diagnostic visualisations.

Developed as part of an ongoing collaboration with Marie Phelan (University of Liverpool NMR Centre) to build open-source metabolite quantification routines.

## Repository Structure

    nmr-metabolomics/
    ├── scripts/
    │   ├── ccpn_integration/
    │   │   ├── Baseline_QC_Pipe.py                     # Baseline flatness assessment
    │   │   ├── SNR_QC_Pipe.py                          # Signal-to-noise ratio evaluation
    │   │   ├── TSP_Linewidth_QC_Pipe.py                # TSP reference linewidth check
    │   │   ├── Water_Suppression_QC_Pipe.py            # Water suppression quality
    │   │   └── QC_Summary_Report_Pipe_With_Columns.py  # Combined QC summary report
    │   └── quality_control/
    │       └── nmr_qc_standalone.py                    # Standalone QC script (no CCPN dependency)
    └── README.md

## CCPN Pipeline Plugins

Five pipeline plugins designed for CCPN AnalysisMetabolomics, each implementing a specific QC check as a modular pipe that integrates into the CCPN pipeline framework.

- **Baseline QC** — Evaluates baseline flatness by measuring standard deviation in the noise region (10-11 ppm). Flags spectra exceeding configurable SD threshold.
- **SNR QC** — Calculates signal-to-noise ratio for reference peaks. Ensures adequate sensitivity for quantification.
- **TSP Linewidth QC** — Measures linewidth of the TSP internal reference standard. Detects shimming problems and magnetic field inhomogeneity.
- **Water Suppression QC** — Assesses residual water signal quality. Poor water suppression distorts nearby metabolite peaks.
- **QC Summary Report** — Aggregates results from all QC pipes into a single pass/fail summary table with per-spectrum diagnostics.

Each plugin follows the CCPN PipeBase architecture with configurable thresholds and GUI integration.

## Standalone QC Script

The standalone script (nmr_qc_standalone.py) operates independently of CCPN, reading predicted spectra and sample data directly. It performs:

- Spectral loading and cleaning (TSV format)
- Peak detection and comparison between predicted and observed spectra
- Diagnostic overlay plots (sample vs. predicted)
- Automated QC report generation

Dependencies: pandas, numpy, matplotlib, scipy

## Dependencies

CCPN plugins: Requires CCPN AnalysisMetabolomics (v3+)

Standalone script: pandas, numpy, matplotlib, scipy, tqdm

## Author

Jack Edmondson — PhD Candidate, Liverpool John Moores University

Collaboration: Marie Phelan, University of Liverpool NMR Centre; CCPN

## Status

Active development. QC pipeline plugins deployed and in use. Metabolite quantification library under development.
